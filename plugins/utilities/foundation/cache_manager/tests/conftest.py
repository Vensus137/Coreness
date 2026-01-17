"""
Локальные фикстуры для тестов cache_manager
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Импортируем фикстуры из tests/conftest
from tests.conftest import logger, module_logger, settings_manager  # noqa: F401

# Автоматически добавляем родительскую директорию плагина в sys.path
# Это позволяет использовать импорты вида "from cache_manager import ..."
# вместо "from plugins.utilities.foundation.cache_manager.cache_manager import ..."
# и делает тесты независимыми от структуры папок выше уровня плагина
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

from cache_manager import CacheManager


@pytest.fixture
def mock_settings_manager():
    """Создает мок SettingsManager с тестовыми настройками"""
    mock = MagicMock()
    
    # Настройки для тестов
    mock.get_plugin_settings.return_value = {
        'default_ttl': 3600,  # 1 час
        'cleanup_interval': 0.01,  # 0.01 секунды для быстрых тестов
        'cleanup_sample_size': 10,  # Маленькая выборка для тестов
        'cleanup_expired_threshold': 0.25,  # 25%
    }
    
    return mock


@pytest.fixture
def cache_manager(logger, mock_settings_manager):
    """Создает CacheManager для тестов"""
    return CacheManager(logger=logger, settings_manager=mock_settings_manager)


@pytest.fixture
def cache_manager_with_short_ttl(logger, mock_settings_manager):
    """Создает CacheManager с очень коротким TTL для быстрых тестов истечения"""
    # Переопределяем настройки для быстрого истечения (0.01 сек для максимального ускорения тестов)
    mock_settings_manager.get_plugin_settings.return_value = {
        'default_ttl': 0.01,  # 0.01 секунды (10 мс) для быстрых тестов
        'cleanup_interval': 0.01,  # 0.01 секунды для тестов
        'cleanup_sample_size': 10,
        'cleanup_expired_threshold': 0.25,
    }
    
    return CacheManager(logger=logger, settings_manager=mock_settings_manager)

