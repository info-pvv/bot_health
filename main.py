from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import health, users, admin
from app.models.database import engine, Base
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц при старте
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Очистка при завершении
    await engine.dispose()

app = FastAPI(
    title="Employee Health Tracker API",
    description="API для отслеживания статусов здоровья сотрудников",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(health.router)
app.include_router(users.router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "Employee Health Tracker API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)