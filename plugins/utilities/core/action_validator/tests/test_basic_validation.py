"""
Тесты базовой валидации
"""


class TestSimpleValidation:
    """Тесты простой валидации"""

    def test_success_with_required_and_optional_field(self, validator):
        """Проверка успешной валидации с обязательным и опциональным полем"""
        result = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test', 'age': 25})
        assert result.get('result') == 'success'

    def test_success_without_optional_field(self, validator):
        """Проверка успешной валидации без опционального поля"""
        result = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test'})
        assert result.get('result') == 'success'

    def test_error_missing_required_field(self, validator):
        """Проверка ошибки валидации: отсутствует обязательное поле"""
        result = validator.validate_action_input('test_service', 'simple_action', {})
        assert result.get('result') == 'error'

    def test_error_invalid_optional_field_type(self, validator):
        """Проверка ошибки валидации: неверный тип опционального поля"""
        result = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test', 'age': 'invalid'})
        assert result.get('result') == 'error'

