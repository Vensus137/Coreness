"""
Базовый репозиторий с общими методами
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union


class BaseRepository:
    """
    Базовый репозиторий с общими методами
    """
    
    def __init__(self, session_factory, **kwargs):
        self.session_factory = session_factory
        self.logger = kwargs['logger']
        self.data_converter = kwargs['data_converter']
        self.data_preparer = kwargs['data_preparer']
    
    async def _to_dict(self, obj: Any, json_fields: Optional[List[str]] = None, convert_text_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Преобразовать объект модели в словарь с использованием data_converter
        Возвращает None при ошибке преобразования
        """
        try:
            if obj is None:
                return None
            
            result = await self.data_converter.to_dict(obj, json_fields=json_fields)
            
            # Преобразуем указанные Text поля в типы
            if convert_text_fields:
                for field_name in convert_text_fields:
                    if field_name in result:
                        result[field_name] = await self._convert_value_from_db(result[field_name])
            
            return result
        except Exception as e:
            self.logger.error(f"Ошибка преобразования объекта в словарь: {e}")
            return None
    
    async def _to_dict_list(self, objects: List[Any], json_fields: Optional[List[str]] = None, convert_text_fields: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Преобразовать список объектов в список словарей с использованием data_converter
        Возвращает None при ошибке преобразования
        """
        try:
            if objects is None:
                return None
            
            result = await self.data_converter.to_dict_list(objects, json_fields=json_fields)
            
            # Преобразуем указанные Text поля в типы
            if convert_text_fields:
                for record in result:
                    for field_name in convert_text_fields:
                        if field_name in record:
                            record[field_name] = await self._convert_value_from_db(record[field_name])
            
            return result
        except Exception as e:
            self.logger.error(f"Ошибка преобразования списка объектов в словари: {e}")
            return None
    
    async def _convert_value_from_db(self, value: Any, column_type: Optional[Any] = None) -> Union[str, int, float, bool, list, None]:
        """
        Преобразует значение из БД в Python тип на основе содержимого строки
        Использует data_converter для преобразования типов.
        
        Правила преобразования:
        - Массивы (JSON строка, начинающаяся с '[') - десериализует из JSON
        - Числа (int, float) - преобразует в соответствующий тип
        - Булевы значения ('true', 'false') - преобразует в bool
        - Остальное - оставляет как строку
        
        """
        return await self.data_converter.convert_string_to_type(value)
    
    @contextmanager
    def _get_session(self):
        """
        Контекстный менеджер для получения сессии БД
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()