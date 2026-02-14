import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from pathlib import Path


@pytest.fixture(autouse=True)
def setup_test_env():
    """Устанавливает переменные окружения для тестов"""
    # Загружаем .env.test если существует
    env_test = Path(__file__).parent.parent / ".env.test"
    if env_test.exists():
        with open(env_test) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value
    else:
        # Устанавливаем минимально необходимые переменные
        os.environ["POSTGRES_USER"] = "test_user"
        os.environ["POSTGRES_PASSWORD"] = "test_pass"
        os.environ["POSTGRES_HOST"] = "localhost"
        os.environ["POSTGRES_DB"] = "test_db"
        os.environ["TELEGRAM_TOKEN"] = "test_token"
        os.environ["SECRET_KEY"] = "test_key"


def test_imports():
    """Проверка импортов"""
    try:
        from bot.handlers.start import cmd_start

        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.asyncio
async def test_cmd_cancel():
    """Тест команды отмены"""
    from bot.handlers.start import cmd_cancel

    # Создаем моки
    message = AsyncMock()
    message.from_user.id = 12345
    message.text = "/cancel"

    state = AsyncMock()
    state.get_state.return_value = None

    # Мокаем get_main_keyboard чтобы не зависеть от БД
    with patch("bot.handlers.start.get_main_keyboard", return_value=AsyncMock()):
        # Вызываем функцию
        await cmd_cancel(message, state)

        # Проверяем, что answer был вызван
        message.answer.assert_called_once()
