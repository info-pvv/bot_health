#!/bin/bash
# deploy.sh - Production deployment script

set -e

echo "🚀 Starting Health Tracker Production Deployment..."

# Проверка наличия .env.production
if [ ! -f .env.production ]; then
    echo "❌ .env.production file not found!"
    echo "💡 Copy .env.example to .env.production and fill in the values"
    exit 1
fi

# Загрузка переменных окружения
export $(grep -v '^#' .env.production | xargs)

# Проверка обязательных переменных
required_vars=("TELEGRAM_TOKEN" "POSTGRES_PASSWORD" "SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required variable $var is not set in .env.production"
        exit 1
    fi
done

echo "✅ Environment variables loaded"

# Сборка и запуск контейнеров
echo "🔨 Building Docker images..."
docker compose -f docker-compose.prod.yml build

echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Проверка состояния сервисов
echo "🔍 Checking service status..."

# Проверка PostgreSQL
if docker compose -f docker-compose.prod.yml exec -T postgres_prod pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready"
    docker compose -f docker-compose.prod.yml logs postgres_prod
    exit 1
fi

# Проверка API
if curl -s -f http://api-prod:$API_PORT/ > /dev/null; then
    echo "✅ API is running"
else
    echo "❌ API is not responding"
    docker compose -f docker-compose.prod.yml logs api-prod
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Services Status:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo "🔗 API URL: http://localhost:${API_PORT}"
echo "📚 API Docs: http://localhost:${API_PORT}/docs"
echo "🛠️  PgAdmin: http://localhost:${PGADMIN_PORT} (optional)"
echo ""
echo "📋 Useful commands:"
echo "  View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop services: docker-compose -f docker-compose.prod.yml down"
echo "  Restart bot: docker-compose -f docker-compose.prod.yml restart bot"
echo ""
echo "✅ Health Tracker is now running in production mode!"