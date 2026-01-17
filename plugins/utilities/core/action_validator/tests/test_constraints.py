"""
Тесты валидации с ограничениями
"""


class TestStringConstraints:
    """Тесты ограничений для строк"""

    def test_success_with_valid_constraints(self, validator):
        """Проверка успешной валидации с ограничениями"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Valid prompt', 'temperature': 1.0, 'json_mode': 'json_object'})
        assert result.get('result') == 'success'

    def test_error_empty_string_min_length(self, validator):
        """Проверка ошибки валидации: пустая строка (min_length=1)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', {'prompt': ''})
        assert result.get('result') == 'error'

    def test_error_string_too_long_max_length(self, validator):
        """Проверка ошибки валидации: слишком длинная строка (max_length=100)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', {'prompt': 'A' * 101})
        assert result.get('result') == 'error'


class TestOptionalFieldConstraints:
    """Тесты ограничений для опциональных полей"""

    def test_optional_temperature_ignores_max_constraint(self, validator):
        """Проверка: опциональное поле temperature игнорирует ограничения (3.0 > max)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': 3.0})
        assert result.get('result') == 'success'

    def test_optional_temperature_ignores_min_constraint(self, validator):
        """Проверка: опциональное поле temperature игнорирует ограничения (-1.0 < min)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': -1.0})
        assert result.get('result') == 'success'

    def test_optional_temperature_can_be_none(self, validator):
        """Проверка: опциональное поле temperature может быть None"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': None})
        assert result.get('result') == 'success'

    def test_optional_temperature_boundary_min(self, validator):
        """Проверка: опциональное поле temperature с граничным значением min (0.0)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': 0.0})
        assert result.get('result') == 'success'

    def test_optional_temperature_boundary_max(self, validator):
        """Проверка: опциональное поле temperature с граничным значением max (2.0)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'temperature': 2.0})
        assert result.get('result') == 'success'

    def test_all_optional_fields_not_provided(self, validator):
        """Проверка: все опциональные поля не переданы - валидация проходит"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', {'prompt': 'Test'})
        assert result.get('result') == 'success'


class TestEnumConstraints:
    """Тесты ограничений для enum"""

    def test_error_invalid_enum_value(self, validator):
        """Проверка ошибки валидации: неверное enum значение"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'json_mode': 'invalid'})
        assert result.get('result') == 'error'

    def test_success_valid_enum_value(self, validator):
        """Проверка успешной валидации: правильное enum значение"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'json_mode': 'json_schema'})
        assert result.get('result') == 'success'

    def test_optional_enum_can_be_none(self, validator):
        """Проверка: опциональное поле json_mode может быть None (enum не применяется для None)"""
        result = validator.validate_action_input('test_service', 'action_with_constraints', 
                                                {'prompt': 'Test', 'json_mode': None})
        assert result.get('result') == 'success'

