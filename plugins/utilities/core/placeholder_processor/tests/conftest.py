"""
Локальные фикстуры для тестов placeholder_processor
"""
import sys
from pathlib import Path

import pytest

# Импорты из других плагинов (foundation) оставляем абсолютными
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager

# Импортируем фикстуры из корневого tests/conftest через абсолютный путь
_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
    
from tests.conftest import logger, module_logger  # noqa: F401

# Добавляем родительскую директорию плагина в sys.path
# Импортируем PlaceholderProcessor через полное имя модуля с сохранением структуры пакета
_plugin_dir = Path(__file__).parent.parent.parent  # plugins/utilities/core/
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# Импортируем через подпапку, сохраняя структуру пакета для относительных импортов
from placeholder_processor.placeholder_processor import PlaceholderProcessor


@pytest.fixture(scope="session")
def _plugins_manager(module_logger):
    """Создает PluginsManager один раз на всю сессию тестов (максимальная оптимизация)"""
    return PluginsManager(logger=module_logger.get_logger("plugins_manager"))


@pytest.fixture(scope="session")
def _settings_manager(_plugins_manager, module_logger):
    """Создает SettingsManager один раз на всю сессию тестов (максимальная оптимизация)"""
    return SettingsManager(logger=module_logger.get_logger("settings_manager"), plugins_manager=_plugins_manager)


@pytest.fixture(scope="session")
def processor(module_logger, _settings_manager):
    """Создает PlaceholderProcessor один раз на всю сессию тестов (максимальная оптимизация)"""
    return PlaceholderProcessor(logger=module_logger, settings_manager=_settings_manager)


def assert_equal(actual, expected, message=""):
    """Упрощённая проверка равенства с нормализацией типов для строковых результатов"""
    # Если actual - строка, а expected - число или булево, нормализуем
    if isinstance(actual, str):
        if isinstance(expected, bool):
            # Преобразуем строку "True"/"False" в булево
            if actual == "True":
                actual = True
            elif actual == "False":
                actual = False
        elif isinstance(expected, (int, float)):
            # Преобразуем строку в число
            try:
                actual = float(actual) if isinstance(expected, float) else int(actual)
            except (ValueError, TypeError):
                pass
    
    assert actual == expected, f"{message}: expected {expected!r}, got {actual!r}"

