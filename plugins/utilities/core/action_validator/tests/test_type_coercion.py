"""
Тесты приведения типов к целевому виду (_coerce_types)
"""


class TestTypeCoercion:
    """Тесты приведения типов"""

    def test_string_type_int_to_str(self, validator):
        """Проверка: type: string, пришло int → преобразуется в str"""
        # Добавляем тестовую схему
        validator.settings_manager._plugin_info['test_service']['actions']['coerce_string'] = {
            'input': {
                'data': {
                    'properties': {
                        'message': {
                            'type': 'string',
                            'optional': False
                        }
                    }
                }
            }
        }
        validator.invalidate_cache('test_service', 'coerce_string')
        
        # int должен преобразоваться в str
        result = validator.validate_action_input('test_service', 'coerce_string', {'message': 123})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('message'), str)
        assert validated_data.get('message') == '123'

    def test_string_type_float_to_str(self, validator):
        """Проверка: type: string, пришло float → преобразуется в str"""
        result = validator.validate_action_input('test_service', 'coerce_string', {'message': 123.45})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('message'), str)
        assert validated_data.get('message') == '123.45'

    def test_string_type_already_str(self, validator):
        """Проверка: type: string, пришло str → остается str"""
        result = validator.validate_action_input('test_service', 'coerce_string', {'message': 'test'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('message'), str)
        assert validated_data.get('message') == 'test'

    def test_string_type_bool_to_str(self, validator):
        """Проверка: type: string, пришло bool → преобразуется в str"""
        result = validator.validate_action_input('test_service', 'coerce_string', {'message': True})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('message'), str)
        assert validated_data.get('message') == 'True'
        
        result = validator.validate_action_input('test_service', 'coerce_string', {'message': False})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('message'), str)
        assert validated_data.get('message') == 'False'

    def test_integer_type_str_to_int(self, validator):
        """Проверка: type: integer, пришло str (только цифры) → преобразуется в int"""
        validator.settings_manager._plugin_info['test_service']['actions']['coerce_integer'] = {
            'input': {
                'data': {
                    'properties': {
                        'count': {
                            'type': 'integer',
                            'optional': False
                        }
                    }
                }
            }
        }
        validator.invalidate_cache('test_service', 'coerce_integer')
        
        # str с цифрами должен преобразоваться в int
        result = validator.validate_action_input('test_service', 'coerce_integer', {'count': '123'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('count'), int)
        assert validated_data.get('count') == 123

    def test_integer_type_str_negative_to_int(self, validator):
        """Проверка: type: integer, пришло str с отрицательным числом → преобразуется в int"""
        result = validator.validate_action_input('test_service', 'coerce_integer', {'count': '-456'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('count'), int)
        assert validated_data.get('count') == -456

    def test_integer_type_float_to_int(self, validator):
        """Проверка: type: integer, пришло float (целое) → преобразуется в int"""
        result = validator.validate_action_input('test_service', 'coerce_integer', {'count': 123.0})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('count'), int)
        assert validated_data.get('count') == 123

    def test_integer_type_already_int(self, validator):
        """Проверка: type: integer, пришло int → остается int"""
        result = validator.validate_action_input('test_service', 'coerce_integer', {'count': 123})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('count'), int)
        assert validated_data.get('count') == 123

    def test_integer_type_str_invalid_fails(self, validator):
        """Проверка: type: integer, пришло str (не только цифры) → ошибка валидации"""
        result = validator.validate_action_input('test_service', 'coerce_integer', {'count': 'abc'})
        assert result.get('result') == 'error'

    def test_integer_type_float_non_integer_fails(self, validator):
        """Проверка: type: integer, пришло float (не целое) → ошибка валидации"""
        result = validator.validate_action_input('test_service', 'coerce_integer', {'count': 123.45})
        assert result.get('result') == 'error'

    def test_float_type_int_to_float(self, validator):
        """Проверка: type: float, пришло int → преобразуется в float"""
        validator.settings_manager._plugin_info['test_service']['actions']['coerce_float'] = {
            'input': {
                'data': {
                    'properties': {
                        'price': {
                            'type': 'float',
                            'optional': False
                        }
                    }
                }
            }
        }
        validator.invalidate_cache('test_service', 'coerce_float')
        
        # int должен преобразоваться в float
        result = validator.validate_action_input('test_service', 'coerce_float', {'price': 123})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('price'), float)
        assert validated_data.get('price') == 123.0

    def test_float_type_str_to_float(self, validator):
        """Проверка: type: float, пришло str → преобразуется в float"""
        result = validator.validate_action_input('test_service', 'coerce_float', {'price': '123.45'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('price'), float)
        assert validated_data.get('price') == 123.45

    def test_float_type_already_float(self, validator):
        """Проверка: type: float, пришло float → остается float"""
        result = validator.validate_action_input('test_service', 'coerce_float', {'price': 123.45})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('price'), float)
        assert validated_data.get('price') == 123.45

    def test_union_types_not_coerced(self, validator):
        """Проверка: Union типы НЕ преобразуются, остаются как есть"""
        validator.settings_manager._plugin_info['test_service']['actions']['union_not_coerced'] = {
            'input': {
                'data': {
                    'properties': {
                        'callback_query_id': {
                            'type': 'string|integer',
                            'optional': False
                        }
                    }
                }
            }
        }
        validator.invalidate_cache('test_service', 'union_not_coerced')
        
        # int должен остаться int (не преобразовываться в str)
        result = validator.validate_action_input('test_service', 'union_not_coerced', {'callback_query_id': 12345})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('callback_query_id'), int)
        assert validated_data.get('callback_query_id') == 12345
        
        # str должен остаться str (не преобразовываться в int)
        result2 = validator.validate_action_input('test_service', 'union_not_coerced', {'callback_query_id': '12345'})
        assert result2.get('result') == 'success'
        validated_data2 = result2.get('validated_data', {})
        assert isinstance(validated_data2.get('callback_query_id'), str)
        assert validated_data2.get('callback_query_id') == '12345'

    def test_coercion_preserves_extra_fields(self, validator):
        """Проверка: преобразование типов сохраняет дополнительные поля"""
        result = validator.validate_action_input('test_service', 'coerce_string', {
            'message': 123,
            'extra_field': 'extra_value'
        })
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert validated_data.get('message') == '123'
        assert validated_data.get('extra_field') == 'extra_value'

    def test_coercion_multiple_fields(self, validator):
        """Проверка: преобразование нескольких полей одновременно"""
        validator.settings_manager._plugin_info['test_service']['actions']['coerce_multiple'] = {
            'input': {
                'data': {
                    'properties': {
                        'name': {
                            'type': 'string',
                            'optional': False
                        },
                        'age': {
                            'type': 'integer',
                            'optional': False
                        },
                        'price': {
                            'type': 'float',
                            'optional': False
                        }
                    }
                }
            }
        }
        validator.invalidate_cache('test_service', 'coerce_multiple')
        
        result = validator.validate_action_input('test_service', 'coerce_multiple', {
            'name': 123,  # int → str
            'age': '25',  # str → int
            'price': 100  # int → float
        })
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('name'), str)
        assert validated_data.get('name') == '123'
        assert isinstance(validated_data.get('age'), int)
        assert validated_data.get('age') == 25
        assert isinstance(validated_data.get('price'), float)
        assert validated_data.get('price') == 100.0

    def test_boolean_type_str_true_to_bool(self, validator):
        """Проверка: type: boolean, пришло 'true' → преобразуется в True"""
        validator.settings_manager._plugin_info['test_service']['actions']['coerce_boolean'] = {
            'input': {
                'data': {
                    'properties': {
                        'enabled': {
                            'type': 'boolean',
                            'optional': False
                        }
                    }
                }
            }
        }
        validator.invalidate_cache('test_service', 'coerce_boolean')
        
        result = validator.validate_action_input('test_service', 'coerce_boolean', {'enabled': 'true'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('enabled'), bool)
        assert validated_data.get('enabled') is True

    def test_boolean_type_str_false_to_bool(self, validator):
        """Проверка: type: boolean, пришло 'false' → преобразуется в False"""
        result = validator.validate_action_input('test_service', 'coerce_boolean', {'enabled': 'false'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('enabled'), bool)
        assert validated_data.get('enabled') is False

    def test_boolean_type_str_case_insensitive(self, validator):
        """Проверка: type: boolean, пришло 'True' или 'FALSE' → преобразуется с учетом регистра"""
        result = validator.validate_action_input('test_service', 'coerce_boolean', {'enabled': 'True'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert validated_data.get('enabled') is True
        
        result = validator.validate_action_input('test_service', 'coerce_boolean', {'enabled': 'FALSE'})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert validated_data.get('enabled') is False

    def test_boolean_type_already_bool(self, validator):
        """Проверка: type: boolean, пришло bool → остается bool"""
        result = validator.validate_action_input('test_service', 'coerce_boolean', {'enabled': True})
        assert result.get('result') == 'success'
        validated_data = result.get('validated_data', {})
        assert isinstance(validated_data.get('enabled'), bool)
        assert validated_data.get('enabled') is True

    def test_boolean_type_invalid_str_not_converted(self, validator):
        """Проверка: type: boolean, пришло невалидная строка → Pydantic может принять или отклонить"""
        # Pydantic автоматически преобразует некоторые строки ('yes'→True, 'no'→False)
        # Но мы преобразуем только явные 'true'/'false', остальное оставляем Pydantic
        result = validator.validate_action_input('test_service', 'coerce_boolean', {'enabled': 'invalid_boolean_string'})
        # Pydantic должен отклонить явно невалидную строку
        assert result.get('result') == 'error'

