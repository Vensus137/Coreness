"""
Basic validation tests
"""


class TestSimpleValidation:
    """Simple validation tests"""

    def test_success_with_required_and_optional_field(self, validator):
        """Check successful validation with required and optional field"""
        result = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test', 'age': 25})
        assert result.get('result') == 'success'

    def test_success_without_optional_field(self, validator):
        """Check successful validation without optional field"""
        result = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test'})
        assert result.get('result') == 'success'

    def test_error_missing_required_field(self, validator):
        """Check validation error: missing required field"""
        result = validator.validate_action_input('test_service', 'simple_action', {})
        assert result.get('result') == 'error'

    def test_error_invalid_optional_field_type(self, validator):
        """Check validation error: invalid optional field type"""
        result = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test', 'age': 'invalid'})
        assert result.get('result') == 'error'

