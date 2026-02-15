# bot/keyboards/duty.py
"""
Клавиатуры для системы дежурств
"""
import logging
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder  # ← ВАЖНО: правильный импорт
from typing import List, Dict, Optional
from datetime import date

logger = logging.getLogger(__name__)


def get_duty_main_keyboard() -> types.InlineKeyboardMarkup:
    """Главное меню управления дежурствами"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📋 Пул дежурных", callback_data="duty_view_pool"
        ),
        types.InlineKeyboardButton(
            text="➕ Добавить в пул", callback_data="duty_add_to_pool"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="➖ Удалить из пула", callback_data="duty_remove_from_pool"
        ),
        types.InlineKeyboardButton(
            text="📅 Назначить на неделю (авто)", callback_data="duty_assign_week"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="👤 Назначить вручную", callback_data="duty_assign_week_manual"
        ),
        types.InlineKeyboardButton(
            text="👤 Дежурный сегодня", callback_data="duty_today"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="📊 Графики дежурств", callback_data="duty_view_schedules"
        ),
        types.InlineKeyboardButton(
            text="🤖 План на год", callback_data="duty_auto_plan"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад в админку", callback_data="duty_back_to_admin"
        )
    )
    return builder.as_markup()


def get_sector_selection_keyboard(
    sectors: List[Dict], action_prefix: str = "duty_select_sector"
) -> types.InlineKeyboardMarkup:
    """
    Клавиатура для выбора сектора.

    Args:
        sectors: Список секторов [{'sector_id': 1, 'name': 'Название'}, ...]
        action_prefix: Префикс для callback_data (например, "duty_select_sector_add")
    """
    builder = InlineKeyboardBuilder()
    for sector in sectors:
        sector_id = sector.get("sector_id")
        name = sector.get("name", f"Сектор {sector_id}")
        builder.row(
            types.InlineKeyboardButton(
                text=f"{sector_id}. {name}",
                callback_data=f"{action_prefix}:{sector_id}",
            )
        )
    builder.row(
        types.InlineKeyboardButton(text="🔙 Отмена", callback_data="duty_cancel")
    )
    return builder.as_markup()


def get_user_selection_keyboard_duty(
    users: List[Dict], sector_id: int, action_prefix: str = "duty_select_user"
) -> types.InlineKeyboardMarkup:
    """
    Клавиатура для выбора пользователя из списка (для дежурств).

    Args:
        users: Список пользователей с полями user_id, first_name, last_name
        sector_id: ID сектора, для которого выбирается пользователь
        action_prefix: Префикс для callback_data
    """
    builder = InlineKeyboardBuilder()
    for user in users:
        user_id = user.get("user_id")
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        name = f"{first_name} {last_name}".strip()
        if not name:
            name = f"ID {user_id}"

        builder.row(
            types.InlineKeyboardButton(
                text=f"{name[:30]}",
                callback_data=f"{action_prefix}:{sector_id}:{user_id}",
            )
        )
    builder.row(
        types.InlineKeyboardButton(text="🔙 Отмена", callback_data="duty_cancel")
    )
    return builder.as_markup()


def get_week_confirmation_keyboard(
    sector_id: int, week_start: str
) -> types.InlineKeyboardMarkup:
    """Клавиатура для подтверждения назначения на неделю"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"duty_confirm_week:{sector_id}:{week_start}",
        ),
        types.InlineKeyboardButton(text="❌ Отмена", callback_data="duty_cancel"),
    )
    return builder.as_markup()


def get_duty_pool_actions_keyboard(
    sector_id: int, user_id: int
) -> types.InlineKeyboardMarkup:
    """Кнопки действий для конкретной записи в пуле"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Удалить из пула",
            callback_data=f"duty_remove_confirm:{sector_id}:{user_id}",
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад к пулу", callback_data=f"duty_view_pool:{sector_id}"
        )
    )
    return builder.as_markup()


def get_duty_back_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопка возврата в меню дежурств"""
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="duty_menu"))
    return builder.as_markup()


def get_duty_period_keyboard(sector_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора периода дежурства"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📅 На день", callback_data=f"duty_period:day:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="📅 На неделю", callback_data=f"duty_period:week:{sector_id}"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="📅 На месяц", callback_data=f"duty_period:month:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="📅 На год", callback_data=f"duty_period:year:{sector_id}"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🤖 Авто-план на год", callback_data=f"duty_plan_year:{sector_id}"
        ),
    )
    builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="duty_menu"))
    return builder.as_markup()


def get_working_days_keyboard(sector_id: int, year: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора типа дней при планировании на год"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📆 Все дни",
            callback_data=f"duty_plan_execute:{sector_id}:{year}:false",
        ),
        types.InlineKeyboardButton(
            text="💼 Только рабочие",
            callback_data=f"duty_plan_execute:{sector_id}:{year}:true",
        ),
    )
    builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="duty_menu"))
    return builder.as_markup()


def get_schedule_view_keyboard(sector_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора типа графика"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📅 На неделю", callback_data=f"schedule_view:week:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="📆 На месяц", callback_data=f"schedule_view:month:{sector_id}"
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="📊 На год", callback_data=f"schedule_view:year:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="📈 Статистика", callback_data=f"schedule_view:stats:{sector_id}"
        ),
    )
    builder.row(types.InlineKeyboardButton(text="🔙 Назад", callback_data="duty_menu"))
    return builder.as_markup()


def get_month_navigation_keyboard(
    sector_id: int, year: int, month: int
) -> types.InlineKeyboardMarkup:
    """Клавиатура для навигации по месяцам"""
    builder = InlineKeyboardBuilder()

    # Предыдущий месяц
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year = year - 1

    # Следующий месяц
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year = year + 1

    builder.row(
        types.InlineKeyboardButton(
            text="◀ Предыдущий",
            callback_data=f"schedule_month:{sector_id}:{prev_year}:{prev_month}",
        ),
        types.InlineKeyboardButton(
            text="Следующий ▶",
            callback_data=f"schedule_month:{sector_id}:{next_year}:{next_month}",
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔄 Текущий месяц",
            callback_data=f"schedule_month:{sector_id}:{date.today().year}:{date.today().month}",
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад", callback_data=f"schedule_view_menu:{sector_id}"
        )
    )
    return builder.as_markup()


def get_year_navigation_keyboard(
    sector_id: int, year: int
) -> types.InlineKeyboardMarkup:
    """Клавиатура для навигации по годам"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="◀ {0}".format(year - 1),
            callback_data=f"schedule_year:{sector_id}:{year - 1}",
        ),
        types.InlineKeyboardButton(
            text="{0} ▶".format(year + 1),
            callback_data=f"schedule_year:{sector_id}:{year + 1}",
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔄 Текущий год",
            callback_data=f"schedule_year:{sector_id}:{date.today().year}",
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад", callback_data=f"schedule_view_menu:{sector_id}"
        )
    )
    return builder.as_markup()


# bot/keyboards/duty.py - добавьте новые функции


def get_date_selection_keyboard(sector_id: int) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора типа даты"""
    logger.info(f"🔍 Создание клавиатуры для сектора {sector_id}")
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📅 Конкретный день", callback_data=f"duty_ask_custom_date:{sector_id}"
        ),
        types.InlineKeyboardButton(
            text="📆 Конкретная неделя",
            callback_data=f"duty_select_custom_week:{sector_id}",
        ),
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад к списку админов",
            callback_data=f"duty_manual_sector:{sector_id}",
        )
    )
    return builder.as_markup()


def get_week_selection_keyboard(
    sector_id: int, year: int, month: int
) -> types.InlineKeyboardMarkup:
    """Клавиатура для выбора недели в месяце"""
    import calendar
    from datetime import date

    builder = InlineKeyboardBuilder()

    # Получаем календарь на месяц
    cal = calendar.monthcalendar(year, month)

    # Для каждой недели в месяце
    for week_num, week in enumerate(cal, 1):
        # Находим первый и последний день недели
        days = [d for d in week if d != 0]
        if days:
            first_day = days[0]
            last_day = days[-1]
            week_start = date(year, month, first_day)
            week_end = date(year, month, last_day)

            builder.row(
                types.InlineKeyboardButton(
                    text=f"Неделя {week_num}: {week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m')}",
                    callback_data=f"duty_confirm_week:{sector_id}:{week_start.isoformat()}",
                )
            )

    # Навигация по месяцам
    # Предыдущий месяц
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year = year - 1

    # Следующий месяц
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year = year + 1

    # Добавляем строку с навигацией
    builder.row(
        types.InlineKeyboardButton(
            text="◀ Предыдущий",
            callback_data=f"duty_week_month:{sector_id}:{prev_year}:{prev_month}",
        ),
        types.InlineKeyboardButton(
            text=f"{calendar.month_name[month]} {year}", callback_data="current"
        ),
        types.InlineKeyboardButton(
            text="Следующий ▶",
            callback_data=f"duty_week_month:{sector_id}:{next_year}:{next_month}",
        ),
    )

    # Кнопка возврата
    builder.row(
        types.InlineKeyboardButton(
            text="🔙 Назад", callback_data=f"duty_select_custom_day:{sector_id}"
        )
    )

    return builder.as_markup()
