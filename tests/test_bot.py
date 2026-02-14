import pytest
from unittest.mock import AsyncMock, MagicMock


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
    state = AsyncMock()
    state.get_state.return_value = None

    # Вызываем функцию
    await cmd_cancel(message, state)

    # Проверяем, что answer был вызван
    message.answer.assert_called_once()
