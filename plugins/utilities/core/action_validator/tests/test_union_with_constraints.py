"""
Тесты валидации union типов с ограничениями (min_length, max_length, min, max)
"""


class TestUnionTypesWithConstraints:
    """Тесты union типов с ограничениями"""

    def test_union_string_integer_with_min_length_string(self, validator):
        """Проверка: string|integer с min_length - строка проходит валидацию"""
        # Добавляем тестовую схему в mock
        validator.settings_manager._plugin_info['test_service']['actions']['union_string_int'] = {
            'input': {
                'data': {
                    'properties': {
                        'callback_query_id': {
                            'type': 'string|integer',
                            'optional': False,
                            'min_length': 1
                        }
                    }
                }
            }
        }
        # Очищаем кэш для нового действия
        validator.invalidate_cache('test_service', 'union_string_int')
        
        # Строка должна пройти валидацию с min_length
        result = validator.validate_action_input('test_service', 'union_string_int', 
                                                {'callback_query_id': '12345'})
        assert result.get('result') == 'success'
    
    def test_union_string_integer_with_min_length_integer(self, validator):
        """Проверка: string|integer с min_length - integer проходит валидацию"""
        # Integer должен пройти валидацию (min_length не применяется к int)
        result = validator.validate_action_input('test_service', 'union_string_int', 
                                                {'callback_query_id': 12345})
        assert result.get('result') == 'success'
    
    def test_union_string_integer_with_min_length_empty_string(self, validator):
        """Проверка: string|integer с min_length - пустая строка проходит (ограничения не применяются к union)"""
        # Для union типов ограничения не применяются, поэтому пустая строка проходит валидацию
        result = validator.validate_action_input('test_service', 'union_string_int', 
                                                {'callback_query_id': ''})
        assert result.get('result') == 'success'

