"""
Локальные фикстуры для тестов scenario_processor
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Импортируем фикстуры из tests/conftest
from tests.conftest import logger, module_logger, settings_manager  # noqa: F401

# Автоматически добавляем родительскую директорию плагина в sys.path
# Это позволяет использовать импорты вида "from scenario_engine.scenario_engine import ..."
# вместо "from plugins.services.scenario_processor.scenario_engine.scenario_engine import ..."
# и делает тесты независимыми от структуры папок выше уровня плагина
_plugin_dir = Path(__file__).parent.parent
if str(_plugin_dir) not in sys.path:
    sys.path.insert(0, str(_plugin_dir))


@pytest.fixture
def mock_data_loader():
    """Создает мок DataLoader"""
    mock = MagicMock()
    mock.load_scenarios_by_tenant = AsyncMock(return_value=[])
    mock.load_triggers_by_scenario = AsyncMock(return_value=[])
    mock.load_steps_by_scenario = AsyncMock(return_value=[])
    mock.load_transitions_by_step = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_action_hub():
    """Создает мок ActionHub"""
    mock = MagicMock()
    mock.execute_action = AsyncMock(return_value={"result": "success"})
    return mock


@pytest.fixture
def mock_condition_parser():
    """Создает мок ConditionParser"""
    mock = MagicMock()
    mock.parse = MagicMock(return_value=True)
    return mock


@pytest.fixture
def mock_placeholder_processor():
    """Создает мок PlaceholderProcessor"""
    mock = MagicMock()
    mock.process = AsyncMock(side_effect=lambda x, y: x)  # Возвращает как есть
    return mock


@pytest.fixture
def mock_scenario_finder():
    """Создает мок ScenarioFinder"""
    mock = MagicMock()
    mock.extract_tenant_id = MagicMock(return_value=1)
    mock.find_scenarios_by_event = AsyncMock(return_value=[])
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
    # Настраиваем возврат настроек scenario_processor
    mock.get_plugin_settings = MagicMock(return_value={
        'cache_ttl': 315360000
    })
    return mock


@pytest.fixture
def scenario_engine(mock_data_loader, logger, mock_action_hub, mock_condition_parser, mock_placeholder_processor, mock_cache_manager, mock_settings_manager):
    """Создает ScenarioEngine для тестов"""
    from scenario_engine.scenario_engine import ScenarioEngine
    
    # Мокируем методы condition_parser, которые используются в ScenarioLoader
    mock_condition_parser.parse_condition_string = AsyncMock(return_value={
        'search_path': ['event_type', 'message']
    })
    mock_condition_parser.add_to_tree = AsyncMock()
    mock_condition_parser.search_in_tree = AsyncMock(return_value=[])
    
    engine = ScenarioEngine(
        data_loader=mock_data_loader,
        logger=logger,
        action_hub=mock_action_hub,
        condition_parser=mock_condition_parser,
        placeholder_processor=mock_placeholder_processor,
        cache_manager=mock_cache_manager,
        settings_manager=mock_settings_manager
    )
    
    return engine

