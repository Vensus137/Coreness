"""
Тесты опциональных полей с ограничениями
"""


class TestOptionalFieldsBasic:
    """Тесты базовой работы с опциональными полями"""

    def test_optional_fields_not_provided_validation_passes(self, validator):
        """Проверка: опциональные поля с ограничениями не переданы - валидация проходит"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test'})
        assert result.get('result') == 'success'


class TestOptionalStringMinLength:
    """Тесты опциональных строковых полей с min_length"""

    def test_optional_string_min_length_can_be_none(self, validator):
        """Проверка: опциональное поле с min_length может быть None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': None})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_can_be_empty(self, validator):
        """Проверка: опциональное поле с min_length может быть пустой строкой (ограничение игнорируется)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': ''})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_valid_value(self, validator):
        """Проверка: опциональное поле с min_length принимает валидное значение"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': 'valid'})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_ignores_max_length(self, validator):
        """Проверка: опциональное поле с max_length игнорирует ограничение (200 > max_length=100)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': 'a' * 200})
        assert result.get('result') == 'success'

    def test_optional_string_min_length_valid_range(self, validator):
        """Проверка: опциональное поле с min_length и max_length принимает значение в диапазоне"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_min_length': 'a' * 50})
        assert result.get('result') == 'success'


class TestOptionalStringPattern:
    """Тесты опциональных строковых полей с pattern"""

    def test_optional_string_pattern_can_be_none(self, validator):
        """Проверка: опциональное поле с pattern может быть None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_pattern': None})
        assert result.get('result') == 'success'

    def test_optional_string_pattern_ignores_constraint(self, validator):
        """Проверка: опциональное поле с pattern игнорирует ограничение (invalid не соответствует ^[A-Z]+$)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_pattern': 'invalid'})
        assert result.get('result') == 'success'

    def test_optional_string_pattern_valid_value(self, validator):
        """Проверка: опциональное поле с pattern принимает валидное значение"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_string_pattern': 'VALID'})
        assert result.get('result') == 'success'


class TestOptionalNumberMinMax:
    """Тесты опциональных числовых полей с min/max"""

    def test_optional_number_min_max_can_be_none(self, validator):
        """Проверка: опциональное поле с min/max может быть None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': None})
        assert result.get('result') == 'success'

    def test_optional_number_min_max_ignores_min(self, validator):
        """Проверка: опциональное поле с min/max игнорирует ограничение (0 < min=1)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': 0})
        assert result.get('result') == 'success'

    def test_optional_number_min_max_ignores_max(self, validator):
        """Проверка: опциональное поле с min/max игнорирует ограничение (200 > max=100)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': 200})
        assert result.get('result') == 'success'

    def test_optional_number_min_max_valid_value(self, validator):
        """Проверка: опциональное поле с min/max принимает валидное значение"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_number_min_max': 50})
        assert result.get('result') == 'success'


class TestOptionalFloatMinMax:
    """Тесты опциональных float полей с min/max"""

    def test_optional_float_min_max_can_be_none(self, validator):
        """Проверка: опциональное поле float с min/max может быть None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_float_min_max': None})
        assert result.get('result') == 'success'

    def test_optional_float_min_max_ignores_min(self, validator):
        """Проверка: опциональное поле float с min/max игнорирует ограничение (-1.0 < min=0.0)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_float_min_max': -1.0})
        assert result.get('result') == 'success'

    def test_optional_float_min_max_ignores_max(self, validator):
        """Проверка: опциональное поле float с min/max игнорирует ограничение (2.0 > max=1.0)"""
        result = validator.validate_action_input('test_service', 'action_with_optional_constraints', 
                                                {'required_field': 'test', 'optional_float_min_max': 2.0})
        assert result.get('result') == 'success'

