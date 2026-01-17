"""
Тесты кэширования моделей валидации
"""


class TestCaching:
    """Тесты кэширования"""

    def test_caching(self, validator):
        """Проверка, что валидация работает корректно при повторных вызовах (кэширование)"""
        # Первый вызов
        result1 = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test'})
        assert result1.get('result') == 'success', "Первый вызов должен быть успешным"
        
        # Второй вызов с другими данными (должен использовать кэш модели, но это детали реализации)
        result2 = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test2'})
        assert result2.get('result') == 'success', "Второй вызов должен быть успешным"
        
        # Третий вызов с невалидными данными
        result3 = validator.validate_action_input('test_service', 'simple_action', {})
        assert result3.get('result') == 'error', "Вызов без обязательных полей должен вернуть ошибку"

