"""
Локальные фикстуры для тестов bot_hub
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Импортируем фикстуры из tests/conftest
from tests.conftest import logger, module_logger, settings_manager  # noqa: F401

# Автоматически добавляем родительскую директорию плагина в sys.path
# Это позволяет использовать импорты вида "from modules.webhook_manager import ..."
# вместо "from plugins.services.hub.bot_hub.modules.webhook_manager import ..."
# и делает тесты независимыми от структуры папок выше уровня плагина
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))


@pytest.fixture
def mock_database_manager():
    """Создает мок DatabaseManager"""
    mock = MagicMock()
    mock.get_master_repository = MagicMock()
    return mock


@pytest.fixture
def mock_master_repository():
    """Создает мок MasterRepository"""
    mock = MagicMock()
    mock.get_bot_by_id = AsyncMock(return_value=None)
    mock.get_bot_by_tenant_id = AsyncMock(return_value=None)
    mock.get_all_bots = AsyncMock(return_value=[])
    mock.get_commands_by_bot = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_telegram_api():
    """Создает мок TelegramAPI"""
    mock = MagicMock()
    mock.get_bot_info = AsyncMock(return_value={
        'result': 'success',
        'response_data': {
            'telegram_bot_id': 123456,
            'username': 'test_bot'
        }
    })
    return mock


@pytest.fixture
def mock_telegram_polling():
    """Создает мок TelegramPolling"""
    mock = MagicMock()
    mock.start_bot_polling = AsyncMock(return_value=True)
    mock.stop_bot_polling = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_action_hub():
    """Создает мок ActionHub"""
    mock = MagicMock()
    mock.execute_action = AsyncMock(return_value={"result": "success"})
    return mock


@pytest.fixture
def mock_cache_manager():
    """Создает мок CacheManager с сохранением состояния"""
    cache_storage = {}  # Хранилище для кэша
    
    mock = MagicMock()
    
    async def get_side_effect(key):
        return cache_storage.get(key)
    
    async def set_side_effect(key, value, ttl=None):
        cache_storage[key] = value
        return True
    
    async def exists_side_effect(key):
        return key in cache_storage
    
    async def delete_side_effect(key):
        if key in cache_storage:
            del cache_storage[key]
        return True
    
    async def invalidate_pattern_side_effect(pattern):
        # Простая реализация для тестов
        keys_to_delete = [k for k in cache_storage.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            del cache_storage[key]
        return len(keys_to_delete)
    
    mock.get = AsyncMock(side_effect=get_side_effect)
    mock.set = AsyncMock(side_effect=set_side_effect)
    mock.exists = AsyncMock(side_effect=exists_side_effect)
    mock.delete = AsyncMock(side_effect=delete_side_effect)
    mock.invalidate_pattern = AsyncMock(side_effect=invalidate_pattern_side_effect)
    
    return mock


@pytest.fixture
def mock_settings_manager():
    """Создает мок SettingsManager для тестов"""
    mock = MagicMock()
    # Настраиваем возврат настроек bot_hub
    mock.get_plugin_settings = MagicMock(return_value={
        'cache_ttl': 315360000,
        'error_cache_ttl': 300
    })
    return mock


@pytest.fixture
def mock_webhook_manager():
    """Создает мок WebhookManager для тестов"""
    mock = MagicMock()
    mock.get_webhook_info = AsyncMock(return_value={
        'result': 'success',
        'response_data': {
            'is_webhook_active': False,
            'webhook_url': ''
        }
    })
    return mock


@pytest.fixture
def bot_info_manager(logger, mock_database_manager, mock_action_hub, mock_telegram_api, mock_telegram_polling, mock_master_repository, mock_cache_manager, mock_settings_manager, mock_webhook_manager):
    """Создает BotInfoManager для тестов"""
    from modules.bot_info_manager import BotInfoManager
    
    # Настраиваем мок database_manager для возврата master_repository
    mock_database_manager.get_master_repository.return_value = mock_master_repository
    
    return BotInfoManager(
        database_manager=mock_database_manager,
        action_hub=mock_action_hub,
        telegram_api=mock_telegram_api,
        telegram_polling=mock_telegram_polling,
        logger=logger,
        cache_manager=mock_cache_manager,
        settings_manager=mock_settings_manager,
        webhook_manager=mock_webhook_manager
    )


@pytest.fixture
def bot_hub_service(logger, mock_database_manager, mock_action_hub, mock_telegram_api, mock_telegram_polling, mock_master_repository, mock_settings_manager, mock_cache_manager):
    """Создает BotHubService для тестов"""
    from bot_hub import BotHubService
    
    # Настраиваем мок database_manager для возврата master_repository
    mock_database_manager.get_master_repository.return_value = mock_master_repository
    
    return BotHubService(
        logger=logger,
        settings_manager=mock_settings_manager,
        telegram_polling=mock_telegram_polling,
        telegram_api=mock_telegram_api,
        database_manager=mock_database_manager,
        action_hub=mock_action_hub,
        cache_manager=mock_cache_manager
    )

