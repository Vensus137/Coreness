import datetime
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
        if not value or not isinstance(value, str):
            return False
        
        try:
            json.loads(value)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
    
    def to_dict(self, orm_object, json_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Конвертирует ORM объект в словарь с автоматическим декодированием JSON
        
        Args:
            orm_object: SQLAlchemy ORM объект
            json_fields: Список полей для принудительного декодирования (опционально)
        """
        if not orm_object:
            return {}
        
        # Получаем все поля из ORM объекта
        item = {c.name: getattr(orm_object, c.name) for c in orm_object.__table__.columns}
        
        # Декодируем JSON поля
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
                    decoded_value = json.loads(field_value)
                    item[field_name] = decoded_value
                except Exception as e:
                    error_msg = f"Ошибка декодирования JSON для поля {field_name}: {e}"
                    if self.strict_json_validation:
                        self.logger.error(error_msg)
                        raise ValueError(error_msg)
                    else:
                        self.logger.warning(error_msg)
        
        return item
    
    def to_dict_list(self, orm_objects: List, json_fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Конвертирует список ORM объектов в список словарей"""
        return [self.to_dict(obj, json_fields) for obj in orm_objects]
    
    # === Универсальная конвертация ===
    
    def to_safe_dict(self, obj: Any) -> Union[Dict[str, Any], List[Any], Any]:
        """Конвертирует объект в безопасный словарь/список/значение."""
        self._processed_objects.clear()  # Сбрасываем для нового вызова
        return self._to_safe_value(obj)
    
    def _to_safe_value(self, value: Any, depth: int = 0) -> Any:
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
        
        # Обрабатываем datetime
        if isinstance(value, datetime.datetime):
            return self.datetime_formatter.to_iso_string(value)
        
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
                return {k: self._to_safe_value(v, depth + 1) for k, v in value.items()}
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Обрабатываем списки и кортежи
        if isinstance(value, (list, tuple)):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                return [self._to_safe_value(item, depth + 1) for item in value]
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Обрабатываем множества
        if isinstance(value, set):
            return [self._to_safe_value(item, depth + 1) for item in value]
        
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
                            attrs[attr_name] = self._to_safe_value(attr_value, depth + 1)
                    except Exception as e:
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
        except Exception as e:
            if not self.safe_mode:
                raise
            return f"<несериализуемый_объект_{type(value).__name__}>" 