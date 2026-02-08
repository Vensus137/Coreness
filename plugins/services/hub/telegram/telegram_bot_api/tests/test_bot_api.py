"""
Tests for TelegramBotAPI service
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure project root is on path (run from any cwd)
_root = Path(__file__).resolve()
for _ in range(10):
    if (_root / "pyproject.toml").exists() or (_root / "plugins").is_dir():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break
    _root = _root.parent

from plugins.services.hub.telegram.telegram_bot_api.bot_api import TelegramBotAPI


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for TelegramBotAPI"""
    action_hub = MagicMock()
    action_hub.execute_action = AsyncMock(return_value={
        'result': 'success',
        'response_data': {'bot_token': 'test_token'}
    })

    telegram_api = MagicMock()
    telegram_api.send_message = AsyncMock(return_value={'result': 'success'})

    return {
        'logger': MagicMock(),
        'settings_manager': MagicMock(),
        'action_hub': action_hub,
        'telegram_api': telegram_api,
    }


@pytest.fixture
def bot_api(mock_dependencies):
    """Create TelegramBotAPI instance"""
    mock_dependencies['settings_manager'].get_plugin_settings.return_value = {
        'default_buttons_per_row': 2
    }

    return TelegramBotAPI(**mock_dependencies)


@pytest.mark.asyncio
async def test_bot_api_initialization(bot_api):
    """Test that bot API initializes correctly"""
    assert bot_api is not None
    assert bot_api.message_handler is not None
    assert bot_api.keyboard_builder is not None


@pytest.mark.asyncio
async def test_send_message_success(bot_api, mock_dependencies):
    """Test send_message with valid bot_id"""
    result = await bot_api.send_message({
        'bot_id': 1,
        'text': 'Test message'
    })

    assert result['result'] == 'success'
    mock_dependencies['telegram_api'].send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_no_token(bot_api, mock_dependencies):
    """Test send_message when bot token not found"""
    mock_dependencies['action_hub'].execute_action.return_value = {
        'result': 'success',
        'response_data': {'bot_token': None}
    }

    result = await bot_api.send_message({'bot_id': 1, 'text': 'Test'})

    assert result['result'] == 'error'
    assert result['error']['code'] == 'NOT_FOUND'


@pytest.mark.asyncio
async def test_build_keyboard_inline(bot_api):
    """Test building inline keyboard"""
    result = await bot_api.build_keyboard({
        'items': [1, 2, 3],
        'keyboard_type': 'inline',
        'text_template': 'Item $value$',
        'callback_template': 'select_$value$',
        'buttons_per_row': 2
    })

    assert result['result'] == 'success'
    assert result['response_data']['keyboard_type'] == 'inline'
    assert result['response_data']['buttons_count'] == 3
    assert result['response_data']['rows_count'] == 2


@pytest.mark.asyncio
async def test_build_keyboard_validation_error(bot_api):
    """Test build_keyboard with missing callback_template for inline"""
    result = await bot_api.build_keyboard({
        'items': [1, 2],
        'keyboard_type': 'inline',
        'text_template': 'Item $value$'
    })

    assert result['result'] == 'error'
    assert result['error']['code'] == 'VALIDATION_ERROR'
