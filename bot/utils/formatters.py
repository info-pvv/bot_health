"""
Форматирование сообщений
"""

# bot/utils/formatters.py

from typing import Optional, Dict, Any
from datetime import datetime


def format_report(report_data: dict, duty_info: Optional[dict] = None) -> str:
    """
    Форматирование отчета с информацией о дежурном

    Args:
        report_data: Данные отчета из API
        duty_info: Информация о дежурном администраторе

    Returns:
        Отформатированный текст отчета
    """
    # Информация о секторе
    sector_info = report_data.get("sector_info", {})
    sector_text = ""
    if sector_info:
        sector_name = sector_info.get("name", "Неизвестный сектор")
        sector_text = f"**{sector_name}**\n\n"

    # Информация о дежурном администраторе
    duty_text = ""
    if duty_info:
        duty_text = "👨‍✈️ **Дежурный администратор:**\n"
        if duty_info.get("multiple"):
            # Несколько дежурных (для общего отчета)
            for d in duty_info["duties"]:
                duty_text += f"  • {d['sector_name']}: {d['user_name']}\n"
        else:
            # Один дежурный
            duty_text += f"  • {duty_info.get('user_name', 'Неизвестно')}\n"
        duty_text += "\n"

    # Статистика
    status_summary = report_data.get("status_summary", {})
    total = report_data.get("total", 0)

    if not status_summary:
        return f"{sector_text}{duty_text}📊 Нет данных для отчета"

    # Заголовок
    current_date = datetime.now().strftime("%d.%m.%Y")
    report = f"📋 **ОТЧЕТ О СОСТОЯНИИ ЗДОРОВЬЯ**\n"
    report += f"📅 {current_date}\n\n"

    report += sector_text
    report += duty_text

    # Статистика по статусам
    report += "📊 **Статистика:**\n"

    status_emojis = {
        "здоров": "✅",
        "болен": "🤒",
        "отпуск": "🏖",
        "удаленка": "🏠",
        "отгул": "📋",
        "учеба": "📚",
        "не указан": "❓",
    }

    for status, count in sorted(
        status_summary.items(), key=lambda x: x[1], reverse=True
    ):
        emoji = status_emojis.get(status, "📝")
        percentage = (count / total * 100) if total > 0 else 0
        report += f"{emoji} **{status}:** {count} чел. ({percentage:.1f}%)\n"

    report += f"\n👥 **Всего сотрудников:** {total}\n\n"

    # Детальный список сотрудников
    report += "📋 **Список сотрудников:**\n"
    report += "```\n"

    users = report_data.get("users", [])
    for user in users:
        first_name = user.get("first_name", "").ljust(15)
        last_name = user.get("last_name", "").ljust(15)
        status = user.get("status", "не указан").ljust(10)
        disease = user.get("disease", "")

        if disease:
            line = f"{last_name} {first_name} - {status} ({disease})"
        else:
            line = f"{last_name} {first_name} - {status}"

        report += line[:50] + "\n"

    report += "```"

    return report


def format_duty_info(duty_data: dict) -> str:
    """Форматирование информации о дежурном"""
    duties = duty_data.get("duties", [])

    if not duties:
        return "👨‍✈️ **Дежурный администратор:**\n  • Не назначен\n\n"

    text = "👨‍✈️ **Дежурный администратор:**\n"
    for duty in duties:
        sector_name = duty.get("sector_name", f"Сектор {duty['sector_id']}")
        user_name = duty.get("user_name", "Неизвестно")
        text += f"  • {sector_name}: {user_name}\n"

    text += "\n"
    return text


def format_user_info(user_data: dict, report_data: dict) -> str:
    """Форматировать информацию о пользователе"""
    if "error" in user_data:
        return f"❌ Ошибка: {user_data['error']}"

    message = "👤 **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ**\n\n"

    # Основная информация
    first_name = user_data.get("first_name", "Не указано")
    last_name = user_data.get("last_name", "Не указано")
    username = user_data.get("username", "Не указано")
    user_id = user_data.get("user_id", "Не указано")

    message += f"**ID:** {user_id}\n"
    message += f"**Имя:** {first_name}\n"
    message += f"**Фамилия:** {last_name}\n"
    message += f"**Username:** {username}\n"

    # Информация о здоровье
    health_info = user_data.get("health_info", {})
    disease_info = user_data.get("disease_info", {})

    status = health_info.get("status") if health_info else "не указан"
    disease = disease_info.get("disease") if disease_info else "не указано"

    status_emojis = {
        "здоров": "✅",
        "болен": "🤒",
        "отпуск": "🏖",
        "удаленка": "🏠",
        "отгул": "📋",
        "учеба": "📚",
    }

    emoji = status_emojis.get(status, "❓")
    message += f"\n**Статус здоровья:** {emoji} {status if status else 'не указан'}\n"

    if disease and disease != "не указано":
        message += f"**Заболевание:** {disease}\n"

    # Информация о правах
    status_info = user_data.get("status_info", {})
    if status_info:
        enable_report = status_info.get("enable_report", False)
        enable_admin = status_info.get("enable_admin", False)
        sector_id = status_info.get("sector_id", "Не указан")

        sector_info = report_data.get("sector_info", {})

        # Определяем заголовок
        sector_name = sector_info.get("name") if sector_info else None
        # sector_id = sector_info.get("sector_id") if sector_info else None

        message += f"\n**Настройки доступа:**\n"
        message += f"📊 Отчеты: {'✅ Включены' if enable_report else '❌ Выключены'}\n"
        message += f"👑 Админ: {'✅ Да' if enable_admin else '❌ Нет'}\n"
        message += f"🏢 Сектор: {sector_name}\n"

    # Даты
    created_at = user_data.get("created_at", "")

    if created_at:
        created_str = str(created_at)
        if "." in created_str:
            created_str = created_str.split(".")[0]
        message += f"\n📅 Зарегистрирован: {created_str}"

    return message
