"""
Тесты предобработки пустых строк для опциональных параметров
"""


class TestEmptyStringPreprocessing:
    """Тесты преобразования пустых строк в None для опциональных параметров"""

    def test_optional_array_empty_string_converted_to_none(self, validator):
        """Проверка: пустая строка для опционального array преобразуется в None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_array': ''})
        assert result.get('result') == 'success'

    def test_optional_integer_empty_string_converted_to_none(self, validator):
        """Проверка: пустая строка для опционального integer преобразуется в None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_integer': ''})
        assert result.get('result') == 'success'

    def test_optional_string_empty_string_remains_empty(self, validator):
        """Проверка: пустая строка для опционального string остается пустой строкой"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_string': ''})
        assert result.get('result') == 'success'

    def test_optional_union_array_empty_string_converted_to_none(self, validator):
        """Проверка: пустая строка для опционального union (integer|array) преобразуется в None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_union_array': ''})
        assert result.get('result') == 'success'

    def test_optional_union_string_empty_string_remains_empty(self, validator):
        """Проверка: пустая строка для опционального union (string|array) остается пустой строкой"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_union_string': ''})
        assert result.get('result') == 'success'

    def test_optional_array_none_remains_none(self, validator):
        """Проверка: None для опционального array остается None"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_array': None})
        assert result.get('result') == 'success'

    def test_optional_array_valid_value_unchanged(self, validator):
        """Проверка: валидное значение для опционального array не изменяется"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_array': [1, 2, 3]})
        assert result.get('result') == 'success'

    def test_optional_integer_valid_value_unchanged(self, validator):
        """Проверка: валидное значение для опционального integer не изменяется"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_integer': 42})
        assert result.get('result') == 'success'

    def test_optional_string_valid_value_unchanged(self, validator):
        """Проверка: валидное значение для опционального string не изменяется"""
        result = validator.validate_action_input('test_service', 'action_with_optional_array', 
                                                {'required_field': 'test', 'optional_string': 'valid'})
        assert result.get('result') == 'success'
