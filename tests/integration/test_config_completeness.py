"""
Интеграционные тесты конфигураций и валидации
Расширяют существующие тесты конфигураций
"""
import pytest
from pathlib import Path

from tests.conftest import project_root  # noqa: F401


@pytest.mark.integration
def test_all_plugins_have_config(project_root):
    """Проверка, что все плагины имеют config.yaml"""
    plugins_dir = project_root / "plugins"
    missing_configs = []
    
    # Ищем все папки с плагинами
    # Плагин определяется как папка, содержащая .py файлы
    for plugin_dir in plugins_dir.rglob("*"):
        if not plugin_dir.is_dir():
            continue
        
        # Пропускаем служебные папки
        if plugin_dir.name.startswith('__') or plugin_dir.name.startswith('.'):
            continue
        
        # Пропускаем папки tests
        if 'tests' in plugin_dir.parts:
            continue
        
        # Проверяем, есть ли .py файлы (это может быть плагин)
        py_files = [f for f in plugin_dir.iterdir() if f.is_file() and f.suffix == '.py' and not f.name.startswith('__')]
        
        if py_files:
            # Это может быть плагин, проверяем наличие config.yaml
            config_file = plugin_dir / "config.yaml"
            if not config_file.exists():
                # Проверяем, не является ли это подмодулем (например, core/, utils/)
                # Подмодули могут не иметь config.yaml
                parent_config = plugin_dir.parent / "config.yaml"
                if not parent_config.exists():
                    missing_configs.append(str(plugin_dir.relative_to(project_root)))
    
    if missing_configs:
        pytest.fail(f"Плагины без config.yaml:\n" + "\n".join(missing_configs))


@pytest.mark.integration
def test_all_dependencies_exist(project_root):
    """Проверка, что все зависимости в config.yaml существуют"""
    from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
    from plugins.utilities.foundation.logger.logger import Logger
    
    logger = Logger()
    plugins_manager = PluginsManager(logger=logger.get_logger('test'))
    all_plugins = plugins_manager.get_all_plugins_info()
    
    missing_deps = []
    for plugin_name, plugin_info in all_plugins.items():
        deps = plugin_info.get('dependencies', []) + plugin_info.get('optional_dependencies', [])
        for dep in deps:
            if dep not in all_plugins:
                missing_deps.append(f"{plugin_name} -> {dep}")
    
    if missing_deps:
        pytest.fail(f"Несуществующие зависимости:\n" + "\n".join(missing_deps))


@pytest.mark.integration
def test_all_plugins_have_name(project_root):
    """Проверка, что все config.yaml содержат поле name"""
    plugins_dir = project_root / "plugins"
    errors = []
    
    import yaml
    
    for config_path in plugins_dir.rglob("config.yaml"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            if 'name' not in config:
                errors.append(f"{config_path.relative_to(project_root)}: отсутствует поле 'name'")
        except Exception as e:
            errors.append(f"{config_path.relative_to(project_root)}: ошибка чтения - {str(e)}")
    
    if errors:
        pytest.fail(f"Ошибки в config.yaml файлах:\n" + "\n".join(errors))


@pytest.mark.integration
def test_all_plugins_have_type(project_root):
    """Проверка, что все config.yaml содержат корректный тип (определяется автоматически)"""
    from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
    from plugins.utilities.foundation.logger.logger import Logger
    
    logger = Logger()
    plugins_manager = PluginsManager(logger=logger.get_logger('test'))
    
    utilities = plugins_manager.get_plugins_by_type("utilities")
    services = plugins_manager.get_plugins_by_type("services")
    
    # Проверяем, что все плагины имеют тип
    all_plugins = plugins_manager.get_all_plugins_info()
    plugins_without_type = []
    
    for plugin_name, plugin_info in all_plugins.items():
        plugin_type = plugin_info.get('type')
        if not plugin_type:
            plugins_without_type.append(plugin_name)
    
    if plugins_without_type:
        pytest.fail(f"Плагины без типа:\n" + "\n".join(plugins_without_type))
    
    # Проверяем, что типы корректны
    assert len(utilities) > 0, "Должны быть утилиты"
    assert len(services) > 0, "Должны быть сервисы"


@pytest.mark.integration
def test_actions_have_correct_structure(project_root):
    """Проверка структуры действий в config.yaml"""
    from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
    from plugins.utilities.foundation.logger.logger import Logger
    
    logger = Logger()
    plugins_manager = PluginsManager(logger=logger.get_logger('test'))
    all_plugins = plugins_manager.get_all_plugins_info()
    
    errors = []
    for plugin_name, plugin_info in all_plugins.items():
        actions = plugin_info.get('actions', {})
        
        for action_name, action_config in actions.items():
            # Проверяем наличие обязательных полей
            if 'description' not in action_config:
                errors.append(f"{plugin_name}.{action_name}: отсутствует 'description'")
            
            # Проверяем структуру input (если есть)
            if 'input' in action_config:
                input_config = action_config['input']
                if 'data' in input_config:
                    data_config = input_config['data']
                    if 'type' not in data_config:
                        errors.append(f"{plugin_name}.{action_name}: input.data должен иметь 'type'")
            
            # Проверяем структуру output (если есть)
            if 'output' in action_config:
                output_config = action_config['output']
                if 'result' not in output_config:
                    errors.append(f"{plugin_name}.{action_name}: output должен содержать 'result'")
    
    if errors:
        pytest.fail(f"Ошибки структуры действий:\n" + "\n".join(errors))

