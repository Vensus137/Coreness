"""
Фикстуры для тестов TaskManager
"""
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from plugins.utilities.foundation.logger.logger import Logger
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager

# Добавляем родительскую директорию плагина в sys.path
_plugin_dir = Path(__file__).parent.parent.parent  # plugins/utilities/core/
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))


@pytest.fixture
def mock_logger():
    """Создает мок логгера"""
    logger = Mock(spec=Logger)
    logger.get_logger = Mock(return_value=Mock())
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def mock_settings_manager():
    """Создает мок settings_manager"""
    settings_manager = Mock(spec=SettingsManager)
    settings_manager.get_plugin_settings = Mock(return_value={
        'default_queue': 'action',
        'wait_interval': 1.0
    })
    settings_manager.get_global_settings = Mock(return_value={
        'shutdown': {
            'plugin_timeout': 0.15
        }
    })
    return settings_manager


@pytest.fixture
def task_manager_kwargs(mock_logger, mock_settings_manager):
    """Создает kwargs для инициализации TaskManager"""
    return {
        'logger': mock_logger,
        'settings_manager': mock_settings_manager
    }

