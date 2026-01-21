"""
Utility for validating action input data according to schemas from config.yaml
"""

from typing import Any, Dict, List, Literal, Optional, Union, get_args, get_origin

from pydantic import ConfigDict, Field, ValidationError, create_model


class ActionValidator:
    """
    Utility for validating action input data according to schemas from config.yaml
    
    Uses Pydantic for data validation based on schemas described in service config.yaml files.
    Caches created Pydantic models for performance.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Pydantic models cache (key: "service_name.action_name")
        self._validation_models: Dict[str, Any] = {}
    
    def validate_action_input(self, service_name: str, action_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate action input data according to schema from config.yaml
        """
        try:
            # Get schema from config.yaml (already cached in PluginsManager)
            input_schema = self._get_input_schema(service_name, action_name)
            
            if not input_schema:
                # No schema - skip validation, return original data
                return {
                    "result": "success",
                    "validated_data": data
                }
            
            # Get or create Pydantic model
            model = self._get_or_create_model(service_name, action_name, input_schema)
            
            if not model:
                # Failed to create model - skip, return original data
                return {
                    "result": "success",
                    "validated_data": data
                }
            
            # Data preprocessing: extract values from _config for fields with from_config
            processed_data = self._extract_from_config(data, input_schema)
            
            # Data preprocessing: for optional parameters convert empty strings to None
            # if parameter type is not string (e.g., array, integer, etc.)
            processed_data = self._preprocess_data(processed_data, input_schema)
            
            # Type coercion to target type (modify data "on the fly")
            # This ensures that converted values are preserved
            self._coerce_types(processed_data, input_schema)
            
            # Validate data through Pydantic (only for constraint checking: min/max, pattern, enum, etc.)
            # Pydantic does NOT convert types automatically, so we do it ourselves above
            validated_model = model(**processed_data)
            
            # Get validated data from model (for default values if field was not provided)
            validated_data_dict = validated_model.model_dump(exclude_unset=True)
            
            # Merge: processed_data (with converted types) has priority
            # validated_data_dict is only needed for default values of fields that were not provided
            final_data = {**validated_data_dict, **processed_data}
            
            return {
                "result": "success",
                "validated_data": final_data
            }
            
        except ValidationError as e:
            # Structured validation errors
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
                    "message": "Input data validation error",
                    "details": errors
                }
            }
            
        except Exception as e:
            self.logger.error(f"Validation error for {service_name}.{action_name}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Validation error: {str(e)}"
                }
            }
    
    def _get_input_schema(self, service_name: str, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Get input data schema from config.yaml
        """
        try:
            # Get plugin info (already cached in PluginsManager)
            plugin_info = self.settings_manager.get_plugin_info(service_name)
            
            if not plugin_info:
                return None
            
            # Extract action schema
            actions = plugin_info.get('actions', {})
            action_config = actions.get(action_name, {})
            
            if not action_config:
                return None
            
            # Get input schema
            input_config = action_config.get('input', {})
            
            if not input_config:
                return None
            
            # Structure: input.data.properties (see config.yaml)
            data_config = input_config.get('data', {})
            properties = data_config.get('properties', {})
            
            return properties if properties else None
            
        except Exception as e:
            self.logger.error(f"Error getting schema for {service_name}.{action_name}: {e}")
            return None
    
    def _get_or_create_model(self, service_name: str, action_name: str, schema: Dict[str, Any]):
        """
        Get or create Pydantic model with caching
        """
        cache_key = f"{service_name}.{action_name}"
        
        # Check cache
        if cache_key in self._validation_models:
            return self._validation_models[cache_key]
        
        # Create model
        model = self._create_pydantic_model(schema)
        
        # Cache it
        if model:
            self._validation_models[cache_key] = model
        
        return model
    
    def _create_pydantic_model(self, schema: Dict[str, Any], model_name: str = 'ValidationModel'):
        """
        Create Pydantic model from config.yaml schema (recursively for nested objects)
        """
        try:
            pydantic_fields = {}
            
            for field_name, field_config in schema.items():
                # Determine field type (can be union via |)
                type_str = field_config.get('type', 'string')
                
                # Determine required status (required by default for input schemas)
                is_optional = field_config.get('optional', False)
                
                # Check if None is in type
                has_none_in_type = isinstance(type_str, str) and 'none' in [p.strip().lower() for p in type_str.split('|')]
                
                # Parse type
                field_type = self._parse_type_string(type_str, field_config)
                
                # Create Field with constraints
                field_kwargs = {}
                
                # Check if type is Union for applying constraints
                origin = get_origin(field_type)
                is_union = origin == Union
                
                # Get Union arguments
                union_args = get_args(field_type) if is_union else []
                
                # Determine if type contains string or number
                has_string_type = (isinstance(field_type, type) and field_type is str) or (is_union and str in union_args)
                has_integer_type = (isinstance(field_type, type) and field_type is int) or (is_union and int in union_args)
                has_float_type = (isinstance(field_type, type) and field_type is float) or (is_union and float in union_args)
                
                # For optional fields don't apply validation constraints
                # Pydantic will handle None for Optional fields, but if empty string or 0 is passed,
                # constraints will still apply. So for optional fields we don't apply constraints.
                # For Union types also don't apply constraints - leave as is
                if not is_optional and not is_union:
                    # Apply constraints via Field only for NON-union types
                    # Constraints for strings (if it's a string)
                    if has_string_type:
                        if 'min_length' in field_config:
                            field_kwargs['min_length'] = field_config['min_length']
                        if 'max_length' in field_config:
                            field_kwargs['max_length'] = field_config['max_length']
                        if 'pattern' in field_config:
                            field_kwargs['regex'] = field_config['pattern']
                    
                    # Constraints for numbers (if it's a number)
                    if has_integer_type or has_float_type:
                        if 'min' in field_config:
                            field_kwargs['ge'] = field_config['min']
                        if 'max' in field_config:
                            field_kwargs['le'] = field_config['max']
                
                # Enum values
                if 'enum' in field_config:
                    enum_values = tuple(field_config['enum'])
                    literal_type = Literal[enum_values]
                    # If field is optional or None is in type, make Optional[Literal[...]]
                    if is_optional or has_none_in_type:
                        field_type = Optional[literal_type]
                    else:
                        field_type = literal_type
                
                # Create field
                if is_optional:
                    # If haven't made Optional yet (for enum already done above)
                    if 'enum' not in field_config:
                        # Check if already Union/Optional
                        origin = get_origin(field_type)
                        
                        # If None already in type (via |None), don't add Optional again
                        if not has_none_in_type:
                            # Check if already Optional
                            if origin == Union:
                                # Check if None already in Union
                                args = get_args(field_type)
                                if type(None) not in args:
                                    # Add None to union only if it's not there yet
                                    field_type = Union[tuple(list(args) + [type(None)])]
                            elif origin is None:
                                # Simple type (not Union, not Optional) - make Optional
                                field_type = Optional[field_type]
                    field_kwargs['default'] = None
                    pydantic_fields[field_name] = (field_type, Field(**field_kwargs))
                else:
                    # Required field - no default
                    # If None in type, leave as is (Union[Type, None])
                    # If no None in type, just Type
                    pydantic_fields[field_name] = (field_type, Field(**field_kwargs))
            
            # Create dynamic Pydantic model
            if not pydantic_fields:
                return None
            
            # Create model with explicit extra fields ignore
            # This ensures that fields not described in schema will be ignored
            Model = create_model(
                model_name,
                __config__=ConfigDict(extra='ignore'),
                **pydantic_fields
            )
            return Model
            
        except Exception as e:
            self.logger.error(f"Error creating Pydantic model: {e}")
            return None
    
    def _extract_from_config(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract values from _config for fields with from_config: true
        If field not provided in data, but from_config: true is specified, take value from data.get('_config', {}).get(field_name)
        """
        processed_data = data.copy()
        tenant_config = data.get('_config', {})
        
        for field_name, field_config in schema.items():
            # Skip if field already in data (explicitly provided)
            if field_name in processed_data:
                continue
            
            # Check if need to take from _config
            from_config = field_config.get('from_config', False)
            if not from_config:
                continue
            
            # Extract value from _config
            config_value = tenant_config.get(field_name)
            if config_value is not None:
                processed_data[field_name] = config_value
        
        return processed_data
    
    def _preprocess_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Data preprocessing before validation:
        - For optional non-string type parameters convert empty strings to None
        - This allows correct handling of fallback: for optional parameters
        """
        processed_data = data.copy()
        
        for field_name, field_config in schema.items():
            if field_name not in processed_data:
                continue
            
            value = processed_data[field_name]
            
            # Skip if value is already None
            if value is None:
                continue
            
            # Check if field is optional
            is_optional = field_config.get('optional', False)
            
            if not is_optional:
                continue
            
            # Get field type
            type_str = field_config.get('type', 'string')
            
            # If it's empty string and type is not string (or doesn't contain string in union)
            if value == "":
                # Check if type is string
                is_string_type = False
                if isinstance(type_str, str):
                    # Parse union types (e.g., "string|array")
                    type_parts = [t.strip().lower() for t in type_str.split('|')]
                    is_string_type = 'string' in type_parts
                elif type_str == 'string':
                    is_string_type = True
                
                # If type is not string (e.g., array, integer, etc.), convert empty string to None
                if not is_string_type:
                    processed_data[field_name] = None
        
        return processed_data
    
    def _coerce_types(self, data: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Type coercion to schema-specified type (only for NON-union types)
        Modifies data "on the fly" in the passed dictionary
        
        Conversion rules:
        - If type: string specified, but something else received (except None) → convert to str
        - If type: integer specified, but str received (digits only) → convert to int
        - If type: integer specified, but float received (whole number) → convert to int
        - If type: float specified, but int/str received → convert to float
        - If type: boolean specified, but 'true'/'false' received → convert to bool
        
        Union types (string|integer) - NOT processed, leave as is
        None - skip (don't convert)
        """
        for field_name, field_config in schema.items():
            if field_name not in data:
                continue
            
            value = data[field_name]
            
            # Skip None
            if value is None:
                continue
            
            type_str = field_config.get('type', 'string')
            
            # Skip Union types - don't touch them
            if isinstance(type_str, str) and '|' in type_str:
                continue
            
            # Process only simple types
            target_type = type_str.lower().strip() if isinstance(type_str, str) else None
            
            if not target_type:
                continue
            
            # Convert only if value type doesn't match target
            try:
                if target_type == 'string':
                    # If string specified, but something else received (except None) - convert to string
                    if not isinstance(value, str):
                        # Convert any types to string (int, float, bool, etc.)
                        # None skipped (already handled above)
                        data[field_name] = str(value)
                
                elif target_type == 'integer':
                    # If integer specified, but something else received - try to convert
                    if isinstance(value, float):
                        # Check if whole number
                        if value == int(value):
                            data[field_name] = int(value)
                    elif isinstance(value, str):
                        # Try to convert string to int (if consists of digits)
                        if value.strip().lstrip('-+').isdigit():
                            data[field_name] = int(value)
                    # If already int - leave as is
                
                elif target_type == 'float':
                    # If float specified, but int or str received - convert
                    if isinstance(value, (int, str)):
                        try:
                            data[field_name] = float(value)
                        except (ValueError, TypeError):
                            # Failed to convert - leave as is
                            pass
                    # If already float - leave as is
                
                elif target_type == 'boolean':
                    # If boolean specified, but string received - check explicit values
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower == 'true':
                            data[field_name] = True
                        elif value_lower == 'false':
                            data[field_name] = False
                        # Otherwise leave as is (Pydantic will check)
                    # If already bool - leave as is
                        
            except (ValueError, TypeError, OverflowError):
                # Failed to convert - leave as is, Pydantic will raise validation error
                pass
    
    def _parse_type_string(self, type_str: Any, field_config: Dict[str, Any]):
        """
        Parse type from schema with support for union types (string|None, integer|array|None)
        and nested objects in arrays (items.properties)
        """
        if not type_str:
            return str
        
        # If it's a string with | - it's a union type
        if isinstance(type_str, str) and '|' in type_str:
            type_parts = [part.strip() for part in type_str.split('|')]
            python_types = []
            
            for part in type_parts:
                if part.lower() == 'none':
                    # None will be handled through Optional
                    continue
                python_type = self._get_pydantic_type(part)
                python_types.append(python_type)
            
            # If None is in union - add to types
            has_none = 'none' in [p.strip().lower() for p in type_str.split('|')]
            
            if len(python_types) == 1:
                # Simple case: string|None -> Optional[str]
                if has_none:
                    return Optional[python_types[0]]
                return python_types[0]
            elif len(python_types) > 1:
                # Multiple union: integer|array|None -> Union[int, list, None]
                if has_none:
                    # Add None to union
                    python_types.append(type(None))
                return Union[tuple(python_types)]
            else:
                # Only None - return None
                return type(None)
        
        # If it's an array with items - check nested objects
        if isinstance(type_str, str) and type_str.lower() in ('array', 'list'):
            items_config = field_config.get('items', {})
            if isinstance(items_config, dict) and 'properties' in items_config:
                # Nested object in array - create model for items
                items_schema = items_config.get('properties', {})
                if items_schema:
                    # Create model for array element
                    item_model = self._create_pydantic_model(items_schema, f'ItemModel_{id(items_schema)}')
                    if item_model:
                        return List[item_model]
            # Regular array without nested objects
            return list
        
        # Regular type
        return self._get_pydantic_type(type_str)
    
    def _get_pydantic_type(self, type_str: str):
        """
        Convert simple type from schema to Pydantic type
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
        Invalidate validation models cache
        """
        if service_name and action_name:
            # Invalidate specific model
            cache_key = f"{service_name}.{action_name}"
            if cache_key in self._validation_models:
                del self._validation_models[cache_key]
                self.logger.info(f"Model cache {cache_key} cleared")
        else:
            # Clear entire cache
            count = len(self._validation_models)
            self._validation_models.clear()
            self.logger.info(f"Entire model cache cleared ({count} models removed)")

