"""
Тесты валидации union типов
"""


class TestUnionTypes:
    """Тесты union типов"""

    def test_union_integer_type(self, validator):
        """Проверка успешной валидации: integer в union типе"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': 123, 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_array_type(self, validator):
        """Проверка успешной валидации: array в union типе"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': [123, 456], 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_empty_array(self, validator):
        """Проверка: union тип принимает пустой массив"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': [], 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_none_with_optional(self, validator):
        """Проверка успешной валидации: None в union типе (optional: true автоматически добавляет None)"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': None, 'state': None})
        assert result.get('result') == 'success'

    def test_union_required_field_can_be_none(self, validator):
        """Проверка успешной валидации: обязательное поле может быть None (string|None)"""
        result = validator.validate_action_input('test_service', 'action_with_union', {'state': None})
        assert result.get('result') == 'success'

    def test_union_optional_can_be_none(self, validator):
        """Проверка: union тип с optional: true может быть None"""
        result = validator.validate_action_input('test_service', 'action_with_union', 
                                                {'target_chat_id': None, 'state': 'active'})
        assert result.get('result') == 'success'

    def test_union_error_invalid_type(self, validator):
        """Проверка ошибки валидации: неверный тип в union"""
        result = validator.validate_action_input('test_service', 'action_with_union', {'target_chat_id': 'invalid'})
        assert result.get('result') == 'error'

