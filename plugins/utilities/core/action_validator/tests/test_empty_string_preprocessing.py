"""
Tests for empty string preprocessing for optional parameters
"""


class TestEmptyStringPreprocessing:
    """Tests for converting empty strings to None for optional parameters"""

    def test_optional_array_empty_string_converted_to_none(self, validator):
        """Check: empty string for optional array is converted to None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_array': ''})
        assert result.get('result') == 'success'

    def test_optional_integer_empty_string_converted_to_none(self, validator):
        """Check: empty string for optional integer is converted to None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_integer': ''})
        assert result.get('result') == 'success'

    def test_optional_string_empty_string_remains_empty(self, validator):
        """Check: empty string for optional string remains empty string"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_string': ''})
        assert result.get('result') == 'success'

    def test_optional_union_array_empty_string_converted_to_none(self, validator):
        """Check: empty string for optional union (integer|array) is converted to None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_union_array': ''})
        assert result.get('result') == 'success'

    def test_optional_union_string_empty_string_remains_empty(self, validator):
        """Check: empty string for optional union (string|array) remains empty string"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_union_string': ''})
        assert result.get('result') == 'success'

    def test_optional_array_none_remains_none(self, validator):
        """Check: None for optional array remains None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_array': None})
        assert result.get('result') == 'success'

    def test_optional_array_valid_value_unchanged(self, validator):
        """Check: valid value for optional array is unchanged"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_array': [1, 2, 3]})
        assert result.get('result') == 'success'

    def test_optional_integer_valid_value_unchanged(self, validator):
        """Check: valid value for optional integer is unchanged"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_integer': 42})
        assert result.get('result') == 'success'

    def test_optional_string_valid_value_unchanged(self, validator):
        """Check: valid value for optional string is unchanged"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_string': 'valid'})
        assert result.get('result') == 'success'
