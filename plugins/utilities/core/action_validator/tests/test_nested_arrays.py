"""
Тесты валидации вложенных объектов в массивах
"""


class TestNestedArrays:
    """Тесты вложенных массивов"""

    def test_success_nested_array_with_objects(self, validator):
        """Проверка успешной валидации: массив с вложенными объектами"""
        result = validator.validate_action_input('test_service', 'action_with_nested_array', 
                                                {'items': [{'id': 1, 'name': 'Item 1'}, {'id': 2}]})
        assert result.get('result') == 'success'

    def test_error_missing_required_field_in_nested_object(self, validator):
        """Проверка ошибки валидации: отсутствует обязательное поле id во вложенном объекте"""
        result = validator.validate_action_input('test_service', 'action_with_nested_array', 
                                                {'items': [{'id': 1}, {'name': 'Item 2'}]})
        assert result.get('result') == 'error'

    def test_error_invalid_type_in_nested_object(self, validator):
        """Проверка ошибки валидации: неверный тип во вложенном объекте"""
        result = validator.validate_action_input('test_service', 'action_with_nested_array', 
                                                {'items': [{'id': 'invalid'}]})
        assert result.get('result') == 'error'

