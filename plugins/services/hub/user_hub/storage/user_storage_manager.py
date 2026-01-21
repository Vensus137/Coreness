"""
UserStorageManager - submodule for working with user data storage
"""

import json
from typing import Any, Dict, List, Optional


class UserStorageManager:
    """
    Submodule for working with user data storage
    Manages user key-value data (without groups, flat structure)
    """
    
    def __init__(self, database_manager, logger, settings_manager):
        self.database_manager = database_manager
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Get record limit from settings once on initialization
        service_settings = self.settings_manager.get_plugin_settings('user_hub')
        self.storage_max_records = service_settings.get('storage_max_records', 100)
    
    async def get_storage(
        self, tenant_id: int, user_id: int, key: Optional[str] = None,
        key_pattern: Optional[str] = None, format_yaml: bool = False, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get storage values for user
        Supports getting all values, specific value, and pattern search
        """
        try:
            # Use limit from settings if not explicitly specified
            if limit is None:
                limit = self.storage_max_records
            
            # Use universal get method
            master_repo = self.database_manager.get_master_repository()
            records = await master_repo.get_user_storage_records(
                tenant_id, user_id, key, key_pattern, limit
            )
            
            if not records:
                return {"result": "not_found"}
            
            # Determine what was requested to simplify response structure
            if key and not key_pattern:
                # Specific key requested (exact value) - return only value
                first_record = records[0]
                user_storage_values = first_record.get('value')
            else:
                # Entire storage requested (nothing specified) or pattern for keys
                # Return structure {key: value, key2: value2}
                user_storage_values = {}
                for record in records:
                    k = record.get('key')
                    v = record.get('value')
                    # Check key presence (protection against incorrect data)
                    if k is not None:
                        user_storage_values[k] = v
            
            # Base response with structured data
            response_data = {
                "user_storage_values": user_storage_values
            }
            
            # If formatted output requested
            if format_yaml:
                import yaml
                # For primitives (strings, numbers, bool) don't use YAML formatting,
                # to avoid adding document end marker (...)
                if isinstance(user_storage_values, (str, int, float, bool)) or user_storage_values is None:
                    formatted_text = str(user_storage_values) if user_storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        user_storage_values,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )
                    # Remove extra newlines at end
                    formatted_text = formatted_text.rstrip()
                response_data["formatted_text"] = formatted_text
            
            return {
                "result": "success",
                "response_data": response_data
            }
                
        except Exception as e:
            self.logger.error(f"Error getting storage data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def set_storage(
        self, tenant_id: int, user_id: int, key: Optional[str] = None, value: Optional[Any] = None,
        values: Optional[Dict[str, Any]] = None, format_yaml: bool = False
    ) -> Dict[str, Any]:
        """
        Set storage values for user
        Supports mixed approach with priority: key -> value -> values
        - If key specified: value must be specified (sets single value)
        - If values specified (without key): sets full structure {key: value}
        """
        try:
            # Determine mode and form structure for DB write
            # Priority: key -> value -> values
            if key:
                # Mode with key - value must be specified
                if value is not None:
                    # Mode: key + value - sets single value
                    final_values = {key: value}
                    return_mode = "single_value"  # Return only value
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "When key is specified, value must be specified"
                        }
                    }
            elif values:
                # Mode: full values structure (without key)
                if not isinstance(values, dict):
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "values parameter must be object {key: value}"
                        }
                    }
                final_values = values
                return_mode = "structure"  # Return {key: value}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Must specify either values (full structure) or key with value"
                    }
                }
            
            # Use universal set method (batch for all keys)
            master_repo = self.database_manager.get_master_repository()
            success = await master_repo.set_user_storage_records(tenant_id, user_id, final_values)
            
            if not success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to set values"
                    }
                }
            
            # Determine response format similar to get_storage based on input parameters
            if return_mode == "single_value":
                # Single value set (key + value) - return only value (like get_storage for single key)
                user_storage_values = final_values[key]
            else:
                # Structure set - return {key: value} (like get_storage for multiple keys)
                user_storage_values = final_values
            
            # Base response with structured data
            response_data = {
                "user_storage_values": user_storage_values
            }
            
            # If formatted output requested
            if format_yaml:
                import yaml
                # For primitives (strings, numbers, bool) don't use YAML formatting,
                # to avoid adding document end marker (...)
                if isinstance(user_storage_values, (str, int, float, bool)) or user_storage_values is None:
                    formatted_text = str(user_storage_values) if user_storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        user_storage_values,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )
                    # Remove extra newlines at end
                    formatted_text = formatted_text.rstrip()
                response_data["formatted_text"] = formatted_text
            
            return {
                "result": "success",
                "response_data": response_data
            }
                
        except Exception as e:
            self.logger.error(f"Error setting storage data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def delete_storage(
        self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete values from storage
        If key or key_pattern specified - deletes value/values, otherwise deletes all user records
        """
        try:
            # Use universal delete method
            master_repo = self.database_manager.get_master_repository()
            deleted_count = await master_repo.delete_user_storage_records(
                tenant_id, user_id, key, key_pattern
            )
            
            if deleted_count > 0:
                return {"result": "success"}
            else:
                return {"result": "not_found"}
                
        except Exception as e:
            self.logger.error(f"Error deleting storage data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _normalize_value(self, value: Any) -> str:
        """
        Normalize value for comparison
        For JSON values: parses and serializes back with normalization
        For simple values: converts to string
        """
        if value is None:
            return ""
        
        # If value is already string, check if it's JSON
        if isinstance(value, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(value)
                # Serialize back with normalization (sort_keys=True for dict)
                return json.dumps(parsed, sort_keys=True, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                # Not JSON, return as is
                return str(value)
        
        # If value is dict or list, serialize to JSON with normalization
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        
        # For simple types (int, float, bool) convert to string
        return str(value)
    
    async def find_users_by_storage_value(self, tenant_id: int, key: str, value: Any) -> List[int]:
        """
        Search users by key and value in storage
        Uses index for fast search by tenant_id and key, then filters by value in memory
        """
        try:
            # Get all records by tenant_id and key (fast through index)
            master_repo = self.database_manager.get_master_repository()
            records = await master_repo.get_user_storage_by_tenant_and_key(tenant_id, key)
            
            if not records:
                return []
            
            # Normalize search value once
            normalized_target_value = self._normalize_value(value)
            
            # Filter records by value in memory
            matching_user_ids = []
            for record in records:
                record_value = record.get('value')
                # Normalize value from DB for comparison (JSON objects may have different key order)
                normalized_record_value = self._normalize_value(record_value)
                
                if normalized_record_value == normalized_target_value:
                    user_id = record.get('user_id')
                    if user_id is not None:
                        matching_user_ids.append(user_id)
            
            # Remove duplicates (in case user has multiple records with same value)
            return list(set(matching_user_ids))
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error searching users by storage key={key}, value={value}: {e}")
            return []
