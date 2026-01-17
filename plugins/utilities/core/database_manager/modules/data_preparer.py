import json
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, TIMESTAMP, BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeMeta


class DataPreparer:
    """
    Подготовщик данных для работы с SQLAlchemy моделями.
    Автоматически приводит данные к нужным типам на основе схемы таблицы.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.datetime_formatter = kwargs['datetime_formatter']
        self._model_fields_cache = {}  # Кэш полей моделей
    
    def _get_model_fields(self, model: DeclarativeMeta) -> set:
        """Получает список полей модели с кэшированием."""
        model_name = model.__name__
        if model_name not in self._model_fields_cache:
            self._model_fields_cache[model_name] = set(model.__table__.columns.keys())
        return self._model_fields_cache[model_name]
    
    async def prepare_for_update(self, model: DeclarativeMeta, fields: Dict[str, Any],
                          json_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Подготавливает поля для обновления записи с автоматическим добавлением служебных полей."""
        # Получаем список полей модели
        model_fields = self._get_model_fields(model)
        
        # Определяем служебные поля, которые есть в модели
        service_fields = []
        if 'updated_at' in model_fields:
            service_fields.append('updated_at')
        if 'processed_at' in model_fields:
            service_fields.append('processed_at')
        
        # Исключаем только служебные поля (разрешаем None значения для nullable полей)
        user_fields = {k: v for k, v in fields.items() if k not in service_fields}
        if not user_fields:
            return None  # Нет полей для обновления
        
        # Добавляем служебные поля если их нет
        all_fields = user_fields.copy()  # Используем все поля (включая None для nullable полей)
        for service_field in service_fields:
            if service_field not in all_fields:
                all_fields[service_field] = await self.datetime_formatter.now_local()
        
        # Подготавливаем поля с флагом is_update=True
        return await self.prepare_fields(model, all_fields, json_fields=json_fields, is_update=True)
    
    async def prepare_for_insert(self, model: DeclarativeMeta, fields: Dict[str, Any],
                          json_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Подготавливает поля для создания новой записи с автоматическим добавлением служебных полей."""
        # Проверяем, есть ли поля для создания
        if not fields:
            return None
        
        # Получаем список полей модели
        model_fields = self._get_model_fields(model)
        
        # Определяем служебные поля, которые есть в модели
        service_fields = []
        if 'created_at' in model_fields:
            service_fields.append('created_at')
        if 'updated_at' in model_fields:
            service_fields.append('updated_at')
        if 'processed_at' in model_fields:
            service_fields.append('processed_at')
        
        # Добавляем служебные поля если их нет
        all_fields = fields.copy()
        for service_field in service_fields:
            if service_field not in all_fields:
                all_fields[service_field] = await self.datetime_formatter.now_local()
        
        # Подготавливаем поля с флагом is_update=False
        return await self.prepare_fields(model, all_fields, json_fields=json_fields, is_update=False)
    
    async def prepare_fields(self, model: DeclarativeMeta, fields: Dict[str, Any], 
                      json_fields: Optional[List[str]] = None, is_update: bool = False) -> Optional[Dict[str, Any]]:
        """Подготавливает поля для создания/обновления записи."""
        try:
            # Получаем разрешенные поля из модели
            allowed_fields = self._get_model_fields(model)
            
            # 🚀 ИСКЛЮЧАЕМ PRIMARY KEY при обновлении
            pk_columns = set()
            if is_update:
                pk_columns = {col.name for col in model.__table__.primary_key.columns}
                allowed_fields = allowed_fields - pk_columns
            
            # Фильтруем поля
            result = {k: v for k, v in fields.items() if k in allowed_fields}
            ignored_fields = set(fields.keys()) - allowed_fields
            
            # Исключаем PK колонки из предупреждения - они специально исключены при обновлении
            if is_update:
                ignored_fields = ignored_fields - pk_columns
            
            if ignored_fields:
                self.logger.warning(f"Игнорируются несуществующие поля: {ignored_fields}")
            
            if not result:
                self.logger.warning("Нет валидных полей для обработки")
                return None
            
            # Приводим поля к нужным типам
            result = await self._convert_field_types(model, result, json_fields)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка подготовки полей: {e}")
            return None
    
    async def _convert_field_types(self, model: DeclarativeMeta, fields: Dict[str, Any], 
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
                converted_value = await self._convert_single_field(column, value, field_name, json_fields)
                result[field_name] = converted_value
            except Exception as e:
                self.logger.error(f"Ошибка конвертации поля {field_name}: {e}")
                result[field_name] = value  # Оставляем исходное значение
        
        return result
    
    async def _convert_single_field(self, column: Column, value: Any, field_name: str, 
                            json_fields: Optional[List[str]] = None) -> Any:
        """Конвертирует одно поле к нужному типу."""
        # Определяем тип колонки
        column_type = type(column.type)
        
        # JSON поля
        if json_fields and field_name in json_fields:
            # Для JSONB колонок SQLAlchemy ожидает Python dict/list, а не JSON строку
            if column_type == JSONB:
                if isinstance(value, str):
                    # Если значение - строка, пытаемся распарсить в dict/list
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Поле {field_name} содержит невалидный JSON: {value[:100]}...")
                        return value
                else:
                    # Если значение уже dict/list - возвращаем как есть
                    return value
            else:
                # Для обычных JSON колонок (не JSONB) сериализуем в строку
                if not isinstance(value, str):
                    result = json.dumps(value, ensure_ascii=False, default=str)
                    return result
                else:
                    # Если значение уже строка, проверяем что это валидный JSON
                    try:
                        json.loads(value)  # Проверяем валидность
                        return value  # Возвращаем как есть
                    except json.JSONDecodeError:
                        self.logger.warning(f"Поле {field_name} содержит невалидный JSON: {value[:100]}...")
                        return value
        
        # Строковые типы
        if column_type in (String, Text, JSON, JSONB):
            # Для Text колонок: если значение - массив или словарь, сериализуем в JSON строку
            if column_type == Text and isinstance(value, (list, dict)):
                return json.dumps(value, ensure_ascii=False, default=str)
            return str(value) if value is not None else None
        
        # Целочисленные типы
        elif column_type in (Integer, BigInteger):
            return int(value) if value is not None else None
        
        # Булевы типы
        elif column_type == Boolean:
            if value is None:
                return None
            if isinstance(value, str):
                # Преобразуем только строки 'true' и 'false' в булевы значения
                value_lower = value.lower().strip()
                if value_lower == 'true':
                    return True
                if value_lower == 'false':
                    return False
                # Для других строк используем явное приведение
                return bool(value)
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return bool(value)
            # Для других типов используем явное приведение
            return bool(value)
        
        # Дата/время
        elif column_type in (DateTime, TIMESTAMP):
            if isinstance(value, str):
                try:
                    return await self.datetime_formatter.parse(value)
                except Exception:
                    return await self.datetime_formatter.now_local()
            return value
        
        # Для остальных типов возвращаем как есть
        return value
