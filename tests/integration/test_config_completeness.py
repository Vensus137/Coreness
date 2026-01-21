"""
Integration tests for configurations and validation
Extend existing configuration tests
"""
import pytest
from pathlib import Path

from tests.conftest import project_root  # noqa: F401


@pytest.mark.integration
def test_all_plugins_have_config(project_root):
    """Verify that all plugins have config.yaml"""
    plugins_dir = project_root / "plugins"
    missing_configs = []
    
    # Find all plugin folders
    # Plugin is defined as a folder containing .py files
    for plugin_dir in plugins_dir.rglob("*"):
        if not plugin_dir.is_dir():
            continue
        
        # Skip system folders
        if plugin_dir.name.startswith('__') or plugin_dir.name.startswith('.'):
            continue
        
        # Skip tests folders
        if 'tests' in plugin_dir.parts:
            continue
        
        # Check if there are .py files (this might be a plugin)
        py_files = [f for f in plugin_dir.iterdir() if f.is_file() and f.suffix == '.py' and not f.name.startswith('__')]
        
        if py_files:
            # This might be a plugin, check for config.yaml
            config_file = plugin_dir / "config.yaml"
            if not config_file.exists():
                # Check if this is a submodule (e.g., core/, utils/)
                # Submodules may not have config.yaml
                parent_config = plugin_dir.parent / "config.yaml"
                if not parent_config.exists():
                    missing_configs.append(str(plugin_dir.relative_to(project_root)))
    
    if missing_configs:
        pytest.fail(f"Plugins without config.yaml:\n" + "\n".join(missing_configs))


@pytest.mark.integration
def test_all_dependencies_exist(project_root):
    """Verify that all dependencies in config.yaml exist"""
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
        pytest.fail(f"Non-existent dependencies:\n" + "\n".join(missing_deps))


@pytest.mark.integration
def test_all_plugins_have_name(project_root):
    """Verify that all config.yaml files contain name field"""
    plugins_dir = project_root / "plugins"
    errors = []
    
    import yaml
    
    for config_path in plugins_dir.rglob("config.yaml"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            if 'name' not in config:
                errors.append(f"{config_path.relative_to(project_root)}: missing 'name' field")
        except Exception as e:
            errors.append(f"{config_path.relative_to(project_root)}: read error - {str(e)}")
    
    if errors:
        pytest.fail(f"Errors in config.yaml files:\n" + "\n".join(errors))


@pytest.mark.integration
def test_all_plugins_have_type(project_root):
    """Verify that all config.yaml files contain correct type (determined automatically)"""
    from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
    from plugins.utilities.foundation.logger.logger import Logger
    
    logger = Logger()
    plugins_manager = PluginsManager(logger=logger.get_logger('test'))
    
    utilities = plugins_manager.get_plugins_by_type("utilities")
    services = plugins_manager.get_plugins_by_type("services")
    
    # Verify that all plugins have a type
    all_plugins = plugins_manager.get_all_plugins_info()
    plugins_without_type = []
    
    for plugin_name, plugin_info in all_plugins.items():
        plugin_type = plugin_info.get('type')
        if not plugin_type:
            plugins_without_type.append(plugin_name)
    
    if plugins_without_type:
        pytest.fail(f"Plugins without type:\n" + "\n".join(plugins_without_type))
    
    # Verify that types are correct
    assert len(utilities) > 0, "There should be utilities"
    assert len(services) > 0, "There should be services"


@pytest.mark.integration
def test_actions_have_correct_structure(project_root):
    """Verify action structure in config.yaml"""
    from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
    from plugins.utilities.foundation.logger.logger import Logger
    
    logger = Logger()
    plugins_manager = PluginsManager(logger=logger.get_logger('test'))
    all_plugins = plugins_manager.get_all_plugins_info()
    
    errors = []
    for plugin_name, plugin_info in all_plugins.items():
        actions = plugin_info.get('actions', {})
        
        for action_name, action_config in actions.items():
            # Verify presence of required fields
            if 'description' not in action_config:
                errors.append(f"{plugin_name}.{action_name}: missing 'description'")
            
            # Verify input structure (if present)
            if 'input' in action_config:
                input_config = action_config['input']
                if 'data' in input_config:
                    data_config = input_config['data']
                    if 'type' not in data_config:
                        errors.append(f"{plugin_name}.{action_name}: input.data should have 'type'")
            
            # Verify output structure (if present)
            if 'output' in action_config:
                output_config = action_config['output']
                if 'result' not in output_config:
                    errors.append(f"{plugin_name}.{action_name}: output should contain 'result'")
    
    if errors:
        pytest.fail(f"Action structure errors:\n" + "\n".join(errors))

