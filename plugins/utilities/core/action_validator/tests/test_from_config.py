"""
Тесты для функциональности from_config: true
Проверяют автоматическое извлечение параметров из _config
"""


class TestFromConfig:
    """Тесты извлечения параметров из _config"""
    
    def test_extract_from_config_success(self, validator):
        """Проверка успешного извлечения параметра из _config"""
        # Данные с _config
        data = {
            'prompt': 'Test prompt',
            '_config': {
                'openrouter_token': 'sk-test-token-123'
            }
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        # Параметр должен быть извлечен из _config
        assert validated_data.get('openrouter_token') == 'sk-test-token-123'
        assert validated_data.get('prompt') == 'Test prompt'
    
    def test_extract_from_config_explicit_value_priority(self, validator):
        """Проверка: явно переданное значение имеет приоритет над _config"""
        # Данные с _config и явным значением
        data = {
            'prompt': 'Test prompt',
            'openrouter_token': 'explicit-token',
            '_config': {
                'openrouter_token': 'sk-test-token-123'
            }
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        # Явно переданное значение должно иметь приоритет
        assert validated_data.get('openrouter_token') == 'explicit-token'
    
    def test_extract_from_config_missing_in_config(self, validator):
        """Проверка: если параметр отсутствует в _config, валидация должна провалиться для обязательного поля"""
        # Данные без _config и без параметра
        data = {
            'prompt': 'Test prompt'
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        # Обязательное поле отсутствует - должна быть ошибка
        assert result.get('result') == 'error'
    
    def test_extract_from_config_empty_config(self, validator):
        """Проверка: пустой _config не должен вызывать ошибок"""
        # Данные с пустым _config
        data = {
            'prompt': 'Test prompt',
            '_config': {}
        }
        
        result = validator.validate_action_input('test_service', 'action_with_from_config', data)
        
        # Обязательное поле отсутствует - должна быть ошибка
        assert result.get('result') == 'error'
    
    def test_extract_from_config_optional_field(self, validator):
        """Проверка: опциональное поле с from_config может отсутствовать"""
        # Данные с _config, но без опционального поля
        data = {
            'prompt': 'Test prompt',
            '_config': {
                'openrouter_token': 'sk-test-token-123'
            }
        }
        
        result = validator.validate_action_input('test_service', 'action_with_optional_from_config', data)
        
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        # Обязательное поле должно быть извлечено
        assert validated_data.get('openrouter_token') == 'sk-test-token-123'
        # Опциональное поле может отсутствовать
        assert 'optional_token' not in validated_data or validated_data.get('optional_token') is None

