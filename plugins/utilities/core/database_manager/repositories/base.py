"""
Base repository with common methods
"""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union


class BaseRepository:
    """
    Base repository with common methods
    """
    
    def __init__(self, session_factory, **kwargs):
        self.session_factory = session_factory
        self.logger = kwargs['logger']
        self.data_converter = kwargs['data_converter']
        self.data_preparer = kwargs['data_preparer']
    
    async def _to_dict(self, obj: Any, json_fields: Optional[List[str]] = None, convert_text_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Convert model object to dictionary using data_converter
        Returns None on conversion error
        """
        try:
            if obj is None:
                return None
            
            result = await self.data_converter.to_dict(obj, json_fields=json_fields)
            
            # Convert specified Text fields to types
            if convert_text_fields:
                for field_name in convert_text_fields:
                    if field_name in result:
                        result[field_name] = await self._convert_value_from_db(result[field_name])
            
            return result
        except Exception as e:
            self.logger.error(f"Error converting object to dictionary: {e}")
            return None
    
    async def _to_dict_list(self, objects: List[Any], json_fields: Optional[List[str]] = None, convert_text_fields: Optional[List[str]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Convert list of objects to list of dictionaries using data_converter
        Returns None on conversion error
        """
        try:
            if objects is None:
                return None
            
            result = await self.data_converter.to_dict_list(objects, json_fields=json_fields)
            
            # Convert specified Text fields to types
            if convert_text_fields:
                for record in result:
                    for field_name in convert_text_fields:
                        if field_name in record:
                            record[field_name] = await self._convert_value_from_db(record[field_name])
            
            return result
        except Exception as e:
            self.logger.error(f"Error converting list of objects to dictionaries: {e}")
            return None
    
    async def _convert_value_from_db(self, value: Any, column_type: Optional[Any] = None) -> Union[str, int, float, bool, list, None]:
        """
        Converts value from DB to Python type based on string content
        Uses data_converter for type conversion.
        
        Conversion rules:
        - Arrays (JSON string starting with '[') - deserializes from JSON
        - Numbers (int, float) - converts to corresponding type
        - Boolean values ('true', 'false') - converts to bool
        - Everything else - leaves as string
        
        """
        return await self.data_converter.convert_string_to_type(value)
    
    @contextmanager
    def _get_session(self):
        """
        Context manager for getting DB session
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