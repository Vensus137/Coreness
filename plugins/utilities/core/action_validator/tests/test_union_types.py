"""
Tests for union type validation
"""


class TestUnionTypes:
    """Tests for union types"""

    def test_union_integer_type(self, validator):
        """Check successful validation: integer in union type"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': 123, 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_array_type(self, validator):
        """Check successful validation: array in union type"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': [123, 456], 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_empty_array(self, validator):
        """Check: union type accepts empty array"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': [], 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_none_with_optional(self, validator):
        """Check successful validation: None in union type (optional: true automatically adds None)"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': None, 'state': None})
        assert result.get('result') == 'success'

    def test_union_required_field_can_be_none(self, validator):
        """Check successful validation: required field can be None (string|None)"""
        result = validator.validate_action_input('test_service', 'action_with_union', {'state': None})
        assert result.get('result') == 'success'

    def test_union_optional_can_be_none(self, validator):
        """Check: union type with optional: true can be None"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': None, 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_error_invalid_type(self, validator):
        """Check validation error: invalid type in union"""
        result = validator.validate_action_input('test_service', 'action_with_union', {'target_chat_id': 'invalid'})
        assert result.get('result') == 'error'

