"""
Форматирование сообщений
"""

def format_report(report_data: dict) -> str:
    """Форматировать данные отчета в читаемый вид"""
    if "error" in report_data:
        return f"❌ Ошибка при получении отчета:\n{report_data['error']}"
    
    summary = report_data.get("status_summary", {})
    users = report_data.get("users", [])
    total = report_data.get("total", 0)
    sector_info = report_data.get("sector_info", {})
    
    # Определяем заголовок
    sector_name = sector_info.get("name") if sector_info else None
    sector_id = sector_info.get("sector_id") if sector_info else None
    
    if sector_name:
        header = f"📊 **ОТЧЕТ: {sector_name}**\n\n"
    elif sector_id:
        header = f"📊 **ОТЧЕТ: Сектор {sector_id}**\n\n"
    else:
        header = "📊 **ОТЧЕТ ПО ВСЕМ СЕКТОРАМ**\n\n"
    
    message = header
    
    # Сводка по статусам
    message += "**Статистика:**\n"
    status_emojis = {
        "здоров": "✅",
        "болен": "🤒", 
        "отпуск": "🏖",
        "удаленка": "🏠",
        "отгул": "📋",
        "учеба": "📚",
        "не указан": "❓"
    }
    
    for status, count in summary.items():
        if status:  # Пропускаем пустые статусы
            emoji = status_emojis.get(status, "📝")
            message += f"{emoji} {status.capitalize()}: {count}\n"
    
    message += f"\n**Всего сотрудников:** {total}\n"
    
    # Список сотрудников
    if users:
        message += "\n**Сотрудники:**\n"
        for i, user in enumerate(users[:15], 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Без имени"
            status = user.get('status', 'не указан')
            disease = user.get('disease', '')
            
            emoji = status_emojis.get(status, "❓")
            
            message += f"{i}. {emoji} {name}"
            if status and status != "не указан":
                message += f" - {status}"
            if disease:
                message += f" ({disease})"
            message += "\n"
        
        if len(users) > 15:
            message += f"\n... и еще {len(users) - 15} сотрудников"
    
    return message

def format_user_info(user_data: dict,report_data:dict) -> str:
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
        "учеба": "📚"
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
        #sector_id = sector_info.get("sector_id") if sector_info else None
        
        message += f"\n**Настройки доступа:**\n"
        message += f"📊 Отчеты: {'✅ Включены' if enable_report else '❌ Выключены'}\n"
        message += f"👑 Админ: {'✅ Да' if enable_admin else '❌ Нет'}\n"
        message += f"🏢 Сектор: {sector_name}\n"
    
    # Даты
    created_at = user_data.get("created_at", "")
    
    if created_at:
        created_str = str(created_at)
        if '.' in created_str:
            created_str = created_str.split('.')[0]
        message += f"\n📅 Зарегистрирован: {created_str}"
    
    return message