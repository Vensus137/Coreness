import json
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeMeta


class DataPreparer:
    """
    Подготовщик данных для работы с SQLAlchemy моделями.
    Автоматически приводит данные к нужным типам на основе схемы таблицы.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("data_preparer")
        
        self.auto_detect_json = settings.get('auto_detect_json', True)
        self.strict_json_validation = settings.get('strict_json_validation', False)
        self.strict_mode = settings.get('strict_mode', False)
    
    def prepare_fields(self, model: DeclarativeMeta, fields: Dict[str, Any], 
                      json_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Подготавливает поля для создания/обновления записи."""
        try:
            # Получаем разрешенные поля из модели
            allowed_fields = set(model.__table__.columns.keys())
            
            # Фильтруем поля
            result = {k: v for k, v in fields.items() if k in allowed_fields}
            ignored_fields = set(fields.keys()) - allowed_fields
            
            if ignored_fields:
                self.logger.warning(f"Игнорируются несуществующие поля: {ignored_fields}")
            
            if not result:
                self.logger.warning("Нет валидных полей для обработки")
                return None
            
            # Приводим поля к нужным типам
            result = self._convert_field_types(model, result, json_fields)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка подготовки полей: {e}")
            return None
    
    def _convert_field_types(self, model: DeclarativeMeta, fields: Dict[str, Any], 
                           json_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Приводит поля к нужным типам на основе схемы таблицы."""
        result = {}
        
        for field_name, value in fields.items():
            if value is None:
                result[field_name] = None
                continue
                
            column = model.__table__.columns.get(field_name)
            if column is None:
                continue
            
            try:
                converted_value = self._convert_single_field(column, value, field_name, json_fields)
                result[field_name] = converted_value
            except Exception as e:
                self.logger.error(f"Ошибка конвертации поля {field_name}: {e}")
                if self.strict_mode:
                    return None  # В строгом режиме возвращаем None при ошибке
                result[field_name] = value  # Оставляем исходное значение
        
        return result
    
    def _convert_single_field(self, column: Column, value: Any, field_name: str, 
                            json_fields: Optional[List[str]] = None) -> Any:
        """Конвертирует одно поле к нужному типу."""
        # JSON поля
        if json_fields and field_name in json_fields:
            if not isinstance(value, str):
                # Если значение не строка, сериализуем в JSON
                result = json.dumps(value, ensure_ascii=False)
                return result
            else:
                # Если значение уже строка, проверяем что это валидный JSON
                try:
                    json.loads(value)  # Проверяем валидность
                    return value  # Возвращаем как есть
                except json.JSONDecodeError:
                    # Если не валидный JSON, логируем предупреждение
                    self.logger.warning(f"Поле {field_name} содержит невалидный JSON: {value[:100]}...")
                    if self.strict_json_validation:
                        raise ValueError(f"Невалидный JSON в поле {field_name}")
                    return value  # Возвращаем как есть
        
        # Определяем тип колонки
        column_type = type(column.type)
        
        # Строковые типы
        if column_type in (String, Text):
            return str(value) if value is not None else None
        
        # Целочисленные типы
        elif column_type == Integer:
            return int(value) if value is not None else None
        
        # Булевы типы
        elif column_type == Boolean:
            if value is None:
                return None
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return bool(value)
            # Для других типов используем явное приведение
            return bool(value)
        
        # Дата/время
        elif column_type == DateTime:
            if isinstance(value, str):
                try:
                    return self.datetime_formatter.parse(value)
                except Exception:
                    return self.datetime_formatter.now_local()
            return value
        
        # Для остальных типов возвращаем как есть
        return value
    
    def prepare_for_update(self, model: DeclarativeMeta, fields: Dict[str, Any],
                          json_fields: Optional[List[str]] = None,
                          auto_timestamp_fields: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Подготавливает поля для обновления записи."""
        # Объединяем поля с автоматическими
        all_fields = fields.copy()
        if auto_timestamp_fields:
            for field, value in auto_timestamp_fields.items():
                if field not in all_fields:  # Не перезаписываем явно переданные значения
                    all_fields[field] = value
        
        # Подготавливаем поля
        return self.prepare_fields(model, all_fields, json_fields=json_fields)
    
    def prepare_for_insert(self, model: DeclarativeMeta, fields: Dict[str, Any],
                          json_fields: Optional[List[str]] = None,
                          auto_timestamp_fields: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Подготавливает поля для создания новой записи."""
        # Объединяем поля с автоматическими
        all_fields = fields.copy()
        if auto_timestamp_fields:
            for field, value in auto_timestamp_fields.items():
                if field not in all_fields:  # Не перезаписываем явно переданные значения
                    all_fields[field] = value
        
        # Подготавливаем поля
        return self.prepare_fields(model, all_fields, json_fields=json_fields) 