"""
Local fixtures for tenant_hub tests
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import fixtures from tests/conftest
from tests.conftest import logger, module_logger, settings_manager  # noqa: F401

# Automatically add parent plugin directory to sys.path
# This allows using imports like "from handlers.github_webhook import ..."
# instead of "from plugins.services.hub.tenant_hub.handlers.github_webhook import ..."
# and makes tests independent of folder structure above plugin level
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))


@pytest.fixture
def mock_database_manager():
    """Create mock DatabaseManager"""
    mock = MagicMock()
    mock.get_master_repository = MagicMock()
    return mock


@pytest.fixture
def mock_master_repository():
    """Create mock MasterRepository"""
    mock = MagicMock()
    mock.get_bot_by_tenant_id = AsyncMock(return_value=None)
    mock.get_commands_by_bot = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_datetime_formatter():
    """Create mock DateTimeFormatter"""
    mock = MagicMock()
    mock.now_local_tz = AsyncMock(return_value=None)
    mock.to_string = AsyncMock(return_value='2024-01-01T00:00:00+00:00')
    return mock


@pytest.fixture
def mock_cache_manager():
    """Create mock CacheManager with state preservation"""
    cache_storage = {}  # Cache storage
    
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
        # Simple implementation for tests
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
    """Create mock SettingsManager for tests"""
    mock = MagicMock()
    # Configure return of tenant_hub settings
    mock.get_plugin_settings = MagicMock(return_value={
        'cache_ttl': 315360000
    })
    return mock


@pytest.fixture
def tenant_cache(logger, mock_database_manager, mock_datetime_formatter, mock_master_repository, mock_cache_manager, mock_settings_manager):
    """Create TenantCache for tests"""
    import sys
    from pathlib import Path
    import importlib.util
    
    # Direct import of TenantCache without relative imports
    tenant_cache_path = Path(__file__).parent.parent / "domain" / "tenant_cache.py"
    spec = importlib.util.spec_from_file_location("tenant_cache_module", tenant_cache_path)
    tenant_cache_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tenant_cache_module)
    TenantCache = tenant_cache_module.TenantCache
    
    # Configure mock database_manager to return master_repository
    mock_database_manager.get_master_repository.return_value = mock_master_repository
    
    return TenantCache(
        database_manager=mock_database_manager,
        logger=logger,
        datetime_formatter=mock_datetime_formatter,
        cache_manager=mock_cache_manager,
        settings_manager=mock_settings_manager
    )

