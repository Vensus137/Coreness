"""
Локальные фикстуры для тестов condition_parser
"""
import sys
from pathlib import Path

import pytest

from tests.conftest import logger, module_logger  # noqa: F401

# Добавляем родительскую директорию плагина в sys.path
_plugin_dir = Path(__file__).parent.parent.parent  # plugins/utilities/core/
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))

# Импортируем через подпапку, сохраняя структуру пакета для относительных импортов
from condition_parser.condition_parser import ConditionParser


@pytest.fixture(scope="session")
def parser(module_logger):
    """Создает ConditionParser один раз на всю сессию тестов (максимальная оптимизация)"""
    return ConditionParser(logger=module_logger)
