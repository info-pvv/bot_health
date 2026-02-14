# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.models.database import init_database, engine, Base
from app.core.config import settings
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация PostgreSQL
    print(
        f"🔗 Подключение к PostgreSQL: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}"
    )

    # Создаем БД если не существует
    if await init_database():
        print("✅ База данных готова")

        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы созданы")
    else:
        print("❌ Ошибка инициализации базы данных")
        print("💡 Проверьте что PostgreSQL запущен и доступен")

    yield

    # Закрываем соединения
    await engine.dispose()


app = FastAPI(
    title="Employee Health Tracker API",
    description="API для отслеживания статусов здоровья сотрудников",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
from app.api.routes import health_router, users_router, admin_router, duty_router

app.include_router(health_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(duty_router)


@app.get("/")
async def root():
    return {"message": "Employee Health Tracker API"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
