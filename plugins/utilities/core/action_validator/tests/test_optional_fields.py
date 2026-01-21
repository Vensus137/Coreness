"""
Tests for optional fields with constraints
"""


class TestOptionalFieldsBasic:
    """Basic tests for optional fields"""

    def test_optional_fields_not_provided_validation_passes(self, validator):
        """Check: optional fields with constraints not provided - validation passes"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test'})
        assert result.get('result') == 'success'


class TestOptionalStringMinLength:
    """Tests for optional string fields with min_length"""

    def test_optional_string_min_length_can_be_none(self, validator):
        """Check: optional field with min_length can be None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': None})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_can_be_empty(self, validator):
        """Check: optional field with min_length can be empty string (constraint ignored)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': ''})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_valid_value(self, validator):
        """Check: optional field with min_length accepts valid value"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': 'valid'})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_ignores_max_length(self, validator):
        """Check: optional field with max_length ignores constraint (200 > max_length=100)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': 'a' * 200})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_valid_range(self, validator):
        """Check: optional field with min_length and max_length accepts value in range"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': 'a' * 50})
        assert result.get('result') == 'success'


class TestOptionalStringPattern:
    """Tests for optional string fields with pattern"""

    def test_optional_string_pattern_can_be_none(self, validator):
        """Check: optional field with pattern can be None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_pattern': None})
        assert result.get('result') == 'success'

    def test_optional_string_pattern_ignores_constraint(self, validator):
        """Check: optional field with pattern ignores constraint (invalid doesn't match ^[A-Z]+$)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_pattern': 'invalid'})
        assert result.get('result') == 'success'

    def test_optional_string_pattern_valid_value(self, validator):
        """Check: optional field with pattern accepts valid value"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_pattern': 'VALID'})
        assert result.get('result') == 'success'


class TestOptionalNumberMinMax:
    """Tests for optional number fields with min/max"""

    def test_optional_number_min_max_can_be_none(self, validator):
        """Check: optional field with min/max can be None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': None})
        assert result.get('result') == 'success'

    def test_optional_number_min_max_ignores_min(self, validator):
        """Check: optional field with min/max ignores constraint (0 < min=1)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': 0})
        assert result.get('result') == 'success'

    def test_optional_number_min_max_ignores_max(self, validator):
        """Check: optional field with min/max ignores constraint (200 > max=100)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': 200})
        assert result.get('result') == 'success'

    def test_optional_number_min_max_valid_value(self, validator):
        """Check: optional field with min/max accepts valid value"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': 50})
        assert result.get('result') == 'success'


class TestOptionalFloatMinMax:
    """Tests for optional float fields with min/max"""

    def test_optional_float_min_max_can_be_none(self, validator):
        """Check: optional float field with min/max can be None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_float_min_max': None})
        assert result.get('result') == 'success'

    def test_optional_float_min_max_ignores_min(self, validator):
        """Check: optional float field with min/max ignores constraint (-1.0 < min=0.0)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_float_min_max': -1.0})
        assert result.get('result') == 'success'

    def test_optional_float_min_max_ignores_max(self, validator):
        """Check: optional float field with min/max ignores constraint (2.0 > max=1.0)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_float_min_max': 2.0})
        assert result.get('result') == 'success'

