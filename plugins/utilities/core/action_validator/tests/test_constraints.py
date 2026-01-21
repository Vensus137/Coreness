"""
Tests for validation with constraints
"""


class TestStringConstraints:
    """Tests for string constraints"""

    def test_success_with_valid_constraints(self, validator):
        """Check successful validation with constraints"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Valid prompt', 'temperature': 1.0, 'json_mode': 'json_object'})
        assert result.get('result') == 'success'

    def test_error_empty_string_min_length(self, validator):
        """Check validation error: empty string (min_length=1)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', {'prompt': ''})
        assert result.get('result') == 'error'

    def test_error_string_too_long_max_length(self, validator):
        """Check validation error: string too long (max_length=100)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', {'prompt': 'A' * 101})
        assert result.get('result') == 'error'


class TestOptionalFieldConstraints:
    """Tests for optional field constraints"""

    def test_optional_temperature_ignores_max_constraint(self, validator):
        """Check: optional temperature field ignores constraints (3.0 > max)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': 3.0})
        assert result.get('result') == 'success'

    def test_optional_temperature_ignores_min_constraint(self, validator):
        """Check: optional temperature field ignores constraints (-1.0 < min)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': -1.0})
        assert result.get('result') == 'success'

    def test_optional_temperature_can_be_none(self, validator):
        """Check: optional temperature field can be None"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': None})
        assert result.get('result') == 'success'

    def test_optional_temperature_boundary_min(self, validator):
        """Check: optional temperature field with boundary value min (0.0)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': 0.0})
        assert result.get('result') == 'success'

    def test_optional_temperature_boundary_max(self, validator):
        """Check: optional temperature field with boundary value max (2.0)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': 2.0})
        assert result.get('result') == 'success'

    def test_all_optional_fields_not_provided(self, validator):
        """Check: all optional fields not provided - validation passes"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', {'prompt': 'Test'})
        assert result.get('result') == 'success'


class TestEnumConstraints:
    """Tests for enum constraints"""

    def test_error_invalid_enum_value(self, validator):
        """Check validation error: invalid enum value"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'json_mode': 'invalid'})
        assert result.get('result') == 'error'

    def test_success_valid_enum_value(self, validator):
        """Check successful validation: correct enum value"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'json_mode': 'json_schema'})
        assert result.get('result') == 'success'

    def test_optional_enum_can_be_none(self, validator):
        """Check: optional json_mode field can be None (enum not applied for None)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'json_mode': None})
        assert result.get('result') == 'success'

