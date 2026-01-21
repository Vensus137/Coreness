"""
Tests for handling extra fields
"""


class TestExtraFields:
    """Tests for extra fields"""

    def test_extra_fields_ignored(self, validator):
        """Check: extra fields are ignored during validation"""
        result = validator.validate_action_input('test_service', 'simple_action', {
            'name': 'Test',
            'age': 25,
            'extra_field_1': 'should be ignored during validation',
            'extra_field_2': 12345,
            'extra_field_3': {'nested': 'data'}
        })
        # Validation should pass successfully, as required fields are present
        assert result.get('result') == 'success'

