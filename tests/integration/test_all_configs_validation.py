"""
Integration test for all configs for action_validator
Verifies that all validation schemas from config.yaml are correctly parsed and work
"""
import pytest
import yaml
from pathlib import Path

# Project root is already added to sys.path via pythonpath = ["."] in pyproject.toml
from tests.conftest import project_root, module_logger  # noqa: F401


class RealSettingsManager:
    """Real SettingsManager for tests with real configs"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._plugin_info_cache = {}
        self._load_all_plugins()
    
    def _load_all_plugins(self):
        """Load all plugins from config.yaml files"""
        plugins_dir = self.project_root / "plugins"
        
        # Scan all config.yaml files
        for config_path in plugins_dir.rglob("config.yaml"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                plugin_name = config.get('name')
                if not plugin_name:
                    continue
                
                # Save plugin information
                self._plugin_info_cache[plugin_name] = {
                    'actions': config.get('actions', {}),
                    'methods': config.get('methods', {})
                }
                
            except Exception as e:
                # Ignore errors loading individual configs
                print(f"⚠️ Error loading {config_path}: {e}")
                continue
    
    def get_plugin_info(self, plugin_name: str):
        """Get plugin information"""
        plugin_info = self._plugin_info_cache.get(plugin_name)
        if not plugin_info:
            return None
        
        return {
            'actions': plugin_info.get('actions', {}),
            'methods': plugin_info.get('methods', {})
        }
    
    def get_plugin_settings(self, plugin_name: str):
        """Get plugin settings"""
        return {}


@pytest.fixture(scope="session")
def real_settings_manager(project_root):
    """Creates RealSettingsManager with real configs"""
    return RealSettingsManager(project_root)


@pytest.fixture(scope="session")
def real_validator(module_logger, real_settings_manager):
    """Creates ActionValidator with real configs"""
    # Import here to avoid direct import at module level
    from plugins.utilities.core.action_validator.action_validator import ActionValidator
    return ActionValidator(logger=module_logger, settings_manager=real_settings_manager)


class TestAllConfigs:
    """Tests for all configs from plugins/"""
    
    def test_all_actions_schemas_parseable(self, real_validator, real_settings_manager):
        """Verify: all action schemas are correctly parsed"""
        errors = []
        
        for plugin_name, plugin_info in real_settings_manager._plugin_info_cache.items():
            actions = plugin_info.get('actions', {})
            
            for action_name, action_config in actions.items():
                # Extract input.data.properties schema
                input_config = action_config.get('input', {})
                data_config = input_config.get('data', {})
                properties = data_config.get('properties', {})
                
                if not properties:
                    # No schema - this is normal, skip
                    continue
                
                # Try to create validation model
                try:
                    model = real_validator._create_pydantic_model(properties, f'{plugin_name}.{action_name}')
                    
                    if model is None:
                        # Model not created - this may be normal for empty schemas
                        continue
                    
                    # Verify that model can be created without errors
                    # This means the schema is correct
                    
                except Exception as e:
                    errors.append(f"{plugin_name}.{action_name}: {str(e)}")
        
        if errors:
            pytest.fail(f"Schema parsing errors:\n" + "\n".join(errors))
    
    def test_union_string_integer_types_supported(self, real_validator, real_settings_manager):
        """Verify: all union types string|integer are correctly handled"""
        errors = []
        
        for plugin_name, plugin_info in real_settings_manager._plugin_info_cache.items():
            actions = plugin_info.get('actions', {})
            
            for action_name, action_config in actions.items():
                input_config = action_config.get('input', {})
                data_config = input_config.get('data', {})
                properties = data_config.get('properties', {})
                
                for field_name, field_config in properties.items():
                    type_str = field_config.get('type', 'string')
                    
                    # Check union types with string|integer
                    if isinstance(type_str, str) and '|' in type_str:
                        type_parts = [p.strip().lower() for p in type_str.split('|')]
                        
                        # If there is string|integer or integer|string
                        if ('string' in type_parts and 'integer' in type_parts):
                            # Try to create model with this field
                            try:
                                test_schema = {field_name: field_config}
                                model = real_validator._create_pydantic_model(test_schema, f'{plugin_name}.{action_name}.{field_name}')
                                
                                if model is None:
                                    errors.append(f"{plugin_name}.{action_name}.{field_name}: model not created for {type_str}")
                                
                            except Exception as e:
                                errors.append(f"{plugin_name}.{action_name}.{field_name}: error creating model for {type_str}: {str(e)}")
        
        if errors:
            pytest.fail(f"Union type string|integer handling errors:\n" + "\n".join(errors))
    
    def test_all_constraints_applied(self, real_validator, real_settings_manager):
        """Verify: constraints (min_length, max_length, min, max) are correctly applied"""
        errors = []
        
        for plugin_name, plugin_info in real_settings_manager._plugin_info_cache.items():
            actions = plugin_info.get('actions', {})
            
            for action_name, action_config in actions.items():
                input_config = action_config.get('input', {})
                data_config = input_config.get('data', {})
                properties = data_config.get('properties', {})
                
                for field_name, field_config in properties.items():
                    type_str = field_config.get('type', 'string')
                    
                    # Verify that constraints are applied only to appropriate types
                    has_min_length = 'min_length' in field_config
                    has_max_length = 'max_length' in field_config
                    has_pattern = 'pattern' in field_config
                    has_min = 'min' in field_config
                    has_max = 'max' in field_config
                    
                    if has_min_length or has_max_length or has_pattern:
                        # Should be string or union with string
                        if isinstance(type_str, str):
                            type_parts = [p.strip().lower() for p in type_str.split('|')]
                            has_string = 'string' in type_parts or type_str.lower() == 'string'
                            
                            if not has_string:
                                errors.append(f"{plugin_name}.{action_name}.{field_name}: min_length/max_length/pattern applied to non-string type {type_str}")
                    
                    if has_min or has_max:
                        # Should be number or union with number
                        if isinstance(type_str, str):
                            type_parts = [p.strip().lower() for p in type_str.split('|')]
                            has_number = any(t in type_parts for t in ['integer', 'float', 'number']) or type_str.lower() in ['integer', 'float', 'number']
                            
                            if not has_number:
                                errors.append(f"{plugin_name}.{action_name}.{field_name}: min/max applied to non-numeric type {type_str}")
        
        if errors:
            pytest.fail(f"Constraint application errors:\n" + "\n".join(errors))

