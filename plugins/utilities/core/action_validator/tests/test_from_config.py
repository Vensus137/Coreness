"""
Tests for from_config: true functionality
Check automatic parameter extraction from _config
"""


class TestFromConfig:
    """Tests for parameter extraction from _config"""
    
    def test_extract_from_config_success(self, validator):
        """Check successful parameter extraction from _config"""
        # Data with _config
        data = {
            'prompt': 'Test prompt',
            '_config': {
                'openrouter_token': 'sk-test-token-123'
            }
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        # Parameter should be extracted from _config
        assert validated_data.get('openrouter_token') == 'sk-test-token-123'
        assert validated_data.get('prompt') == 'Test prompt'
    
    def test_extract_from_config_explicit_value_priority(self, validator):
        """Check: explicitly passed value has priority over _config"""
        # Data with _config and explicit value
        data = {
            'prompt': 'Test prompt',
            'openrouter_token': 'explicit-token',
            '_config': {
                'openrouter_token': 'sk-test-token-123'
            }
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        # Explicitly passed value should have priority
        assert validated_data.get('openrouter_token') == 'explicit-token'
    
    def test_extract_from_config_missing_in_config(self, validator):
        """Check: if parameter missing in _config, validation should fail for required field"""
        # Data without _config and without parameter
        data = {
            'prompt': 'Test prompt'
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        # Required field missing - should be error
        assert result.get('result') == 'error'
    
    def test_extract_from_config_empty_config(self, validator):
        """Check: empty _config should not cause errors"""
        # Data with empty _config
        data = {
            'prompt': 'Test prompt',
            '_config': {}
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        # Required field missing - should be error
        assert result.get('result') == 'error'
    
    def test_extract_from_config_optional_field(self, validator):
        """Check: optional field with from_config can be missing"""
        # Data with _config, but without optional field
        data = {
            'prompt': 'Test prompt',
            '_config': {
                'openrouter_token': 'sk-test-token-123'
            }
        }
        
        result = validator.validate_action_input('test_service', 'action_with_optional_from_config', data)
        
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        # Required field should be extracted
        assert validated_data.get('openrouter_token') == 'sk-test-token-123'
        # Optional field can be missing
        assert 'optional_token' not in validated_data or validated_data.get('optional_token') is None

