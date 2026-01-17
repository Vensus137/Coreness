"""
Тесты обработки отсутствующих схем
"""


class TestSchemaHandling:
    """Тесты обработки схем"""

    def test_skip_validation_no_schema(self, validator):
        """Проверка пропуска валидации: нет схемы"""
        result = validator.validate_action_input('test_service', 'action_no_schema', {'any': 'data'})
        assert result.get('result') == 'success'

    def test_skip_validation_unknown_service(self, validator):
        """Проверка пропуска валидации: неизвестный сервис"""
        result = validator.validate_action_input('unknown_service', 'unknown_action', {'any': 'data'})
        assert result.get('result') == 'success'

