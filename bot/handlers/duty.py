# bot/handlers/duty.py
"""
Обработчики для системы дежурных администраторов
"""
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
from datetime import datetime, timedelta, date
import calendar

from bot.imports import (
    admin_only,
    api_client,
    DutyStates,
    ActionStates,
    AdminStates,
)
from bot.keyboards.duty import (
    get_duty_main_keyboard,
    get_sector_selection_keyboard,
    get_user_selection_keyboard_duty,
    get_week_confirmation_keyboard,
    get_duty_pool_actions_keyboard,
    get_duty_back_keyboard,
    get_duty_period_keyboard,
    get_working_days_keyboard,
    get_schedule_view_keyboard,
    get_month_navigation_keyboard,
    get_year_navigation_keyboard,
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

    pool_data = await api_client.get_duty_pool(sector_id, active_only=True)

    if "error" in pool_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения пула: {pool_data['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    items = pool_data.get("items", [])

    sector_name = f"Сектор {sector_id}"
    if items and len(items) > 0:
        sector_name = items[0].get("sector_name", sector_name)

    if not items:
        message_text = f"📭 Пул дежурных для **{sector_name}** пуст."
    else:
        message_text = f"👥 **Пул дежурных для {sector_name}:**\n\n"
        for item in items:
            user_name = item.get("user_name", f"ID {item['user_id']}")
            added_at = (
                item.get("added_at", "")[:10] if item.get("added_at") else "неизвестно"
            )
            message_text += f"• {user_name} (с {added_at})\n"

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

    eligible_users = await api_client.get_eligible_users(sector_id=sector_id)

    if "error" in eligible_users:
        await callback.message.edit_text(
            f"❌ Ошибка получения пользователей: {eligible_users['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    if isinstance(eligible_users, list):
        users = eligible_users
    else:
        users = (
            eligible_users.get("users", []) if isinstance(eligible_users, dict) else []
        )

    if not users:
        await callback.message.edit_text(
            f"❌ Нет пользователей, которые могут быть дежурными, для сектора {sector_id}.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    keyboard = get_user_selection_keyboard_duty(
        users, sector_id, action_prefix="duty_add_confirm"
    )

    await callback.message.edit_text(
        f"👤 **Выберите пользователя** для добавления в пул сектора {sector_id}:",
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

    if sector_id < 0:
        logger.error(f"Получен отрицательный sector_id: {sector_id}")
        await callback.message.edit_text(
            f"❌ Ошибка: некорректный ID сектора.",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    today = date.today()
    days_until_monday = (0 - today.weekday()) % 7
    if days_until_monday == 0:
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
        f"Будут назначены дежурства на даты:\n{week_dates_str}",
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


# ========== НАЗНАЧЕНИЕ НА РАЗНЫЕ ПЕРИОДЫ ==========


@admin_only
async def duty_assign_period_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать назначение на период - запросить сектор"""
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
        sectors, action_prefix="duty_period_sector"
    )

    await callback.message.edit_text(
        "🏢 **Выберите сектор** для назначения дежурного:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_period_sector_selected(callback: types.CallbackQuery, state: FSMContext):
    """Сектор выбран, показать выбор периода"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    await state.update_data(selected_sector_id=sector_id)

    keyboard = get_duty_period_keyboard(sector_id)

    await callback.message.edit_text(
        f"📅 **Выберите период** для сектора {sector_id}:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_period_selection)


async def duty_period_selected(callback: types.CallbackQuery, state: FSMContext):
    """Период выбран, назначаем дежурство"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    period = data_parts[1]
    sector_id = int(data_parts[2])

    today = date.today()

    if period == "day":
        start_date = today
        period_name = "день"
        period_text = "сегодня"
    elif period == "week":
        days_until_monday = (0 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        start_date = today + timedelta(days=days_until_monday)
        period_name = "неделю"
        period_text = f"с {start_date.strftime('%d.%m.%Y')}"
    elif period == "month":
        if today.month == 12:
            start_date = date(today.year + 1, 1, 1)
        else:
            start_date = date(today.year, today.month + 1, 1)
        period_name = "месяц"
        period_text = f"месяц с {start_date.strftime('%d.%m.%Y')}"
    elif period == "year":
        start_date = date(today.year + 1, 1, 1)
        period_name = "год"
        period_text = f"год с {start_date.strftime('%d.%m.%Y')}"
    else:
        await callback.message.edit_text(
            "❌ Неверный период.", reply_markup=get_duty_back_keyboard()
        )
        return

    await callback.message.edit_text(
        f"⏳ Назначаю дежурство на {period_text}...", reply_markup=None
    )

    result = await api_client.assign_duty_for_period(
        sector_id=sector_id,
        period=period,
        start_date=start_date.isoformat(),
        created_by=callback.from_user.id,
    )

    if "error" in result:
        await callback.message.edit_text(
            f"❌ Ошибка назначения: {result['error']}",
            reply_markup=get_duty_main_keyboard(),
        )
    elif result.get("assigned_user_id"):
        assigned_user = result.get(
            "assigned_user_name", f"ID {result['assigned_user_id']}"
        )
        start = result.get("start_date", start_date.isoformat())
        end = result.get("end_date", "")
        days_count = result.get("days_count", 0)

        if isinstance(start, str):
            start = start[:10]
        if isinstance(end, str) and end:
            end = end[:10]

        text = f"✅ **Дежурство успешно назначено!**\n\n"
        text += f"Сектор: {sector_id}\n"
        text += f"Период: {period_name}\n"
        text += f"Даты: {start}"
        if end:
            text += f" - {end}"
        text += f"\nДежурный: {assigned_user}\n"
        text += f"Всего дней: {days_count}"

        await callback.message.edit_text(
            text, reply_markup=get_duty_main_keyboard(), parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"⚠️ {result.get('message', 'Не удалось назначить дежурство.')}",
            reply_markup=get_duty_main_keyboard(),
        )

    await state.set_state(DutyStates.waiting_for_action)


# ========== АВТО-ПЛАНИРОВАНИЕ НА ГОД ==========


@admin_only
async def duty_auto_plan_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать авто-планирование на год"""
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
        sectors, action_prefix="duty_plan_year_sector"
    )

    await callback.message.edit_text(
        "🏢 **Выберите сектор** для автоматического планирования на год:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def duty_plan_year_sector(callback: types.CallbackQuery, state: FSMContext):
    """Сектор выбран, выбрать тип дней"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    current_year = datetime.now().year
    next_year = current_year + 1

    await state.update_data(plan_sector_id=sector_id, plan_year=next_year)

    keyboard = get_working_days_keyboard(sector_id, next_year)

    await callback.message.edit_text(
        f"📅 **Планирование дежурств на {next_year} год**\n\n"
        f"Сектор: {sector_id}\n\n"
        f"Выберите режим планирования:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_plan_confirmation)


async def duty_plan_execute(callback: types.CallbackQuery, state: FSMContext):
    """Выполнить планирование на год"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 4:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    year = int(data_parts[2])
    working_days_only = data_parts[3].lower() == "true"

    await callback.message.edit_text(
        f"⏳ Выполняю автоматическое планирование на {year} год...\n"
        f"Это может занять некоторое время.",
        reply_markup=None,
    )

    result = await api_client.plan_yearly_schedule(
        sector_id=sector_id, year=year, working_days_only=working_days_only
    )

    if "error" in result:
        await callback.message.edit_text(
            f"❌ Ошибка планирования: {result['error']}",
            reply_markup=get_duty_main_keyboard(),
        )
    else:
        assignments = result.get("assignments", [])
        days_type = "рабочие дни" if working_days_only else "все дни"

        text = f"✅ **Планирование на {year} год завершено!**\n\n"
        text += f"Сектор: {sector_id}\n"
        text += f"Тип дней: {days_type}\n"
        text += f"Всего назначений: {result.get('total_assignments', 0)}\n\n"

        await callback.message.edit_text(
            text, reply_markup=get_duty_main_keyboard(), parse_mode="Markdown"
        )

    await state.set_state(DutyStates.waiting_for_action)


# ========== ПРОСМОТР ГРАФИКОВ ==========


@admin_only
async def duty_view_schedules_start(callback: types.CallbackQuery, state: FSMContext):
    """Начать просмотр графиков - запросить сектор"""
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
        sectors, action_prefix="schedule_view_sector"
    )

    await callback.message.edit_text(
        "🏢 **Выберите сектор** для просмотра графиков дежурств:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_sector_selection)


async def schedule_view_sector_selected(
    callback: types.CallbackQuery, state: FSMContext
):
    """Сектор выбран, показать меню выбора графика"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    await state.update_data(view_sector_id=sector_id)

    keyboard = get_schedule_view_keyboard(sector_id)

    await callback.message.edit_text(
        f"📊 **Выберите тип графика** для сектора {sector_id}:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(DutyStates.waiting_for_action)


async def schedule_view_week(callback: types.CallbackQuery, state: FSMContext):
    """Показать график на неделю"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[2])

    week_data = await api_client.get_week_schedule(sector_id=sector_id)

    if "error" in week_data:
        await safe_edit_message(
            callback.message,
            f"❌ Ошибка получения данных: {week_data['error']}",
            get_duty_back_keyboard(),
        )
        return

    text = "📅 **График дежурств на неделю**\n\n"
    text += f"Период: {week_data['start_date']} - {week_data['end_date']}\n"
    text += "=" * 30 + "\n\n"

    for day_data in week_data["data"]:
        if day_data["is_today"]:
            emoji = "🔴 "
        elif day_data["is_weekend"]:
            emoji = "🟡 "
        else:
            emoji = "⚪️ "

        text += f"{emoji} *{day_data['day_name']} ({day_data['date']})*\n"

        if day_data["duties"]:
            for duty in day_data["duties"]:
                text += f"  👤 {duty['user_name']}\n"
        else:
            text += "  ❌ Нет дежурного\n"
        text += "\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="🔄 Другая неделя", callback_data=f"schedule_week_other:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="🔙 Назад", callback_data=f"schedule_view_menu:{sector_id}"
        ),
    )

    await safe_edit_message(callback.message, text, builder.as_markup(), "Markdown")


async def schedule_view_month(callback: types.CallbackQuery, state: FSMContext):
    """Показать график на месяц"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[2])
    today = date.today()

    month_data = await api_client.get_month_schedule(
        sector_id=sector_id, year=today.year, month=today.month
    )

    if "error" in month_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения данных: {month_data['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    await show_month_schedule(callback.message, month_data, sector_id)


async def show_month_schedule(message, month_data, sector_id):
    """Отобразить месячный календарь"""
    text = (
        f"📆 **График дежурств на {month_data['month_name']} {month_data['year']}**\n\n"
    )

    text += "```\n"
    text += "Пн Вт Ср Чт Пт Сб Вс\n"
    text += "-" * 27 + "\n"

    for week in month_data["calendar"]:
        week_line = ""
        for day in week:
            if day["day"] is None:
                week_line += "   "
            else:
                if day["duties"]:
                    if day["is_today"]:
                        week_line += "🔴"
                    else:
                        week_line += "✅"
                else:
                    if day["is_weekend"]:
                        week_line += "⬜"
                    else:
                        week_line += "❌"
                week_line += f"{day['day']:2d} "
        text += week_line + "\n"
    text += "```\n\n"

    text += "**Легенда:**\n"
    text += "✅ - есть дежурный\n"
    text += "❌ - нет дежурного\n"
    text += "🔴 - сегодня\n"
    text += "⬜ - выходной\n\n"

    text += "**Детали:**\n"
    for week in month_data["calendar"]:
        for day in week:
            if day["day"] and day["duties"]:
                date_str = f"{day['day']:2d}.{month_data['month']:02d}"
                for duty in day["duties"]:
                    text += f"• {date_str}: {duty['user_name']}\n"

    keyboard = get_month_navigation_keyboard(
        sector_id, month_data["year"], month_data["month"]
    )

    await safe_edit_message(message, text, keyboard, "Markdown")


async def schedule_month_navigate(callback: types.CallbackQuery, state: FSMContext):
    """Навигация по месяцам"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 4:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    year = int(data_parts[2])
    month = int(data_parts[3])

    month_data = await api_client.get_month_schedule(
        sector_id=sector_id, year=year, month=month
    )

    if "error" in month_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения данных: {month_data['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    await show_month_schedule(callback.message, month_data, sector_id)


async def schedule_view_year(callback: types.CallbackQuery, state: FSMContext):
    """Показать годовую статистику"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[2])
    current_year = date.today().year

    year_data = await api_client.get_year_schedule(
        sector_id=sector_id, year=current_year
    )

    if "error" in year_data:
        await callback.message.edit_text(
            f"❌ Ошибка получения данных: {year_data['error']}",
            reply_markup=get_duty_back_keyboard(),
        )
        return

    await show_year_schedule(callback.message, year_data, sector_id)


async def show_year_schedule(message, year_data, sector_id):
    """Отобразить годовую статистику"""
    text = f"📊 **Годовая статистика дежурств {year_data['year']}**\n\n"
    text += f"Всего дежурств: {year_data['total_duties']}\n"
    text += f"В среднем в месяц: {year_data['average_per_month']:.1f}\n\n"

    text += "**Распределение по месяцам:**\n"
    text += "```\n"
    max_duties = (
        max(m["total_duties"] for m in year_data["months"])
        if year_data["months"]
        else 0
    )
    scale = 20 / max_duties if max_duties > 0 else 1

    for month in year_data["months"]:
        bar_length = int(month["total_duties"] * scale)
        bar = "█" * bar_length
        text += f"{month['month_name'][:3]}: {bar} {month['total_duties']}\n"
    text += "```\n\n"

    if year_data["top_users"]:
        text += "**Топ-5 дежурных года:**\n"
        for i, user in enumerate(year_data["top_users"], 1):
            text += f"{i}. {user['user_name']} - {user['count']} деж.\n"

    keyboard = get_year_navigation_keyboard(sector_id, year_data["year"])

    try:
        # Пытаемся отредактировать сообщение
        await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception as e:
        # Если ошибка "message is not modified", игнорируем её
        if "message is not modified" in str(e).lower():
            logger.debug("Сообщение не изменилось, пропускаем")
            # Можно отправить уведомление, но не обязательно
            await message.answer("🔄 Данные не изменились", show_alert=False)
        else:
            # Если другая ошибка - пробрасываем дальше
            raise e


async def safe_edit_message(message, text, reply_markup=None, parse_mode="Markdown"):
    """
    Безопасно редактирует сообщение, игнорируя ошибку "message is not modified"
    """
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception as e:
        error_str = str(e).lower()
        if "message is not modified" in error_str:
            logger.debug("Сообщение не изменилось, пропускаем")
            return False
        else:
            # Если это другая ошибка - пробрасываем
            raise e


async def schedule_year_navigate(callback: types.CallbackQuery, state: FSMContext):
    """Навигация по годам"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await safe_edit_message(
            callback.message, "❌ Ошибка данных.", get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[1])
    year = int(data_parts[2])

    # Показываем индикатор загрузки
    await safe_edit_message(
        callback.message, f"⏳ Загружаю данные за {year} год...", None
    )

    year_data = await api_client.get_year_schedule(sector_id=sector_id, year=year)

    if "error" in year_data:
        await safe_edit_message(
            callback.message,
            f"❌ Ошибка получения данных: {year_data['error']}",
            get_duty_back_keyboard(),
        )
        return

    await show_year_schedule(callback.message, year_data, sector_id)


async def schedule_view_stats(callback: types.CallbackQuery, state: FSMContext):
    """Показать статистику в виде графиков"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.message.edit_text(
            "❌ Ошибка данных.", reply_markup=get_duty_back_keyboard()
        )
        return

    sector_id = int(data_parts[2])

    stats_data = await api_client.get_duty_statistics_chart(sector_id=sector_id)

    if "error" in stats_data:
        await safe_edit_message(
            callback.message,
            f"❌ Ошибка получения статистики: {stats_data['error']}",
            get_duty_back_keyboard(),
        )
        return

    text = f"📈 **Статистика дежурств {stats_data['year']}**\n\n"
    text += f"Всего дежурств: {stats_data['total']}\n\n"

    text += "**По месяцам:**\n"
    text += "```\n"
    monthly = stats_data["monthly"]
    max_val = max(monthly["data"]) if monthly["data"] else 0
    scale = 20 / max_val if max_val > 0 else 1

    for i, (label, value) in enumerate(zip(monthly["labels"], monthly["data"])):
        bar = "█" * int(value * scale)
        text += f"{label[:3]}: {bar} {value}\n"
    text += "```\n\n"

    text += "**По дням недели:**\n"
    text += "```\n"
    weekly = stats_data["weekly"]
    max_val = max(weekly["data"]) if weekly["data"] else 0
    scale = 20 / max_val if max_val > 0 else 1

    for label, value in zip(weekly["labels"], weekly["data"]):
        bar = "█" * int(value * scale)
        text += f"{label}: {bar} {value}\n"
    text += "```\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="🔄 Другой год", callback_data=f"schedule_view_stats_year:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="🔙 Назад", callback_data=f"schedule_view_menu:{sector_id}"
        ),
    )

    await safe_edit_message(callback.message, text, builder.as_markup(), "Markdown")


async def schedule_week_other(callback: types.CallbackQuery, state: FSMContext):
    """Выбрать другую неделю (заглушка)"""
    await callback.answer("Функция выбора другой недели в разработке")
    # Здесь можно добавить логику выбора конкретной недели


async def schedule_view_stats_year(callback: types.CallbackQuery, state: FSMContext):
    """Выбрать другой год для статистики (заглушка)"""
    await callback.answer("Функция выбора года в разработке")
    # Здесь можно добавить логику выбора года


async def schedule_view_menu(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в меню выбора графика"""
    await callback.answer()
    data_parts = callback.data.split(":")
    if len(data_parts) < 2:
        data = await state.get_data()
        sector_id = data.get("view_sector_id")
        if not sector_id:
            await callback.message.edit_text(
                "❌ Ошибка: не найден ID сектора", reply_markup=get_duty_main_keyboard()
            )
            return
    else:
        sector_id = int(data_parts[1])

    keyboard = get_schedule_view_keyboard(sector_id)
    await callback.message.edit_text(
        f"📊 **Выберите тип графика** для сектора {sector_id}:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


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

    text = f"📊 **Статистика дежурств сектора {sector_id} за {current_year} год**\n\n"
    for stat in stats_summary:
        in_pool_mark = "✅" if stat.get("in_pool") else "❌"
        last_date = stat.get("last_duty_date", "никогда")
        if last_date and last_date != "никогда":
            if isinstance(last_date, str):
                last_date = last_date[:10]
            else:
                last_date = last_date.strftime("%d.%m.%Y")
        text += (
            f"{in_pool_mark} {stat['user_name']}\n"
            f"   • Смен: {stat['total_duties']}\n"
            f"   • Последняя: {last_date}\n\n"
        )

    await callback.message.edit_text(
        text, reply_markup=get_duty_main_keyboard(), parse_mode="Markdown"
    )
    await state.set_state(DutyStates.waiting_for_action)


# ========== ПРОВЕРКА ДОСТУПНОСТИ ==========


@admin_only
async def duty_check_availability_start(
    callback: types.CallbackQuery, state: FSMContext
):
    """Начать проверку доступности"""
    await callback.answer()

    await callback.message.edit_text(
        "🔍 **Проверка доступности дежурных**\n\n"
        "Эта функция находится в разработке.",
        reply_markup=get_duty_main_keyboard(),
        parse_mode="Markdown",
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

    try:
        await callback.message.delete()
    except:
        pass

    keyboard = get_admin_keyboard()
    await callback.message.answer(
        "👑 **АДМИНИСТРАТИВНАЯ ПАНЕЛЬ**\n\n" "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await state.set_state(AdminStates.waiting_admin_command)
