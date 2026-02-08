#!/bin/bash
# health_tracker.sh - Management script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"

case "$1" in
    start)
        echo "🚀 Starting Health Tracker..."
        docker compose -f $COMPOSE_FILE up -d
        ;;
    stop)
        echo "🛑 Stopping Health Tracker..."
        docker compose -f $COMPOSE_FILE down
        ;;
    restart)
        echo "🔄 Restarting Health Tracker..."
        docker compose -f $COMPOSE_FILE restart
        ;;
    status)
        echo "📊 Health Tracker Status:"
        docker compose -f $COMPOSE_FILE ps
        ;;
    logs)
        service="${2:-all}"
        if [ "$service" = "all" ]; then
            docker compose -f $COMPOSE_FILE logs -f
        else
            docker compose -f $COMPOSE_FILE logs -f $service
        fi
        ;;
    backup)
        echo "💾 Creating database backup..."
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        docker compose -f $COMPOSE_FILE exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > "backup_${TIMESTAMP}.sql"
        echo "✅ Backup saved to backup_${TIMESTAMP}.sql"
        ;;
    update)
        echo "📦 Updating Health Tracker..."
        git pull origin main
        docker compose -f $COMPOSE_FILE build
        docker compose -f $COMPOSE_FILE up -d
        ;;
    migrate)
        echo "🗄️ Running migrations..."
        docker compose -f $COMPOSE_FILE exec api python migrations/manage.py up
        ;;
    shell)
        service="${2:-api}"
        docker compose -f $COMPOSE_FILE exec $service sh
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|backup|update|migrate|shell}"
        echo ""
        echo "Commands:"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  status    - Show service status"
        echo "  logs      - View logs (all or specific service)"
        echo "  backup    - Backup database"
        echo "  update    - Update from git and rebuild"
        echo "  migrate   - Run database migrations"
        echo "  shell     - Open shell in container"
        exit 1
        ;;
esac