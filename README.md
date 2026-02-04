# Health Tracking Bot 🤖

Telegram бот для отслеживания статусов здоровья сотрудников с FastAPI бэкендом и PostgreSQL базой данных.

## 🚀 Функционал

- 📊 Отслеживание статусов здоровья сотрудников
- 🏢 Работа с секторами/отделами
- 📈 Генерация отчетов
- 👤 Регистрация пользователей
- 💊 Отметка статусов здоровья

## 🛠 Технологии

- **Python 3.11+**
- **Aiogram 3.x** - Telegram Bot Framework
- **FastAPI** - REST API Framework
- **SQLAlchemy** - ORM
- **PostgreSQL** - База данных
- **Asyncpg** - Асинхронный PostgreSQL драйвер

## 📦 Установка

### 1. Клонирование репозитория
```bash
git clone https://github.com/info-pvv/bot_health.git
cd bot_health
2. Создание виртуального окружения
bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
3. Установка зависимостей
bash
pip install -r requirements.txt
4. Настройка окружения
Создайте файл .env на основе .env.example:

bash
cp .env.example .env
Отредактируйте .env файл:

env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=health_tracker

# Telegram
TELEGRAM_TOKEN=your_bot_token_here

# API
API_BASE_URL=http://localhost:8000
SECRET_KEY=your_secret_key_here
5. Настройка базы данных
bash
# Запустите PostgreSQL
# Создайте миграции
python migrations/manage.py up
6. Запуск приложения
bash
# Запуск API сервера (в одном терминале)
python main.py

# Запуск Telegram бота (в другом терминале)
python bot_v3.py
📁 Структура проекта
text
bot_health/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── admin.py
│   │   │   ├── health.py
│   │   │   └── users.py
│   │   └── __init__.py
│   ├── core/
│   │   └── config.py
│   ├── models/
│   │   ├── database.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── admin.py
│   │   ├── health.py
│   │   └── user.py
│   ├── services/
│   │   ├── admin_service.py
│   │   ├── health_service.py
│   │   └── user_service.py
│   └── api_client.py
├── migrations/
│   ├── versions/
│   └── manage.py
├── bot_v3.py
├── main.py
├── config.py
├── requirements.txt
├── .env.example
└── README.md
🔧 Команды бота
/start - Начать работу

/help - Помощь

📊 Отчет по моему сектору

📈 Отчет по всем секторам

🏢 Список секторов

💊 Отметить статус здоровья

👤 Моя информация

📊 Статусы здоровья
✅ Здоров

🤒 Болен (требуется указать заболевание)

🏖 Отпуск

🏠 Удаленка

📋 Отгул

📚 Учеба

🐛 Отладка
Логи хранятся в стандартном выводе. Для отладки API используйте:

http://localhost:8000/docs - Swagger документация

http://localhost:8000/redoc - ReDoc документация

📄 Лицензия
MIT