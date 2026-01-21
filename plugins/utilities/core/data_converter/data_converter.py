import json
from typing import Any, Dict, List, Optional, Union


class DataConverter:
    """
    Universal converter of objects to dictionaries with ORM and JSON support.
    Combines functionality of ORM object conversion and universal conversion.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        
        # Get settings through settings_manager
        settings = self.settings_manager.get_plugin_settings("data_converter")
        
        # Settings for ORM conversion
        self.auto_detect_json = settings.get('auto_detect_json', True)
        self.strict_json_validation = settings.get('strict_json_validation', False)
        
        # Settings for universal conversion
        self.enable_cyclic_reference_detection = settings.get('enable_cyclic_reference_detection', True)
        self.max_recursion_depth = settings.get('max_recursion_depth', 100)
        self.safe_mode = settings.get('safe_mode', True)
        
        # For preventing cyclic references
        self._processed_objects = set()
    
    # === ORM Conversion ===
    
    def is_json_field(self, value) -> bool:
        """Checks if value is a JSON string"""
        # Check for None and empty string safely (avoid errors with numpy arrays)
        if value is None:
            return False
        if not isinstance(value, str):
            return False
        if not value:  # Empty string
            return False
        
        try:
            import json
            json.loads(value)
            return True
        except Exception:
            return False
    
    async def to_dict(self, orm_object, json_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Converts ORM object to dictionary with automatic JSON decoding
        """
        if not orm_object:
            return {}
        
        # Get all fields from ORM object
        item = {c.name: getattr(orm_object, c.name) for c in orm_object.__table__.columns}
        
        # Decode JSON fields and restore bytes
        for field_name, field_value in item.items():
            should_decode = False
            
            # If field list specified - check it
            if json_fields and field_name in json_fields:
                should_decode = self.is_json_field(field_value)
            # Otherwise auto-detect JSON (if enabled)
            elif self.auto_detect_json and not json_fields:
                should_decode = self.is_json_field(field_value)
            
            if should_decode:
                try:
                    import json
                    decoded_value = json.loads(field_value)
                    # Apply recursive bytes processing to decoded value
                    item[field_name] = self._restore_bytes_recursive(decoded_value)
                except Exception as e:
                    error_msg = f"Error decoding JSON for field {field_name}: {e}"
                    if self.strict_json_validation:
                        self.logger.error(error_msg)
                        return None
                    else:
                        self.logger.warning(error_msg)
            
            # Restore bytes from hex string (for non-JSON fields)
            if isinstance(field_value, str) and field_value.startswith("bytes:"):
                try:
                    hex_data = field_value[6:]  # remove "bytes:"
                    restored_bytes = bytes.fromhex(hex_data)
                    item[field_name] = restored_bytes
                except Exception as e:
                    self.logger.warning(f"Error restoring bytes for field {field_name}: {e}")
                    # Leave as is if failed to restore
        
        return item
    
    def _restore_bytes_recursive(self, data: Any) -> Any:
        """
        Optimized recursive function for restoring bytes from hex strings.
        Checks for bytes strings before recursion for maximum performance.
        """
        if isinstance(data, dict):
            # Check if there are bytes strings in dict before recursion
            has_bytes = self._has_bytes_strings(data)
            if not has_bytes:
                return data
            
            # Has bytes strings - process recursively
            return {k: self._restore_bytes_recursive(v) for k, v in data.items()}
            
        elif isinstance(data, list):
            # Check if there are bytes strings in list before recursion
            has_bytes = self._has_bytes_strings(data)
            if not has_bytes:
                return data
            
            # Has bytes strings - process recursively
            return [self._restore_bytes_recursive(item) for item in data]
            
        elif isinstance(data, str) and data.startswith('bytes:'):
            # Restore bytes from hex string
            try:
                hex_data = data[6:]  # remove "bytes:"
                restored_bytes = bytes.fromhex(hex_data)
                return restored_bytes
            except Exception as e:
                self.logger.warning(f"Error recursively restoring bytes: {e}")
                return data
        else:
            # Not a string or not a bytes string - return as is
            return data
    
    def _has_bytes_strings(self, data: Any) -> bool:
        """
        Checks if there are bytes strings in data structure.
        Used for optimization - avoid recursion if no bytes strings.
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
        """Converts list of ORM objects to list of dictionaries"""
        if not orm_objects:
            return []
        return [await self.to_dict(obj, json_fields) for obj in orm_objects]
    
    async def convert_string_to_type(self, value: Any) -> Union[str, int, float, bool, list, dict, None]:
        """
        Converts string value to Python type based on string content
        
        For Text columns tries to automatically determine type:
        - Arrays (JSON string starting with '[') - deserializes from JSON
        - Objects (JSON string starting with '{') - deserializes from JSON
        - Numbers (int, float) - converts to corresponding type
        - Boolean values ('true', 'false') - converts to bool
        - Everything else - leaves as string
        
        Async method for consistency with rest of project code.
        """
        if value is None:
            return None

        # If already not a string - return as is
        if not isinstance(value, str):
            return value

        # Try to deserialize JSON (array or object)
        value_stripped = value.strip()
        if value_stripped.startswith('[') or value_stripped.startswith('{'):
            try:
                parsed = json.loads(value_stripped)
                # Check that it's an array or dictionary
                if isinstance(parsed, (list, dict)):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # If failed to parse - continue
                pass

        # Try to convert to int
        try:
            # Check that it's a whole number (no dot)
            if '.' not in value_stripped and value_stripped.lstrip('-+').isdigit():
                return int(value_stripped)
        except (ValueError, AttributeError):
            pass

        # Try to convert to float
        try:
            float_value = float(value_stripped)
            # If it was a number with dot or scientific notation - return float
            if '.' in value_stripped or 'e' in value_stripped.lower() or 'E' in value_stripped:
                return float_value
        except (ValueError, AttributeError):
            pass

        # Try to convert to bool (only strings 'true' and 'false')
        value_lower = value_stripped.lower()
        if value_lower == 'true':
            return True
        if value_lower == 'false':
            return False

        # Return as string
        return value
    
    # === Universal Conversion ===
    
    async def to_safe_dict(self, obj: Any) -> Union[Dict[str, Any], List[Any], Any]:
        """Converts object to safe dictionary/list/value."""
        self._processed_objects.clear()  # Reset for new call
        return await self._to_safe_value(obj)
    
    async def _to_safe_value(self, value: Any, depth: int = 0) -> Any:
        """Recursively converts value to safe type."""
        # Protection against wrong depth type
        if not isinstance(depth, int):
            self.logger.warning(f"depth received as {type(depth).__name__}: {depth}, using 0")
            depth = 0
        
        # Check recursion depth
        if depth > self.max_recursion_depth:
            return f"<max_recursion_depth_{type(value).__name__}>"
        
        # Check for cyclic references
        if self.enable_cyclic_reference_detection and id(value) in self._processed_objects:
            return f"<cyclic_reference_{type(value).__name__}>"
        
        # Handle None
        if value is None:
            return None
        
        # Handle simple types
        if isinstance(value, (str, int, float, bool)):
            return value
        
        # Handle bytes - convert to hex string
        if isinstance(value, bytes):
            hex_result = f"bytes:{value.hex()}"
            return hex_result
        
        # Handle datetime
        import datetime
        if isinstance(value, datetime.datetime):
            return await self.datetime_formatter.to_iso_string(value)
        
        # Handle date
        if isinstance(value, datetime.date):
            return value.isoformat()
        
        # Handle time
        if isinstance(value, datetime.time):
            return value.isoformat()
        
        # Handle dictionaries
        if isinstance(value, dict):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                return {k: await self._to_safe_value(v, depth + 1) for k, v in value.items()}
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Handle lists and tuples
        if isinstance(value, (list, tuple)):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                return [await self._to_safe_value(item, depth + 1) for item in value]
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # Handle sets
        if isinstance(value, set):
            return [await self._to_safe_value(item, depth + 1) for item in value]
        
        # Handle objects with attributes (e.g., Telegram objects)
        if hasattr(value, '__dict__'):
            if self.enable_cyclic_reference_detection:
                self._processed_objects.add(id(value))
            try:
                # Try to get object attributes
                attrs = {}
                for attr_name in dir(value):
                    # Skip private attributes
                    if attr_name.startswith('_'):
                        continue
                    
                    try:
                        attr_value = getattr(value, attr_name)
                        # Skip methods
                        if not callable(attr_value):
                            attrs[attr_name] = await self._to_safe_value(attr_value, depth + 1)
                    except Exception:
                        if not self.safe_mode:
                            raise
                        # If failed to get attribute, skip
                        continue
                
                return attrs
            finally:
                if self.enable_cyclic_reference_detection:
                    self._processed_objects.discard(id(value))
        
        # For other types use string representation
        try:
            return str(value)
        except Exception:
            if not self.safe_mode:
                raise
            return f"<non_serializable_object_{type(value).__name__}>" 