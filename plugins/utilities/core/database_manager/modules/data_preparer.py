import json
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, TIMESTAMP, BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeMeta


class DataPreparer:
    """
    Data preparer for working with SQLAlchemy models.
    Automatically converts data to required types based on table schema.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.datetime_formatter = kwargs['datetime_formatter']
        self._model_fields_cache = {}  # Model fields cache
    
    def _get_model_fields(self, model: DeclarativeMeta) -> set:
        """Gets list of model fields with caching."""
        model_name = model.__name__
        if model_name not in self._model_fields_cache:
            self._model_fields_cache[model_name] = set(model.__table__.columns.keys())
        return self._model_fields_cache[model_name]
    
    async def prepare_for_update(self, model: DeclarativeMeta, fields: Dict[str, Any],
                          json_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Prepares fields for updating record with automatic addition of service fields."""
        # Get list of model fields
        model_fields = self._get_model_fields(model)
        
        # Determine service fields that exist in model
        service_fields = []
        if 'updated_at' in model_fields:
            service_fields.append('updated_at')
        if 'processed_at' in model_fields:
            service_fields.append('processed_at')
        
        # Exclude only service fields (allow None values for nullable fields)
        user_fields = {k: v for k, v in fields.items() if k not in service_fields}
        if not user_fields:
            return None  # No fields to update
        
        # Add service fields if they don't exist
        all_fields = user_fields.copy()  # Use all fields (including None for nullable fields)
        for service_field in service_fields:
            if service_field not in all_fields:
                all_fields[service_field] = await self.datetime_formatter.now_local()
        
        # Prepare fields with is_update=True flag
        return await self.prepare_fields(model, all_fields, json_fields=json_fields, is_update=True)
    
    async def prepare_for_insert(self, model: DeclarativeMeta, fields: Dict[str, Any],
                          json_fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Prepares fields for creating new record with automatic addition of service fields."""
        # Check if there are fields for creation
        if not fields:
            return None
        
        # Get list of model fields
        model_fields = self._get_model_fields(model)
        
        # Determine service fields that exist in model
        service_fields = []
        if 'created_at' in model_fields:
            service_fields.append('created_at')
        if 'updated_at' in model_fields:
            service_fields.append('updated_at')
        if 'processed_at' in model_fields:
            service_fields.append('processed_at')
        
        # Add service fields if they don't exist
        all_fields = fields.copy()
        for service_field in service_fields:
            if service_field not in all_fields:
                all_fields[service_field] = await self.datetime_formatter.now_local()
        
        # Prepare fields with is_update=False flag
        return await self.prepare_fields(model, all_fields, json_fields=json_fields, is_update=False)
    
    async def prepare_fields(self, model: DeclarativeMeta, fields: Dict[str, Any], 
                      json_fields: Optional[List[str]] = None, is_update: bool = False) -> Optional[Dict[str, Any]]:
        """Prepares fields for creating/updating record."""
        try:
            # Get allowed fields from model
            allowed_fields = self._get_model_fields(model)
            
            # 🚀 EXCLUDE PRIMARY KEY on update
            pk_columns = set()
            if is_update:
                pk_columns = {col.name for col in model.__table__.primary_key.columns}
                allowed_fields = allowed_fields - pk_columns
            
            # Filter fields
            result = {k: v for k, v in fields.items() if k in allowed_fields}
            ignored_fields = set(fields.keys()) - allowed_fields
            
            # Exclude PK columns from warning - they are specifically excluded on update
            if is_update:
                ignored_fields = ignored_fields - pk_columns
            
            if ignored_fields:
                self.logger.warning(f"Ignoring non-existent fields: {ignored_fields}")
            
            if not result:
                self.logger.warning("No valid fields to process")
                return None
            
            # Convert fields to required types
            result = await self._convert_field_types(model, result, json_fields)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error preparing fields: {e}")
            return None
    
    async def _convert_field_types(self, model: DeclarativeMeta, fields: Dict[str, Any], 
                           json_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Converts fields to required types based on table schema."""
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
                self.logger.error(f"Error converting field {field_name}: {e}")
                result[field_name] = value  # Keep original value
        
        return result
    
    async def _convert_single_field(self, column: Column, value: Any, field_name: str, 
                            json_fields: Optional[List[str]] = None) -> Any:
        """Converts single field to required type."""
        # Determine column type
        column_type = type(column.type)
        
        # JSON fields
        if json_fields and field_name in json_fields:
            # For JSONB columns SQLAlchemy expects Python dict/list, not JSON string
            if column_type == JSONB:
                if isinstance(value, str):
                    # If value is string, try to parse into dict/list
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Field {field_name} contains invalid JSON: {value[:100]}...")
                        return value
                else:
                    # If value already dict/list - return as is
                    return value
            else:
                # For regular JSON columns (not JSONB) serialize to string
                if not isinstance(value, str):
                    result = json.dumps(value, ensure_ascii=False, default=str)
                    return result
                else:
                    # If value already string, check that it's valid JSON
                    try:
                        json.loads(value)  # Check validity
                        return value  # Return as is
                    except json.JSONDecodeError:
                        self.logger.warning(f"Field {field_name} contains invalid JSON: {value[:100]}...")
                        return value
        
        # String types
        if column_type in (String, Text, JSON, JSONB):
            # For Text columns: if value is array or dictionary, serialize to JSON string
            if column_type == Text and isinstance(value, (list, dict)):
                return json.dumps(value, ensure_ascii=False, default=str)
            return str(value) if value is not None else None
        
        # Integer types
        elif column_type in (Integer, BigInteger):
            return int(value) if value is not None else None
        
        # Boolean types
        elif column_type == Boolean:
            if value is None:
                return None
            if isinstance(value, str):
                # Convert only strings 'true' and 'false' to boolean values
                value_lower = value.lower().strip()
                if value_lower == 'true':
                    return True
                if value_lower == 'false':
                    return False
                # For other strings use explicit conversion
                return bool(value)
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return bool(value)
            # For other types use explicit conversion
            return bool(value)
        
        # Date/time
        elif column_type in (DateTime, TIMESTAMP):
            if isinstance(value, str):
                try:
                    return await self.datetime_formatter.parse(value)
                except Exception:
                    return await self.datetime_formatter.now_local()
            return value
        
        # For other types return as is
        return value
