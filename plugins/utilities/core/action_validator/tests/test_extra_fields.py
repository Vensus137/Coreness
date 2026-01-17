"""
Тесты обработки лишних полей
"""


class TestExtraFields:
    """Тесты лишних полей"""

    def test_extra_fields_ignored(self, validator):
        """Проверка: лишние поля игнорируются при валидации"""
        result = validator.validate_action_input('test_service', 'simple_action', {
            'name': 'Test',
            'age': 25,
            'extra_field_1': 'should be ignored during validation',
            'extra_field_2': 12345,
            'extra_field_3': {'nested': 'data'}
        })
        # Валидация должна пройти успешно, т.к. обязательные поля присутствуют
        assert result.get('result') == 'success'

