"""
Утилита для валидации входных данных действий по схемам из config.yaml
"""

from typing import Any, Dict, List, Literal, Optional, Union, get_args, get_origin

from pydantic import ConfigDict, Field, ValidationError, create_model


class ActionValidator:
    """
    Утилита для валидации входных данных действий по схемам из config.yaml
    
    Использует Pydantic для валидации данных на основе схем, описанных в config.yaml сервисов.
    Кэширует созданные Pydantic модели для производительности.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Кэш Pydantic моделей (ключ: "service_name.action_name")
        self._validation_models: Dict[str, Any] = {}
    
    def validate_action_input(self, service_name: str, action_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидация входных данных действия по схеме из config.yaml
        """
        try:
            # Получаем схему из config.yaml (уже кэшировано в PluginsManager)
            input_schema = self._get_input_schema(service_name, action_name)
            
            if not input_schema:
                # Нет схемы - пропускаем валидацию, возвращаем исходные данные
                return {
                    "result": "success",
                    "validated_data": data
                }
            
            # Получаем или создаем Pydantic модель
            model = self._get_or_create_model(service_name, action_name, input_schema)
            
            if not model:
                # Не удалось создать модель - пропускаем, возвращаем исходные данные
                return {
                    "result": "success",
                    "validated_data": data
                }
            
            # Предобработка данных: извлекаем значения из _config для полей с from_config
            processed_data = self._extract_from_config(data, input_schema)
            
            # Предобработка данных: для опциональных параметров преобразуем пустые строки в None
            # если тип параметра не string (например, array, integer и т.д.)
            processed_data = self._preprocess_data(processed_data, input_schema)
            
            # Приведение типов к целевому (модифицируем данные "на лету")
            # Это гарантирует, что преобразованные значения сохраняются
            self._coerce_types(processed_data, input_schema)
            
            # Валидируем данные через Pydantic (только для проверки ограничений: min/max, pattern, enum и т.д.)
            # Pydantic НЕ преобразует типы автоматически, поэтому мы делаем это сами выше
            validated_model = model(**processed_data)
            
            # Получаем валидированные данные из модели (для default значений, если поле не было передано)
            validated_data_dict = validated_model.model_dump(exclude_unset=True)
            
            # Объединяем: processed_data (с преобразованными типами) имеет приоритет
            # validated_data_dict нужен только для default значений полей, которые не были переданы
            final_data = {**validated_data_dict, **processed_data}
            
            return {
                "result": "success",
                "validated_data": final_data
            }
            
        except ValidationError as e:
            # Структурированные ошибки валидации
            errors = []
            for error in e.errors():
                field_path = ".".join(str(x) for x in error["loc"])
                errors.append({
                    "field": field_path,
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input")
                })
            
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Ошибка валидации входных данных",
                    "details": errors
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации для {service_name}.{action_name}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Ошибка валидации: {str(e)}"
                }
            }
    
    def _get_input_schema(self, service_name: str, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение схемы входных данных из config.yaml
        """
        try:
            # Получаем информацию о плагине (уже кэшировано в PluginsManager)
            plugin_info = self.settings_manager.get_plugin_info(service_name)
            
            if not plugin_info:
                return None
            
            # Извлекаем схему действия
            actions = plugin_info.get('actions', {})
            action_config = actions.get(action_name, {})
            
            if not action_config:
                return None
            
            # Получаем input схему
            input_config = action_config.get('input', {})
            
            if not input_config:
                return None
            
            # Структура: input.data.properties (см. config.yaml)
            data_config = input_config.get('data', {})
            properties = data_config.get('properties', {})
            
            return properties if properties else None
            
        except Exception as e:
            self.logger.error(f"Ошибка получения схемы для {service_name}.{action_name}: {e}")
            return None
    
    def _get_or_create_model(self, service_name: str, action_name: str, schema: Dict[str, Any]):
        """
        Получение или создание Pydantic модели с кэшированием
        """
        cache_key = f"{service_name}.{action_name}"
        
        # Проверяем кэш
        if cache_key in self._validation_models:
            return self._validation_models[cache_key]
        
        # Создаем модель
        model = self._create_pydantic_model(schema)
        
        # Кэшируем
        if model:
            self._validation_models[cache_key] = model
        
        return model
    
    def _create_pydantic_model(self, schema: Dict[str, Any], model_name: str = 'ValidationModel'):
        """
        Создание Pydantic модели из схемы config.yaml (рекурсивно для вложенных объектов)
        """
        try:
            pydantic_fields = {}
            
            for field_name, field_config in schema.items():
                # Определяем тип поля (может быть union через |)
                type_str = field_config.get('type', 'string')
                
                # Определяем обязательность (по умолчанию обязательное для input схем)
                is_optional = field_config.get('optional', False)
                
                # Проверяем, есть ли None в типе
                has_none_in_type = isinstance(type_str, str) and 'none' in [p.strip().lower() for p in type_str.split('|')]
                
                # Парсим тип
                field_type = self._parse_type_string(type_str, field_config)
                
                # Создаем Field с ограничениями
                field_kwargs = {}
                
                # Проверяем, является ли тип Union для применения ограничений
                origin = get_origin(field_type)
                is_union = origin == Union
                
                # Получаем аргументы Union
                union_args = get_args(field_type) if is_union else []
                
                # Определяем, есть ли в типе строка или число
                has_string_type = (isinstance(field_type, type) and field_type is str) or (is_union and str in union_args)
                has_integer_type = (isinstance(field_type, type) and field_type is int) or (is_union and int in union_args)
                has_float_type = (isinstance(field_type, type) and field_type is float) or (is_union and float in union_args)
                
                # Для опциональных полей не применяем ограничения валидации
                # Pydantic сам обработает None для Optional полей, но если передана пустая строка или 0,
                # ограничения все равно применятся. Поэтому для опциональных полей ограничения не применяем.
                # Для Union типов также не применяем ограничения - оставляем как есть
                if not is_optional and not is_union:
                    # Применяем ограничения через Field только для НЕ-union типов
                    # Ограничения для строк (если это строка)
                    if has_string_type:
                        if 'min_length' in field_config:
                            field_kwargs['min_length'] = field_config['min_length']
                        if 'max_length' in field_config:
                            field_kwargs['max_length'] = field_config['max_length']
                        if 'pattern' in field_config:
                            field_kwargs['regex'] = field_config['pattern']
                    
                    # Ограничения для чисел (если это число)
                    if has_integer_type or has_float_type:
                        if 'min' in field_config:
                            field_kwargs['ge'] = field_config['min']
                        if 'max' in field_config:
                            field_kwargs['le'] = field_config['max']
                
                # Enum значения
                if 'enum' in field_config:
                    enum_values = tuple(field_config['enum'])
                    literal_type = Literal[enum_values]
                    # Если поле опциональное или есть None в типе, делаем Optional[Literal[...]]
                    if is_optional or has_none_in_type:
                        field_type = Optional[literal_type]
                    else:
                        field_type = literal_type
                
                # Создаем поле
                if is_optional:
                    # Если еще не сделали Optional (для enum уже сделали выше)
                    if 'enum' not in field_config:
                        # Проверяем, не является ли уже Union/Optional
                        origin = get_origin(field_type)
                        
                        # Если None уже есть в типе (через |None), не добавляем Optional еще раз
                        if not has_none_in_type:
                            # Проверяем, не является ли уже Optional
                            if origin == Union:
                                # Проверяем, есть ли уже None в Union
                                args = get_args(field_type)
                                if type(None) not in args:
                                    # Добавляем None в union только если его там еще нет
                                    field_type = Union[tuple(list(args) + [type(None)])]
                            elif origin is None:
                                # Простой тип (не Union, не Optional) - делаем Optional
                                field_type = Optional[field_type]
                    field_kwargs['default'] = None
                    pydantic_fields[field_name] = (field_type, Field(**field_kwargs))
                else:
                    # Required field - без default
                    # Если None в типе, оставляем как есть (Union[Type, None])
                    # Если нет None в типе, просто Type
                    pydantic_fields[field_name] = (field_type, Field(**field_kwargs))
            
            # Создаем динамическую Pydantic модель
            if not pydantic_fields:
                return None
            
            # Создаем модель с явным указанием игнорирования лишних полей
            # Это гарантирует, что поля, не описанные в схеме, будут проигнорированы
            Model = create_model(
                model_name,
                __config__=ConfigDict(extra='ignore'),
                **pydantic_fields
            )
            return Model
            
        except Exception as e:
            self.logger.error(f"Ошибка создания Pydantic модели: {e}")
            return None
    
    def _extract_from_config(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечение значений из _config для полей с from_config: true
        Если поле не передано в data, но указано from_config: true, берем значение из data.get('_config', {}).get(field_name)
        """
        processed_data = data.copy()
        tenant_config = data.get('_config', {})
        
        for field_name, field_config in schema.items():
            # Пропускаем, если поле уже есть в data (явно передано)
            if field_name in processed_data:
                continue
            
            # Проверяем, нужно ли брать из _config
            from_config = field_config.get('from_config', False)
            if not from_config:
                continue
            
            # Извлекаем значение из _config
            config_value = tenant_config.get(field_name)
            if config_value is not None:
                processed_data[field_name] = config_value
        
        return processed_data
    
    def _preprocess_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Предобработка данных перед валидацией:
        - Для опциональных параметров не-строкового типа преобразуем пустые строки в None
        - Это позволяет корректно обрабатывать fallback: для опциональных параметров
        """
        processed_data = data.copy()
        
        for field_name, field_config in schema.items():
            if field_name not in processed_data:
                continue
            
            value = processed_data[field_name]
            
            # Пропускаем, если значение уже None
            if value is None:
                continue
            
            # Проверяем, является ли поле опциональным
            is_optional = field_config.get('optional', False)
            
            if not is_optional:
                continue
            
            # Получаем тип поля
            type_str = field_config.get('type', 'string')
            
            # Если это пустая строка и тип не string (или не содержит string в union)
            if value == "":
                # Проверяем, является ли тип строкой
                is_string_type = False
                if isinstance(type_str, str):
                    # Разбираем union типы (например, "string|array")
                    type_parts = [t.strip().lower() for t in type_str.split('|')]
                    is_string_type = 'string' in type_parts
                elif type_str == 'string':
                    is_string_type = True
                
                # Если тип не строка (например, array, integer и т.д.), преобразуем пустую строку в None
                if not is_string_type:
                    processed_data[field_name] = None
        
        return processed_data
    
    def _coerce_types(self, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Приведение типов к указанному в схеме (только для НЕ-union типов)
        Модифицирует данные "на лету" в переданном словаре
        
        Правила преобразования:
        - Если указан type: string, а пришло что-то другое (кроме None) → преобразуем в str
        - Если указан type: integer, а пришло str (только цифры) → преобразуем в int
        - Если указан type: integer, а пришло float (целое) → преобразуем в int
        - Если указан type: float, а пришло int/str → преобразуем в float
        - Если указан type: boolean, а пришло 'true'/'false' → преобразуем в bool
        
        Union типы (string|integer) - НЕ обрабатываем, оставляем как есть
        None - пропускаем (не преобразуем)
        """
        for field_name, field_config in schema.items():
            if field_name not in data:
                continue
            
            value = data[field_name]
            
            # Пропускаем None
            if value is None:
                continue
            
            type_str = field_config.get('type', 'string')
            
            # Пропускаем Union типы - их не трогаем
            if isinstance(type_str, str) and '|' in type_str:
                continue
            
            # Обрабатываем только простые типы
            target_type = type_str.lower().strip() if isinstance(type_str, str) else None
            
            if not target_type:
                continue
            
            # Преобразуем только если тип значения не совпадает с целевым
            try:
                if target_type == 'string':
                    # Если указан string, а пришло что-то другое (кроме None) - преобразуем в строку
                    if not isinstance(value, str):
                        # Преобразуем любые типы в строку (int, float, bool и т.д.)
                        # None пропускаем (уже обработано выше)
                        data[field_name] = str(value)
                
                elif target_type == 'integer':
                    # Если указан integer, а пришло что-то другое - пытаемся преобразовать
                    if isinstance(value, float):
                        # Проверяем, целое ли число
                        if value == int(value):
                            data[field_name] = int(value)
                    elif isinstance(value, str):
                        # Пробуем преобразовать строку в int (если состоит из цифр)
                        if value.strip().lstrip('-+').isdigit():
                            data[field_name] = int(value)
                    # Если уже int - оставляем как есть
                
                elif target_type == 'float':
                    # Если указан float, а пришло int или str - преобразуем
                    if isinstance(value, (int, str)):
                        try:
                            data[field_name] = float(value)
                        except (ValueError, TypeError):
                            # Не удалось преобразовать - оставляем как есть
                            pass
                    # Если уже float - оставляем как есть
                
                elif target_type == 'boolean':
                    # Если указан boolean, а пришло строка - проверяем явные значения
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower == 'true':
                            data[field_name] = True
                        elif value_lower == 'false':
                            data[field_name] = False
                        # Иначе оставляем как есть (Pydantic проверит)
                    # Если уже bool - оставляем как есть
                        
            except (ValueError, TypeError, OverflowError):
                # Не удалось преобразовать - оставляем как есть, Pydantic выдаст ошибку валидации
                pass
    
    def _parse_type_string(self, type_str: Any, field_config: Dict[str, Any]):
        """
        Парсинг типа из схемы с поддержкой union типов (string|None, integer|array|None)
        и вложенных объектов в массивах (items.properties)
        """
        if not type_str:
            return str
        
        # Если это строка с | - это union тип
        if isinstance(type_str, str) and '|' in type_str:
            type_parts = [part.strip() for part in type_str.split('|')]
            python_types = []
            
            for part in type_parts:
                if part.lower() == 'none':
                    # None уже будет обработан через Optional
                    continue
                python_type = self._get_pydantic_type(part)
                python_types.append(python_type)
            
            # Если есть None в union - добавляем в типы
            has_none = 'none' in [p.strip().lower() for p in type_str.split('|')]
            
            if len(python_types) == 1:
                # Простой случай: string|None -> Optional[str]
                if has_none:
                    return Optional[python_types[0]]
                return python_types[0]
            elif len(python_types) > 1:
                # Множественный union: integer|array|None -> Union[int, list, None]
                if has_none:
                    # Добавляем None в union
                    python_types.append(type(None))
                return Union[tuple(python_types)]
            else:
                # Только None - возвращаем None
                return type(None)
        
        # Если это массив с items - проверяем вложенные объекты
        if isinstance(type_str, str) and type_str.lower() in ('array', 'list'):
            items_config = field_config.get('items', {})
            if isinstance(items_config, dict) and 'properties' in items_config:
                # Вложенный объект в массиве - создаем модель для items
                items_schema = items_config.get('properties', {})
                if items_schema:
                    # Создаем модель для элемента массива
                    item_model = self._create_pydantic_model(items_schema, f'ItemModel_{id(items_schema)}')
                    if item_model:
                        return List[item_model]
            # Обычный массив без вложенных объектов
            return list
        
        # Обычный тип
        return self._get_pydantic_type(type_str)
    
    def _get_pydantic_type(self, type_str: str):
        """
        Преобразование простого типа из схемы в Pydantic тип
        """
        type_mapping = {
            'string': str,
            'integer': int,
            'float': float,
            'number': float,
            'boolean': bool,
            'bool': bool,
            'object': dict,
            'dict': dict,
            'array': list,
            'list': list,
            'any': Any,
        }
        return type_mapping.get(type_str.lower() if type_str else 'string', str)
    
    def invalidate_cache(self, service_name: Optional[str] = None, action_name: Optional[str] = None):
        """
        Инвалидация кэша моделей валидации
        """
        if service_name and action_name:
            # Инвалидируем конкретную модель
            cache_key = f"{service_name}.{action_name}"
            if cache_key in self._validation_models:
                del self._validation_models[cache_key]
                self.logger.info(f"Кэш модели {cache_key} очищен")
        else:
            # Очищаем весь кэш
            count = len(self._validation_models)
            self._validation_models.clear()
            self.logger.info(f"Весь кэш моделей очищен (удалено {count} моделей)")

