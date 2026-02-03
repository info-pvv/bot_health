# Employee Health Tracker

Система для отслеживания статусов здоровья сотрудников через Telegram бот и REST API.

## 🚀 Быстрый старт

### 1. Настройка окружения

`powershell
# Клонируйте проект (если нужно)
# git clone <repository-url>
# cd employee-health-tracker

# Инициализируйте проект
.\init-project.ps1

# Скопируйте файл окружения и настройте его
Copy-Item .env.example .env
# Отредактируйте .env файл, указав свои настройки
`

### 2. Настройка базы данных

#### Вариант A: С использованием Docker (рекомендуется)

`powershell
# Запустите базу данных и вспомогательные сервисы
docker-compose up -d postgres pgadmin

# Инициализируйте базу данных
.\init-database.ps1 -DockerMode
`

#### Вариант B: Без Docker

1. Установите PostgreSQL 15+
2. Создайте базу данных
3. Настройте параметры подключения в .env
4. Выполните:
`powershell
.\init-database.ps1
`

### 3. Установка зависимостей

`powershell
# Создайте виртуальное окружение (рекомендуется)
python -m venv venv

# Активируйте виртуальное окружение
# Для Windows:
.\venv\Scripts\activate
# Для Linux/Mac:
# source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
`

### 4. Запуск приложений

#### Запуск REST API:
`powershell
uvicorn main:app --reload
`
API будет доступно по адресу: http://localhost:8000
Документация: http://localhost:8000/docs

#### Запуск Telegram бота:
`powershell
python bot.py
`

#### Запуск всего через Docker:
`powershell
docker-compose up -d
`

## 📁 Структура проекта

`
employee-health-tracker/
├── app/                    # Основное приложение
│   ├── api/               # REST API endpoints
│   ├── core/              # Конфигурация и утилиты
│   ├── models/            # SQLAlchemy модели
│   ├── schemas/           # Pydantic схемы
│   └── services/          # Бизнес-логика
├── alembic/               # Миграции базы данных
├── scripts/               # Вспомогательные скрипты
└── tests/                 # Тесты
`

## 🔧 Вспомогательные скрипты

### Инициализация базы данных
`powershell
.\init-database.ps1 [-Reset] [-TestData] [-DockerMode]
`

Параметры:
- -Reset: Удалить и пересоздать базу данных
- -TestData: Добавить тестовые данные
- -DockerMode: Использовать Docker-контейнеры

### Генерация тестовых данных
`powershell
.\populate-test-data.ps1 [-UserCount 100] [-ClearExisting]
`

### Полная инициализация проекта
`powershell
.\init-project.ps1 [-UseDocker] [-InitDB]
`

## 📊 API Endpoints

### Пользователи
- GET /users/ - Список пользователей
- GET /users/{user_id} - Информация о пользователе
- POST /users/ - Создание пользователя
- PUT /users/{user_id} - Обновление пользователя

### Статусы здоровья
- GET /health/report - Отчет по статусам
- GET /health/sectors - Список секторов

### Администрирование
- PUT /users/{user_id}/status - Обновление статуса пользователя

## 🤖 Telegram Bot

### Команды бота
- /start - Запустить бота
- /cancel - Отменить текущее действие
- /report - Получить отчет

### Основные функции
1. Отметка статуса здоровья
2. Отчеты по сотрудникам
3. Администрирование пользователей
4. Автоматические ежедневные отчеты

## 🐳 Docker

### Сервисы
- **postgres**: База данных PostgreSQL
- **api**: REST API приложение
- **bot**: Telegram бот
- **pgadmin**: Веб-интерфейс для управления БД

### Команды
`powershell
# Запуск всех сервисов
docker-compose up -d

# Остановка всех сервисов
docker-compose down

# Просмотр логов
docker-compose logs -f api
docker-compose logs -f bot

# Пересборка образов
docker-compose build --no-cache
`

## 🔒 Безопасность

1. Все пароли и токены хранятся в .env файле
2. Файл .env добавлен в .gitignore
3. Используется JWT для аутентификации API
4. Telegram бот использует токен из окружения

## 🧪 Тестирование

`powershell
# Запуск тестов
pytest tests/

# Запуск тестов с покрытием
pytest tests/ --cov=app --cov-report=html
`

## 📈 Мониторинг

### Health Check
- API: http://localhost:8000/health
- База данных: Проверяется через healthcheck в docker-compose

### Логирование
- Логи хранятся в стандартном выводе
- Уровень логирования настраивается через LOG_LEVEL

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Добавьте тесты
4. Отправьте Pull Request

## 📄 Лицензия

MIT
