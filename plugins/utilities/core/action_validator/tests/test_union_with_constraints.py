"""
Tests for validation of union types with constraints (min_length, max_length, min, max)
"""


class TestUnionTypesWithConstraints:
    """Tests for union types with constraints"""

    def test_union_string_integer_with_min_length_string(self, validator):
        """Check: string|integer with min_length - string passes validation"""
        # Add test schema to mock
        validator.settings_manager._plugin_info['test_service']['actions']['union_string_int'] = {
            'input': {
                'data': {
                    'properties': {
                        'callback_query_id': {
                            'type': 'string|integer',
                            'optional': False,
                            'min_length': 1
                        }
                    }
                }
            }
        }
        # Clear cache for new action
        validator.invalidate_cache('test_service', 'union_string_int')
        
        # String should pass validation with min_length
        result = validator.validate_action_input('test_service', 'union_string_int', 
                                                {'callback_query_id': '12345'})
        assert result.get('result') == 'success'
    
    def test_union_string_integer_with_min_length_integer(self, validator):
        """Check: string|integer with min_length - integer passes validation"""
        # Integer should pass validation (min_length not applied to int)
        result = validator.validate_action_input('test_service', 'union_string_int', 
                                                {'callback_query_id': 12345})
        assert result.get('result') == 'success'
    
    def test_union_string_integer_with_min_length_empty_string(self, validator):
        """Check: string|integer with min_length - empty string passes (constraints not applied to union)"""
        # For union types constraints are not applied, so empty string passes validation
        result = validator.validate_action_input('test_service', 'union_string_int', 
                                                {'callback_query_id': ''})
        assert result.get('result') == 'success'

