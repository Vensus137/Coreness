"""
Local fixtures for cache_manager tests
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import fixtures from tests/conftest
from tests.conftest import logger, module_logger, settings_manager  # noqa: F401

# Automatically add parent plugin directory to sys.path
# This allows using imports like "from cache_manager import ..."
# instead of "from plugins.utilities.foundation.cache_manager.cache_manager import ..."
# and makes tests independent of folder structure above plugin level
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from cache_manager import CacheManager


@pytest.fixture
def mock_settings_manager():
    """Create mock SettingsManager with test settings"""
    mock = MagicMock()
    
    # Settings for tests
    mock.get_plugin_settings.return_value = {
        'default_ttl': 3600,  # 1 hour
        'cleanup_interval': 0.01,  # 0.01 seconds for fast tests
        'cleanup_sample_size': 10,  # Small sample for tests
        'cleanup_expired_threshold': 0.25,  # 25%
    }
    
    return mock


@pytest.fixture
def cache_manager(logger, mock_settings_manager):
    """Create CacheManager for tests"""
    return CacheManager(logger=logger, settings_manager=mock_settings_manager)


@pytest.fixture
def cache_manager_with_short_ttl(logger, mock_settings_manager):
    """Create CacheManager with very short TTL for fast expiration tests"""
    # Override settings for fast expiration (0.01 sec for maximum test speed)
    mock_settings_manager.get_plugin_settings.return_value = {
        'default_ttl': 0.01,  # 0.01 seconds (10 ms) for fast tests
        'cleanup_interval': 0.01,  # 0.01 seconds for tests
        'cleanup_sample_size': 10,
        'cleanup_expired_threshold': 0.25,
    }
    
    return CacheManager(logger=logger, settings_manager=mock_settings_manager)

