import json
from typing import Any, Dict, List, Optional, Union


class DataConverter:
    """
    Универсальный конвертер объектов в словари с поддержкой ORM и JSON.
    Объединяет функциональность конвертации ORM объектов и универсальной конвертации.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("data_converter")
        
        # Настройки для ORM конвертации
        self.auto_detect_json = settings.get('auto_detect_json', True)
        self.strict_json_validation = settings.get('strict_json_validation', False)
        
        # Настройки для универсальной конвертации
        self.enable_cyclic_reference_detection = settings.get('enable_cyclic_reference_detection', True)
        self.max_recursion_depth = settings.get('max_recursion_depth', 100)
        self.safe_mode = settings.get('safe_mode', True)
        
        # Для предотвращения циклических ссылок
        self._processed_objects = set()
    
    # === ORM Конвертация ===
    
    def is_json_field(self, value) -> bool:
        """Проверяет, является ли значение JSON-строкой"""
        # Проверяем на None и пустую строку безопасно (избегаем ошибок с numpy arrays)
        if value is None:
            return False
        if not isinstance(value, str):
            return False
        if not value:  # Пустая строка
            return False
        
        try:
            import json
            json.loads(value)
            return True
        except Exception:
            return False
    
    async def to_dict(self, orm_object, json_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Конвертирует ORM объект в словарь с автоматическим декодированием JSON
        """
        if not orm_object:
            return {}
        
        # Получаем все поля из ORM объекта
        item = {c.name: getattr(orm_object, c.name) for c in orm_object.__table__.columns}
        
        # Декодируем JSON поля и восстанавливаем bytes
        for field_name, field_value in item.items():
            should_decode = False
            
            # Если указан список полей - проверяем его
            if json_fields and field_name in json_fields:
                should_decode = self.is_json_field(field_value)
            # Иначе автоопределяем JSON (если включено)
            elif self.auto_detect_json and not json_fields:
                should_decode = self.is_json_field(field_value)
            
            if should_decode:
                try:
                    import json
                    decoded_value = json.loads(field_value)
                    # Применяем рекурсивную обработку bytes к декодированному значению
                    item[field_name] = self._restore_bytes_recursive(decoded_value)
                except Exception as e:
                    error_msg = f"Ошибка декодирования JSON для поля {field_name}: {e}"
                    if self.strict_json_validation:
                        self.logger.error(error_msg)
                        return None
                    else:
                        self.logger.warning(error_msg)
            
            # Восстанавливаем bytes из hex строки (для не-JSON полей)
            if isinstance(field_value, str) and field_value.startswith("bytes:"):
                try:
                    hex_data = field_value[6:]  # убираем "bytes:"
                    restored_bytes = bytes.fromhex(hex_data)
                    item[field_name] = restored_bytes
                except Exception as e:
                    self.logger.warning(f"Ошибка восстановления bytes для поля {field_name}: {e}")
                    # Оставляем как есть, если не удалось восстановить
        
        return item
    
    def _restore_bytes_recursive(self, data: Any) -> Any:
        """
        Оптимизированная рекурсивная функция для восстановления bytes из hex строк.
        Проверяет наличие bytes строк перед рекурсией для максимальной производительности.
        """
        if isinstance(data, dict):
            # Проверяем есть ли bytes строки в словаре перед рекурсией
            has_bytes = self._has_bytes_strings(data)
            if not has_bytes:
                return data
            
            # Есть bytes строки - обрабатываем рекурсивно
            return {k: self._restore_bytes_recursive(v) for k, v in data.items()}
            
        elif isinstance(data, list):
            # Проверяем есть ли bytes строки в списке перед рекурсией
            has_bytes = self._has_bytes_strings(data)
            if not has_bytes:
                return data
            
            # Есть bytes строки - обрабатываем рекурсивно
            return [self._restore_bytes_recursive(item) for item in data]
            
        elif isinstance(data, str) and data.startswith('bytes:'):
            # Восстанавливаем bytes из hex строки
            try:
                hex_data = data[6:]  # убираем "bytes:"
                restored_bytes = bytes.fromhex(hex_data)
                return restored_bytes
            except Exception as e:
                self.logger.warning(f"Ошибка рекурсивного восстановления bytes: {e}")
                return data
        else:
            # Не строка или не bytes строка - возвращаем как есть
            return data
    
    def _has_bytes_strings(self, data: Any) -> bool:
        """
        Проверяет есть ли bytes строки в структуре данных.
        Используется для оптимизации - избегаем рекурсии если bytes строк нет.
        """
        if isinstance(data, dict):
            return any(self._has_bytes_strings(v) for v in data.values())
        elif isinstance(data, list):
            return any(self._has_bytes_strings(item) for item in data)
        elif isinstance(data, str) and data.startswith('bytes:'):
            return True
        else:
            return False
    
    async def to_dict_list(self, orm_objects: List, json_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Конвертирует список ORM объектов в список словарей"""
        if not orm_objects:
            return []
        return [await self.to_dict(obj, json_fields) for obj in orm_objects]
    
    async def convert_string_to_type(self, value: Any) -> Union[str, int, float, bool, list, dict, None]:
        """
        Преобразует строковое значение в Python тип на основе содержимого строки
        
        Для Text колонок пытается автоматически определить тип:
        - Массивы (JSON строка, начинающаяся с '[') - десериализует из JSON
        - Объекты (JSON строка, начинающаяся с '{') - десериализует из JSON
        - Числа (int, float) - преобразует в соответствующий тип
        - Булевы значения ('true', 'false') - преобразует в bool
        - Остальное - оставляет как строку
        
        Асинхронный метод для консистентности с остальным кодом проекта.
        """
        if value is None:
            return None

        # Если уже не строка - возвращаем как есть
        if not isinstance(value, str):
            return value

        # Пробуем десериализовать JSON (массив или объект)
        value_stripped = value.strip()
        if value_stripped.startswith('[') or value_stripped.startswith('{'):
            try:
                parsed = json.loads(value_stripped)
                # Проверяем что это массив или словарь
                if isinstance(parsed, (list, dict)):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # Если не удалось распарсить - продолжаем дальше
                pass

        # Пробуем преобразовать в int
        try:
            # Проверяем, что это целое число (без точки)
            if '.' not in value_stripped and value_stripped.lstrip('-+').isdigit():
                return int(value_stripped)
        except (ValueError, AttributeError):
            pass

        # Пробуем преобразовать в float
        try:
            float_value = float(value_stripped)
            # Если это было число с точкой или научная нотация - возвращаем float
            if '.' in value_stripped or 'e' in value_stripped.lower() or 'E' in value_stripped:
                return float_value
        except (ValueError, AttributeError):
            pass

        # Пробуем преобразовать в bool (только строки 'true' и 'false')
        value_lower = value_stripped.lower()
        if value_lower == 'true':
            return True
        if value_lower == 'false':
            return False

        # Возвращаем как строку
        return value
    
    # === Универсальная конвертация ===
    
    async def to_safe_dict(self, obj: Any) -> Union[Dict[str, Any], List[Any], Any]:
        """Конвертирует объект в безопасный словарь/список/значение."""
        self._processed_objects.clear()  # Сбрасываем для нового вызова
        return await self._to_safe_value(obj)
    
    async def _to_safe_value(self, value: Any, depth: int = 0) -> Any:
        """Рекурсивно конвертирует значение в безопасный тип."""
        # Защита от неправильного типа depth
        if not isinstance(depth, int):
            self.logger.warning(f"depth получен как {type(depth).__name__}: {depth}, используем 0")
            depth = 0
        
        # Проверяем глубину рекурсии
        if depth > self.max_recursion_depth:
            return f"<максимальная_глубина_рекурсии_{type(value).__name__}>"
        
        # Проверяем на циклические ссылки
        if self.enable_cyclic_reference_detection and id(value) in self._processed_objects:
            return f"<циклическая_ссылка_{type(value).__name__}>"
        
        # Обрабатываем None
        if value is None:
            return None
        
        # Обрабатываем простые типы
        if isinstance(value, (str, int, float, bool)):
            return value
        
        # Обрабатываем bytes - конвертируем в hex строку
        if isinstance(value, bytes):
            hex_result = f"bytes:{value.hex()}"
            return hex_result
        
        # Обрабатываем datetime
        import datetime
        if isinstance(value, datetime.datetime):
            return await self.datetime_formatter.to_iso_string(value)
        
        # Обрабатываем date
        if isinstance(value, datetime.date):
            return value.isoformat()
        
        # Обрабатываем time
        if isinstance(value, datetime.time):
            return value.isoformat()
        
        # Обрабатываем словари
        if isinstance(value, dict):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                return {k: await self._to_safe_value(v, depth + 1) for k, v in value.items()}
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Обрабатываем списки и кортежи
        if isinstance(value, (list, tuple)):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                return [await self._to_safe_value(item, depth + 1) for item in value]
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Обрабатываем множества
        if isinstance(value, set):
            return [await self._to_safe_value(item, depth + 1) for item in value]
        
        # Обрабатываем объекты с атрибутами (например, Telegram объекты)
        if hasattr(value, '__dict__'):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                # Пытаемся получить атрибуты объекта
                attrs = {}
                for attr_name in dir(value):
                    # Пропускаем служебные атрибуты
                    if attr_name.startswith('_'):
                        continue
                    
                    try:
                        attr_value = getattr(value, attr_name)
                        # Пропускаем методы
                        if not callable(attr_value):
                            attrs[attr_name] = await self._to_safe_value(attr_value, depth + 1)
                    except Exception:
                        if not self.safe_mode:
                            raise
                        # Если не удается получить атрибут, пропускаем
                        continue
                
                return attrs
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Для остальных типов используем строковое представление
        try:
            return str(value)
        except Exception:
            if not self.safe_mode:
                raise
            return f"<несериализуемый_объект_{type(value).__name__}>" 