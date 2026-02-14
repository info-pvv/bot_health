# 📊 Employee Health Tracking System

Система для отслеживания состояния здоровья сотрудников с интеграцией Telegram бота и REST API.

## 🚀 Возможности

### 🤖 Telegram Бот

- **Регистрация сотрудников** - простой процесс регистрации через бота
- **Отметка статуса здоровья** - быстрое обновление статуса (здоров, болен, отпуск и т.д.)
- **Просмотр отчетов** - отчеты по секторам в реальном времени
- **Административная панель** - управление пользователями и правами
- **Поиск сотрудников** - поиск по имени, фамилии или username

### 🌐 REST API

- **Полноценный CRUD** - для всех сущностей системы
- **Отчеты** - генерация отчетов по секторам и статусам
- **Управление правами** - API для администрирования
- **Асинхронные операции** - высокая производительность

### ⏰ Автоматизация

- **Рассылка отчетов** - автоматическая отправка по расписанию
- **Ежедневные отчеты** - настраиваемое время рассылки
- **Тестовые уведомления** - для отладки и тестирования

## 🏗️ Архитектура

```text
├── 📁 app/                    # FastAPI приложение
│   ├── 📁 api/routes/        # Маршруты API
│   ├── 📁 models/            # Модели БД (SQLAlchemy)
│   ├── 📁 schemas/           # Pydantic схемы
│   ├── 📁 services/          # Бизнес-логика
│   └── 📁 core/              # Конфигурация
│
├── 📁 bot/                   # Telegram бот
│   ├── 📁 handlers/          # Обработчики сообщений
│   ├── 📁 keyboards/         # Клавиатуры бота
│   ├── 📁 services/          # Сервисы бота
│   ├── 📁 utils/             # Утилиты
│   └── 📁 scheduler/         # Планировщик задач
│
├── 📁 migrations/            # Миграции БД
├── 📄 requirements.txt       # Зависимости
├── 📄 main.py               # Точка входа API
├── 📄 bot_runner.py         # Точка входа бота
└── 📄 .env                  # Конфигурация
```

## 🛠️ Технологии

- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL с asyncpg
- **Telegram Bot**: Aiogram 3.x
- **Scheduler**: APScheduler
- **Async/await**: Полностью асинхронная архитектура
- **Environment**: Python 3.10+

## 📦 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd bot_health
```

### 2. Настройка окружения

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем .env файл
nano .env
```

### 3. Настройка переменных окружения (.env)

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=health_tracker

# Telegram
TELEGRAM_TOKEN=your_bot_token_here

# API
SECRET_KEY=your_secret_key_here
API_BASE_URL=http://localhost:8000

# Scheduler
REPORT_TIME=07:30
REPORT_TIMEZONE=Europe/Moscow
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Инициализация базы данных

```bash
# Создание и настройка БД
python migrations/manage.py up
```

### 6. Запуск приложений

**Запуск REST API:**

```bash
python main.py
```

API будет доступен по адресу: <http://localhost:8000>
Документация Swagger: <http://localhost:8000/docs>

**Запуск Telegram бота:**

```bash
python bot_runner.py
```

### 7. Деплой в Docker (опционально)

```bash
docker-compose up -d
```

## 📋 Основные команды бота

### Для всех пользователей

- `/start` - Начало работы, регистрация
- `/help` - Справка по командам
- `📊 Отчет по моему сектору` - Просмотр отчета
- `💊 Отметить статус здоровья` - Изменить свой статус
- `👤 Моя информация` - Информация о пользователе

### Для администраторов

- `👑 Админ панель` - Панель управления
- `/users` - Список всех пользователей
- `/search Иванов` - Поиск пользователей
- `/user_info ID` - Информация о пользователе
- `/sector_report ID` - Отчет по сектору
- `/toggle_admin ID` - Дать/забрать админ права
- `/test_schedule` - Тест рассылки отчетов

## 🔧 API Endpoints

### Пользователи

- `GET /users/` - Список пользователей
- `GET /users/{user_id}` - Информация о пользователе
- `POST /users/` - Создание пользователя
- `PUT /users/{user_id}` - Обновление пользователя
- `GET /users/search/` - Поиск пользователей

### Отчеты о здоровье

- `GET /health/report` - Отчет по статусам
- `PUT /users/{user_id}/health` - Обновление статуса
- `GET /health/sectors` - Список секторов

### Администрирование

- `PUT /admin/users/{user_id}/toggle-report` - Вкл/выкл отчеты
- `PUT /admin/users/{user_id}/toggle-admin` - Вкл/выкл админа

## 🗄️ Структура базы данных

```sql
users          - Основная информация о пользователях
id_status      - Статусы и права пользователей
fio            - ФИО пользователей
health         - Статусы здоровья
disease        - Заболевания
sectors        - Сектора/отделы
```

## ⚙️ Настройка рассылки отчетов

### Через переменные окружения

```env
REPORT_TIME=07:30          # Время ежедневной рассылки
REPORT_DAYS=0,1,2,3,4      # Дни недели (0=понедельник)
REPORT_ENABLED=true        # Включить/выключить
```

### Через команды бота

```bash
/test_schedule     # Тестовая рассылка
/schedule_info     # Информация о расписании
```

## 🧪 Тестирование

### Запуск тестов API

```bash
pytest tests/ -v
```

### Тестовая рассылка

```bash
# В боте используйте команду
/test_schedule
```

### Проверка работоспособности

1. Откройте <http://localhost:8000/docs> для проверки API
2. Найдите бота в Telegram и отправьте `/start`
3. Проверьте регистрацию и основные функции

## 🔒 Безопасность

- JWT аутентификация (в разработке)
- Валидация всех входных данных
- Защита от SQL-инъекций через ORM
- Разделение прав пользователей и администраторов

## 📈 Мониторинг и логирование

- Подробное логирование всех операций
- Отслеживание ошибок и исключений
- Мониторинг производительности API
- Логи рассылки отчетов

## 🔄 Миграции базы данных

```bash
# Применить миграции
python migrations/manage.py up

# Откатить миграции
python migrations/manage.py down

# Показать статус
python migrations/manage.py status
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Запушьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Смотрите файл `LICENSE` для подробностей.

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Убедитесь что все службы запущены
3. Проверьте настройки в `.env` файле
4. Создайте Issue в репозитории

## 🎯 Быстрый старт для разработчиков

```bash
# 1. Клонируйте проект
git clone <repo>

# 2. Настройте окружение
cp .env.example .env
# отредактируйте .env

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Инициализируйте БД
python migrations/manage.py up

# 5. Запустите в двух терминалах:
# Терминал 1: API сервер
python main.py

# Терминал 2: Telegram бот
python bot_runner.py
```

**Примечание:** Убедитесь что PostgreSQL запущен и доступен по указанным в `.env` параметрам.

# 🐳 Health Tracker - Windows Development & Production Deployment

## 🚀 Quick Start for Windows

### Prerequisites

1. **Docker Desktop for Windows** - [Download](https://www.docker.com/products/docker-desktop/)
2. **WSL 2** (Recommended) - Enable in Docker Desktop settings
3. **Git** - [Download](https://git-scm.com/download/win)

### Initial Setup

```powershell
# Run as Administrator in PowerShell
.\init-windows.ps1
Development Environment
Edit .env.windows and add your Telegram Bot Token

Start development services:

powershell
.\deploy.ps1 -Build
Management Commands
powershell
# Start all services
.\manage.ps1 start

# Stop all services
.\manage.ps1 stop

# View logs
.\manage.ps1 logs
.\manage.ps1 logs api-dev
.\manage.ps1 logs bot-dev

# Run migrations
.\manage.ps1 migrate

# Backup database
.\manage.ps1 backup

# Open shell in container
.\manage.ps1 shell api-dev
.\manage.ps1 shell postgres-dev

# Clean Docker resources
.\manage.ps1 clean
Access Services
API: http://localhost:8000

API Docs: http://localhost:8000/docs

PgAdmin: http://localhost:5050

Login: dev@example.com

Password: dev_password

🏭 Production Deployment to Linux
Prepare Production Server
powershell
# Setup server for first time
.\deploy-linux.ps1 -Server your-server.com -Username ubuntu -Setup

# Deploy application
.\deploy-linux.ps1 -Server your-server.com -Username ubuntu
Manual Server Setup (Alternative)
bash
# On your Linux server
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose git -y
sudo systemctl enable docker
sudo usermod -aG docker $USER

mkdir -p /opt/health-tracker
cd /opt/health-tracker
Production Commands (on Linux server)
bash
# Start production
cd /opt/health-tracker
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop production
docker-compose -f docker-compose.prod.yml down

# Backup database
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql
🛠️ Development Tips for Windows
1. Performance Optimization
Store project in WSL 2 filesystem (e.g., /home/username/projects/)

In Docker Desktop: Settings → Resources → Increase memory to 8GB

Use .dockerignore to exclude unnecessary files

2. Hot Reload
API: Automatic reload when code changes

Bot: Requires restart on changes: .\manage.ps1 restart bot-dev

3. Database Management
powershell
# Access PostgreSQL
.\manage.ps1 shell postgres-dev
# Inside container:
psql -U dev_user -d health_tracker_dev

# Reset database
.\manage.ps1 stop
docker volume rm health_tracker_postgres_data_dev
.\deploy.ps1 -Build
4. Debugging
powershell
# View all logs
.\manage.ps1 logs

# Check container health
docker ps
docker-compose -f docker-compose.dev.yml ps

# Inspect container
docker exec -it health_tracker_api_dev sh
🔧 Troubleshooting
Docker Desktop Issues
"Docker Desktop not starting"

Check WSL 2 is installed: wsl --list --verbose

Restart Docker Desktop as Administrator

"Volume mounting not working"

In Docker Desktop: Settings → Resources → File Sharing

Add project folder to shared folders

"Out of memory"

Increase Docker Desktop memory limit

Run: .\manage.ps1 clean

Network Issues
"Can't connect to localhost:8000"

Check if API is running: .\manage.ps1 status

Check firewall: Allow port 8000

"Database connection refused"

Wait for PostgreSQL to start (takes ~30 seconds)

Check: .\manage.ps1 logs postgres-dev

Bot Issues
"Bot not responding"

Check TELEGRAM_TOKEN in .env.windows

Restart bot: .\manage.ps1 restart bot-dev

Check logs: .\manage.ps1 logs bot-dev

📦 Production Checklist
Before Deployment
.env.production filled with real values

SECRET_KEY is strong and unique

Database passwords are secure

TELEGRAM_TOKEN is production bot token

Backup strategy is in place

After Deployment
API responds at http://server:8000/

Bot responds to /start

Database migrations applied

Logs are being written

Backups are working

🔐 Security Notes
For Development
Use dummy/test tokens

Never commit .env.windows to git

Use development database credentials

For Production
Use strong, unique passwords

Enable firewall on server

Regular security updates

Monitor logs for suspicious activity

Regular backups

📞 Support
Common Issues
WSL 2 not working: Run PowerShell as Admin: wsl --install

Docker Desktop error: Restart Docker Desktop service

Volume permissions: Run Docker Desktop as Administrator

Getting Help
Check logs: .\manage.ps1 logs

Check status: .\manage.ps1 status

Search existing issues

Create new issue with logs

⭐ Enjoy developing on Windows! ⭐

text

## 10. Конфигурация для CI/CD (GitHub Actions)

Создайте файл `.github/workflows/windows-ci.yml`:

```yaml
# .github/workflows/windows-ci.yml
name: Windows CI/CD

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test-windows:
    runs-on: windows-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ -v
    
    - name: Check code style
      run: |
        pip install black flake8
        black --check app/ bot/
        flake8 app/ bot/

  build-docker:
    runs-on: windows-latest
    needs: test-windows
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Build Docker image
      run: |
        docker build -t health-tracker:latest .
    
    - name: Save Docker image
      run: |
        docker save health-tracker:latest -o health-tracker.tar
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: docker-image
        path: health-tracker.tar

---

⭐ **Если проект вам понравился, поставьте звездочку на GitHub!** ⭐
