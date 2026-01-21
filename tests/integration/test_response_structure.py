"""
Integration test for action response structure
Verifies that all actions in configs have correct output format (result, error, response_data)
"""
import pytest
import yaml
from pathlib import Path

# Project root is already added to sys.path via pythonpath = ["."] in pyproject.toml
from tests.conftest import project_root  # noqa: F401


class TestResponseStructure:
    """Tests for action response structure"""
    
    def test_all_actions_have_correct_output_structure(self, project_root):
        """Verify: all actions have correct output structure"""
        plugins_dir = project_root / "plugins"
        errors = []
        
        # Scan all config.yaml files
        for config_path in plugins_dir.rglob("config.yaml"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                plugin_name = config.get('name', 'unknown')
                actions = config.get('actions', {})
                
                for action_name, action_config in actions.items():
                    output_config = action_config.get('output', {})
                    
                    if not output_config:
                        # No output - this is normal for some actions
                        continue
                    
                    # Verify presence of result
                    result_config = output_config.get('result')
                    if not result_config:
                        errors.append(f"{plugin_name}.{action_name}: missing 'result' in output")
                    
                    # Verify error format (should be object with code, message, details)
                    error_config = output_config.get('error')
                    if error_config:
                        if not isinstance(error_config, dict):
                            errors.append(f"{plugin_name}.{action_name}: 'error' should be an object, got {type(error_config).__name__}")
                        else:
                            # Verify error structure
                            properties = error_config.get('properties', {})
                            
                            if 'code' not in properties:
                                errors.append(f"{plugin_name}.{action_name}: 'error' should contain 'code'")
                            
                            if 'message' not in properties:
                                errors.append(f"{plugin_name}.{action_name}: 'error' should contain 'message'")
                            
                            # details are optional, but if present - should be an array
                            details_config = properties.get('details', {})
                            if details_config and details_config.get('type') != 'array':
                                errors.append(f"{plugin_name}.{action_name}: 'error.details' should be an array")
                    
                    # Verify response_data (if present)
                    response_data_config = output_config.get('response_data')
                    if response_data_config:
                        if not isinstance(response_data_config, dict):
                            errors.append(f"{plugin_name}.{action_name}: 'response_data' should be an object, got {type(response_data_config).__name__}")
                
            except Exception as e:
                errors.append(f"Error loading {config_path}: {str(e)}")
        
        if errors:
            pytest.fail(f"Output structure errors:\n" + "\n".join(errors))
    
    def test_all_actions_error_format_is_object(self, project_root):
        """Verify: all actions use new error format (object, not string)"""
        plugins_dir = project_root / "plugins"
        errors = []
        
        # Scan all config.yaml files
        for config_path in plugins_dir.rglob("config.yaml"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                plugin_name = config.get('name', 'unknown')
                actions = config.get('actions', {})
                
                for action_name, action_config in actions.items():
                    output_config = action_config.get('output', {})
                    
                    if not output_config:
                        continue
                    
                    error_config = output_config.get('error')
                    if error_config:
                        # Verify that error is an object, not a string
                        if isinstance(error_config, str):
                            errors.append(f"{plugin_name}.{action_name}: 'error' should be an object, got string")
                        elif isinstance(error_config, dict):
                            error_type = error_config.get('type')
                            if error_type == 'string':
                                errors.append(f"{plugin_name}.{action_name}: 'error.type' should be 'object', got 'string' (old format)")
            
            except Exception as e:
                errors.append(f"Error loading {config_path}: {str(e)}")
        
        if errors:
            pytest.fail(f"Error format errors (should be object):\n" + "\n".join(errors))

