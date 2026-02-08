"""
Tests for TelegramBotManager service
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

from plugins.services.hub.telegram.bot_manager.bot_manager import TelegramBotManager


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for TelegramBotManager"""
    return {
        'logger': MagicMock(),
        'settings_manager': MagicMock(),
        'action_hub': MagicMock(),
        'database_manager': MagicMock(),
        'cache_manager': MagicMock(),
        'telegram_api': MagicMock(),
        'telegram_polling': MagicMock(),
    }


@pytest.fixture
def bot_manager(mock_dependencies):
    """Create TelegramBotManager instance"""
    mock_dependencies['settings_manager'].get_plugin_settings.return_value = {
        'cache_ttl': 315360000,
        'error_cache_ttl': 300,
        'use_webhooks': False,
        'webhook_endpoint': '/webhooks/telegram'
    }

    mock_repo = MagicMock()
    mock_repo.get_bot_by_id = AsyncMock(return_value=None)
    mock_repo.get_all_bots = AsyncMock(return_value=[])
    mock_repo.get_commands_by_bot = AsyncMock(return_value=[])
    mock_dependencies['database_manager'].get_master_repository.return_value = mock_repo

    return TelegramBotManager(**mock_dependencies)


@pytest.mark.asyncio
async def test_bot_manager_initialization(bot_manager):
    """Test that bot manager initializes correctly"""
    assert bot_manager is not None
    assert bot_manager.repository is not None
    assert bot_manager.lifecycle is not None
    assert bot_manager.parser is not None


@pytest.mark.asyncio
async def test_sync_telegram_bot_not_found(bot_manager):
    """Test sync_telegram_bot when YAML not found"""
    bot_manager.parser.parse_bot_config = AsyncMock(return_value=None)

    result = await bot_manager.sync_telegram_bot({'tenant_id': 1})

    assert result['result'] == 'not_found'


@pytest.mark.asyncio
async def test_get_bot_info_not_found(bot_manager):
    """Test get_bot_info when bot doesn't exist"""
    result = await bot_manager.get_bot_info({'bot_id': 999})

    assert result['result'] == 'error'
    assert result['error']['code'] in ['NOT_FOUND', 'INTERNAL_ERROR']


@pytest.mark.asyncio
async def test_run_loads_cache(bot_manager, mock_dependencies):
    """Test that run() loads bot cache"""
    mock_repo = mock_dependencies['database_manager'].get_master_repository.return_value
    mock_repo.get_all_bots.return_value = [
        {
            'id': 1,
            'tenant_id': 1,
            'bot_token': 'token123',
            'is_active': True,
            'username': 'test_bot',
            'first_name': 'Test'
        }
    ]

    await bot_manager.run()

    mock_repo.get_all_bots.assert_called_once()
