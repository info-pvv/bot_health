# bot/handlers/duty.py
"""
Обработчики для системы дежурных администраторов
"""
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
from datetime import datetime, timedelta, date

from bot.imports import (
    admin_only,
    api_client,
    DutyStates,
    ActionStates,
    AdminStates,  # ← Добавляем недостающий импорт
)
from bot.keyboards.duty import (
    get_duty_main_keyboard,
    get_sector_selection_keyboard,
    get_user_selection_keyboard_duty,
    get_week_confirmation_keyboard,
    get_duty_pool_actions_keyboard,
    get_duty_back_keyboard,
)
from bot.keyboards.admin import get_admin_keyboard

logger = logging.getLogger(__name__)

# ========== ВХОД В МЕНЮ УПРАВЛЕНИЯ ДЕЖУРСТВАМИ ==========


@admin_only
async def cmd_duty_management(message: types.Message, state: FSMContext):
    """Войти в меню управления дежурствами"""
    keyboard = get_duty_main_keyboard()
    await message.answer(
        "👨‍✈️ **УПРАВЛЕНИЕ ДЕЖУРСТВАМИ АДМИНИСТРАТОРОВ**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_action)


# ========== ПРОСМОТР ПУЛА ДЕЖУРНЫХ ==========


@admin_only
async def duty_view_pool_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать просмотр пула - запросить сектор"""
    await callback.answer()

    # Получаем список секторов для выбора
    sectors_data = await api_client.get_sectors()
    if "error" in sectors_data or not sectors_data.get("sectors"):
        await callback.message.edit_text(
            "❌ Не удалось получить список секторов.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    sectors = sectors_data["sectors"]
    keyboard = get_sector_selection_keyboard(sectors, action_prefix="duty_view_pool")

    await callback.message.edit_text(
        "🏢 **Выберите сектор** для просмотра пула дежурных:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_view_pool_by_sector(callback: types.CallbackQuery, state: FSMContext):
    """Показать пул дежурных для выбранного сектора"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])

    # Получаем пул для сектора
    pool_data = await api_client.get_duty_pool(sector_id, active_only=True)

    if "error" in pool_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения пула: {pool_data['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    items = pool_data.get("items", [])

    # Получаем название сектора (если есть в ответе)
    sector_name = f"Сектор {sector_id}"
    if items and len(items) > 0:
        sector_name = items[0].get("sector_name", sector_name)

    if not items:
        message_text = f"📭 Пул дежурных для **{sector_name}** пуст."
    else:
        message_text = f"👥 **Пул дежурных для {sector_name}:**\n\n"
        for item in items:
            # Используем user_name из ответа API
            user_name = item.get("user_name", f"ID {item['user_id']}")
            added_at = (
                item.get("added_at", "")[:10] if item.get("added_at") else "неизвестно"
            )
            message_text += f"• {user_name} (с {added_at})\n"

    # Кнопка для возврата к выбору сектора или в меню
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="🔄 Другой сектор", callback_data="duty_view_pool"
        ),
        types.InlineKeyboardButton(text="🔙 Меню", callback_data="duty_menu"),
    )

    await callback.message.edit_text(
        message_text, reply_markup=builder.as_markup(), parse_mode="Markdown"
    )
    await state.set_state(DutyStates.waiting_for_action)


# ========== ДОБАВЛЕНИЕ В ПУЛ ==========


@admin_only
async def duty_add_to_pool_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать добавление в пул - запросить сектор"""
    await callback.answer()

    sectors_data = await api_client.get_sectors()
    if "error" in sectors_data or not sectors_data.get("sectors"):
        await callback.message.edit_text(
            "❌ Не удалось получить список секторов.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    sectors = sectors_data["sectors"]
    keyboard = get_sector_selection_keyboard(
        sectors, action_prefix="duty_add_select_sector"
    )

    await callback.message.edit_text(
        "🏢 **Выберите сектор**, в который хотите добавить дежурного:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_add_select_sector(callback: types.CallbackQuery, state: FSMContext):
    """Сектор выбран, теперь запросить пользователя"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    await state.update_data(selected_sector_id=sector_id)

    # Получаем название сектора
    sectors_data = await api_client.get_sectors()
    sector_name = f"Сектор {sector_id}"
    if "error" not in sectors_data:
        for sector in sectors_data.get("sectors", []):
            if sector.get("sector_id") == sector_id:
                sector_name = sector.get("name", sector_name)
                break

    # Получаем список пользователей, которые могут быть дежурными
    eligible_users = await api_client.get_eligible_users(sector_id=sector_id)

    if "error" in eligible_users:
        await callback.message.edit_text(
            f"❌ Ошибка получения пользователей: {eligible_users['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    # Проверяем формат ответа
    if isinstance(eligible_users, list):
        users = eligible_users
    else:
        users = (
            eligible_users.get("users", []) if isinstance(eligible_users, dict) else []
        )

    if not users:
        await callback.message.edit_text(
            f"❌ Нет пользователей, которые могут быть дежурными, для {sector_name}.\n"
            f"Сначала включите им флаг 'is_duty_eligible' через админку.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    keyboard = get_user_selection_keyboard_duty(
        users, sector_id, action_prefix="duty_add_confirm"
    )

    await callback.message.edit_text(
        f"👤 **Выберите пользователя** для добавления в пул {sector_name}:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_user_selection)


async def duty_add_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение и добавление пользователя в пул"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    user_id = int(data_parts[2])

    # Добавляем в пул
    result = await api_client.add_to_duty_pool(
        user_id=user_id, sector_id=sector_id, added_by=callback.from_user.id
    )

    if "error" in result:
        await callback.message.edit_text(
            f"❌ Ошибка добавления: {result['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
    else:
        await callback.message.edit_text(
            f"✅ Пользователь успешно добавлен в пул дежурных сектора {sector_id}!",
            reply_markup=get_duty_main_keyboard(),
        )
        await state.set_state(DutyStates.waiting_for_action)


# ========== УДАЛЕНИЕ ИЗ ПУЛА ==========


@admin_only
async def duty_remove_from_pool_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать удаление из пула - запросить сектор"""
    await callback.answer()

    sectors_data = await api_client.get_sectors()
    if "error" in sectors_data or not sectors_data.get("sectors"):
        await callback.message.edit_text(
            "❌ Не удалось получить список секторов.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    sectors = sectors_data["sectors"]
    keyboard = get_sector_selection_keyboard(
        sectors, action_prefix="duty_remove_select_sector"
    )

    await callback.message.edit_text(
        "🏢 **Выберите сектор**, из которого хотите удалить дежурного:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_remove_select_sector(callback: types.CallbackQuery, state: FSMContext):
    """Сектор выбран, показать пул для удаления"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])

    # Получаем активный пул для этого сектора
    pool_data = await api_client.get_duty_pool(sector_id, active_only=True)

    if "error" in pool_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения пула: {pool_data['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    items = pool_data.get("items", [])

    if not items:
        await callback.message.edit_text(
            f"📭 Пул дежурных для сектора {sector_id} пуст. Удалять некого.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    # Создаем клавиатуру с пользователями из пула
    builder = InlineKeyboardBuilder()
    for item in items:
        user_name = item.get("user_name", f"ID {item['user_id']}")

        builder.row(
            types.InlineKeyboardButton(
                text=f"❌ {user_name}",
                callback_data=f"duty_remove_confirm:{sector_id}:{item['user_id']}",
            )
        )
    builder.row(types.InlineKeyboardButton(text="🔙 Отмена", callback_data="duty_menu"))

    await callback.message.edit_text(
        f"👥 **Выберите пользователя для удаления** из пула сектора {sector_id}:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_user_removal)


async def duty_remove_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение и удаление пользователя из пула"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    user_id = int(data_parts[2])

    # Удаляем из пула (деактивируем)
    result = await api_client.remove_from_duty_pool(user_id, sector_id)

    if "error" in result:
        await callback.message.edit_text(
            f"❌ Ошибка удаления: {result['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
    else:
        await callback.message.edit_text(
            f"✅ Пользователь успешно удален из пула дежурных сектора {sector_id}!",
            reply_markup=get_duty_main_keyboard(),
        )
        await state.set_state(DutyStates.waiting_for_action)


# ========== НАЗНАЧЕНИЕ НА НЕДЕЛЮ ==========


@admin_only
async def duty_assign_week_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать назначение на неделю - запросить сектор"""
    await callback.answer()

    sectors_data = await api_client.get_sectors()
    if "error" in sectors_data or not sectors_data.get("sectors"):
        await callback.message.edit_text(
            "❌ Не удалось получить список секторов.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    sectors = sectors_data["sectors"]
    keyboard = get_sector_selection_keyboard(
        sectors, action_prefix="duty_assign_week_sector"
    )

    await callback.message.edit_text(
        "🏢 **Выберите сектор** для назначения дежурного на следующую неделю:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_assign_week_sector(callback: types.CallbackQuery, state: FSMContext):
    """Сектор выбран, подтвердить неделю"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])

    # Проверяем, что sector_id положительный
    if sector_id < 0:
        logger.error(f"Получен отрицательный sector_id: {sector_id}")
        await callback.message.edit_text(
            f"❌ Ошибка: некорректный ID сектора. Обратитесь к администратору.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    # Рассчитываем дату начала следующей недели (ближайший понедельник)
    today = date.today()
    days_until_monday = (0 - today.weekday()) % 7
    if days_until_monday == 0:
        # Если сегодня понедельник, берем следующую неделю
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    week_start_str = next_monday.isoformat()

    week_dates = [next_monday + timedelta(days=i) for i in range(7)]
    week_dates_str = "\n".join([d.strftime("%d.%m.%Y") for d in week_dates])

    await state.update_data(
        assign_sector_id=sector_id, assign_week_start=week_start_str
    )

    keyboard = get_week_confirmation_keyboard(sector_id, week_start_str)

    await callback.message.edit_text(
        f"📅 **Подтвердите назначение**\n\n"
        f"Сектор: {sector_id}\n"
        f"Неделя начала: {next_monday.strftime('%d.%m.%Y')}\n\n"
        f"Будут назначены дежурства на даты:\n{week_dates_str}\n\n"
        f"Система автоматически выберет дежурного с наименьшим количеством смен.",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_week_selection)


async def duty_assign_week_confirm(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение и назначение дежурства на неделю"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    week_start = data_parts[2]

    # Вызываем API для назначения
    result = await api_client.assign_weekly_duty(
        sector_id=sector_id, week_start=week_start, created_by=callback.from_user.id
    )

    if "error" in result:
        await callback.message.edit_text(
            f"❌ Ошибка назначения: {result['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
    elif result.get("assigned_user_id"):
        assigned_user = result.get(
            "assigned_user_name", f"ID {result['assigned_user_id']}"
        )
        week_dates = result.get("week_dates", [])
        week_dates_str = (
            ", ".join([d[:10] for d in week_dates]) if week_dates else "не указаны"
        )

        await callback.message.edit_text(
            f"✅ **Дежурство успешно назначено!**\n\n"
            f"Сектор: {sector_id}\n"
            f"Дежурный: {assigned_user}\n"
            f"Неделя: {week_dates_str}",
            reply_markup=get_duty_main_keyboard(),
            parse_mode="Markdown",
        )
        await state.set_state(DutyStates.waiting_for_action)
    else:
        await callback.message.edit_text(
            f"⚠️ {result.get('message', 'Не удалось назначить дежурство.')}",
            reply_markup=get_duty_main_keyboard(),
        )
        await state.set_state(DutyStates.waiting_for_action)


# ========== ДЕЖУРНЫЙ СЕГОДНЯ ==========


@admin_only
async def duty_today(callback: types.CallbackQuery, state: FSMContext):
    """Показать, кто дежурит сегодня"""
    await callback.answer()

    today_data = await api_client.get_today_duty()

    if "error" in today_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения данных: {today_data['error']}",
            reply_markup=get_duty_main_keyboard(),
        )
        return

    duties = today_data.get("duties", [])

    if not duties:
        message_text = "📭 Сегодня нет назначенных дежурных."
    else:
        message_text = "👨‍✈️ **Дежурные на сегодня:**\n\n"
        for duty in duties:
            sector_name = duty.get("sector_name", f"Сектор {duty['sector_id']}")
            user_name = duty.get("user_name", "Неизвестно")
            message_text += f"• {sector_name}: {user_name}\n"

    await callback.message.edit_text(
        message_text, reply_markup=get_duty_main_keyboard(), parse_mode="Markdown"
    )
    await state.set_state(DutyStates.waiting_for_action)


# ========== СТАТИСТИКА ==========


@admin_only
async def duty_stats_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать просмотр статистики - запросить сектор"""
    await callback.answer()

    sectors_data = await api_client.get_sectors()
    if "error" in sectors_data or not sectors_data.get("sectors"):
        await callback.message.edit_text(
            "❌ Не удалось получить список секторов.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    sectors = sectors_data["sectors"]
    keyboard = get_sector_selection_keyboard(sectors, action_prefix="duty_stats_sector")

    await callback.message.edit_text(
        "🏢 **Выберите сектор** для просмотра статистики дежурств:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_stats_sector(callback: types.CallbackQuery, state: FSMContext):
    """Показать статистику по сектору"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    current_year = datetime.now().year

    # Получаем сводку статистики
    stats_summary = await api_client.get_sector_statistics_summary(
        sector_id, year=current_year
    )

    if "error" in stats_summary:
        await callback.message.edit_text(
            f"❌ Ошибка получения статистики: {stats_summary['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    if not stats_summary:
        await callback.message.edit_text(
            f"📊 Нет данных по статистике для сектора {sector_id} за {current_year} год.",
            reply_markup=get_duty_main_keyboard(),
        )
        await state.set_state(DutyStates.waiting_for_action)
        return

    # Получаем название сектора
    sectors_data = await api_client.get_sectors()
    sector_name = f"Сектор {sector_id}"
    if "error" not in sectors_data:
        for sector in sectors_data.get("sectors", []):
            if sector.get("sector_id") == sector_id:
                sector_name = sector.get("name", sector_name)
                break

    message_text = f"📊 **Статистика дежурств {sector_name} за {current_year} год**\n\n"
    for stat in stats_summary:
        in_pool_mark = "✅" if stat.get("in_pool") else "❌"
        last_date = stat.get("last_duty_date", "никогда")
        if last_date and last_date != "никогда":
            last_date = (
                last_date[:10]
                if isinstance(last_date, str)
                else last_date.strftime("%d.%m.%Y")
            )
        message_text += (
            f"{in_pool_mark} {stat['user_name']}\n"
            f"   • Смен: {stat['total_duties']}\n"
            f"   • Последняя: {last_date}\n\n"
        )

    await callback.message.edit_text(
        message_text, reply_markup=get_duty_main_keyboard(), parse_mode="Markdown"
    )
    await state.set_state(DutyStates.waiting_for_action)


# ========== ВСПОМОГАТЕЛЬНЫЕ ==========


async def duty_menu(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню дежурств"""
    await callback.answer()
    keyboard = get_duty_main_keyboard()
    await callback.message.edit_text(
        "👨‍✈️ **УПРАВЛЕНИЕ ДЕЖУРСТВАМИ АДМИНИСТРАТОРОВ**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_action)


async def duty_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await callback.answer("Действие отменено")
    await duty_menu(callback, state)


async def duty_back_to_admin(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в админ-панель"""
    await callback.answer()

    # Удаляем текущее сообщение с inline-клавиатурой
    try:
        await callback.message.delete()
    except:
        pass  # Игнорируем ошибки удаления

    # Отправляем новое сообщение с Reply-клавиатурой
    keyboard = get_admin_keyboard()
    await callback.message.answer(
        "👑 **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(AdminStates.waiting_admin_command)
