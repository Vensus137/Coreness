"""
StorageManager - submodule for working with tenant attribute storage
"""

from typing import Any, Dict, Optional


class StorageManager:
    """
    Submodule for working with tenant attribute storage
    Manages tenant key-value data (settings, limits, features, etc.)
    """
    
    def __init__(self, database_manager, logger, settings_manager):
        self.database_manager = database_manager
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Get limits from settings once on initialization
        service_settings = self.settings_manager.get_plugin_settings('storage_hub')
        self.storage_max_records = service_settings.get('storage_max_records', 100)
        self.storage_groups_max_limit = service_settings.get('storage_groups_max_limit', 200)
    
    async def get_storage(
        self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None,
        key: Optional[str] = None, key_pattern: Optional[str] = None, format_yaml: bool = False, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get storage values for tenant
        Supports getting all values, group, specific value, and pattern search
        """
        try:
            # Validation: key can only be specified together with group_key or group_key_pattern
            if (key or key_pattern) and not (group_key or group_key_pattern):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "key can only be specified together with group_key or group_key_pattern"
                    }
                }
            
            # Use limit from settings if not explicitly specified
            if limit is None:
                limit = self.storage_max_records
            
            # Use universal get method
            master_repo = self.database_manager.get_master_repository()
            records = await master_repo.get_storage_records(
                tenant_id, group_key, group_key_pattern, key, key_pattern, limit
            )
            
            if not records:
                return {"result": "not_found"}
            
            # Determine what was requested to simplify response structure
            has_group = group_key or group_key_pattern
            has_key = key or key_pattern
            is_exact_key = key and not key_pattern
            is_exact_group = group_key and not group_key_pattern
            
            if has_group and has_key and is_exact_key and is_exact_group:
                # Specific value requested (exact group_key + exact key)
                # Return only value
                first_record = records[0]
                storage_values = first_record.get('value')
            elif has_group and is_exact_group:
                # Exact group requested (group_key without pattern, with key_pattern or without key)
                # Return group structure {key: value, key2: value2}
                storage_values = {}
                for record in records:
                    k = record.get('key')
                    v = record.get('value')
                    # Check key presence (protection against invalid data)
                    if k is not None:
                        storage_values[k] = v
            elif has_group:
                # Group requested by pattern (group_key_pattern)
                # May be multiple groups, return structure {group_key: {key: value}}
                storage_values = {}
                for record in records:
                    gk = record.get('group_key')
                    k = record.get('key')
                    v = record.get('value')
                    # Check required fields presence (protection against invalid data)
                    if gk is not None and k is not None:
                        if gk not in storage_values:
                            storage_values[gk] = {}
                        storage_values[gk][k] = v
            else:
                # Entire storage requested (nothing specified)
                # Return full structure {group_key: {key: value}}
                storage_values = {}
                for record in records:
                    gk = record.get('group_key')
                    k = record.get('key')
                    v = record.get('value')
                    # Check required fields presence (protection against invalid data)
                    if gk is not None and k is not None:
                        if gk not in storage_values:
                            storage_values[gk] = {}
                        storage_values[gk][k] = v
            
            # Base response with structured data
            response_data = {
                "storage_values": storage_values
            }
            
            # If formatted output requested
            if format_yaml:
                import yaml
                # For primitives (strings, numbers, bool) don't use YAML formatting,
                # to avoid adding document end marker (...)
                if isinstance(storage_values, (str, int, float, bool)) or storage_values is None:
                    formatted_text = str(storage_values) if storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        storage_values,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )
                    # Remove extra line breaks at end
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
        self, tenant_id: int, group_key: Optional[str] = None, key: Optional[str] = None,
        value: Optional[Any] = None, values: Optional[Dict[str, Any]] = None, format_yaml: bool = False
    ) -> Dict[str, Any]:
        """
        Set storage values for tenant
        Supports mixed approach with priority: group_key -> key -> value -> values
        - If group_key specified:
          - If key specified:
            - If value specified: set single value
            - If values specified: set structure for group
            - Otherwise: error
          - If values specified (without key): set structure for group
          - Otherwise: error
        - If values specified (without group_key): set full structure
        """
        try:
            # Determine mode and form structure for DB write
            # Priority: group_key -> key -> value -> values
            if group_key:
                # Mode with group_key
                if key:
                    # Mode: group_key + key
                    if value is not None:
                        # Mode: group_key + key + value - set single value
                        final_values = {group_key: {key: value}}
                        return_mode = "single_value"  # Return only value
                    elif values:
                        # Mode: group_key + key + values - set structure for group
                        if not isinstance(values, dict):
                            return {
                                "result": "error",
                                "error": {
                                    "code": "VALIDATION_ERROR",
                                    "message": "Parameter values must be an object {key: value}"
                                }
                            }
                        final_values = {group_key: values}
                        return_mode = "group"  # Return {key: value}
                    else:
                        return {
                            "result": "error",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "When specifying group_key and key, must specify value or values"
                            }
                        }
                elif values:
                    # Mode: group_key + values (without key) - set structure for group
                    if not isinstance(values, dict):
                        return {
                            "result": "error",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Parameter values must be an object {key: value}"
                            }
                        }
                    final_values = {group_key: values}
                    return_mode = "group"  # Return {key: value}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "When specifying group_key, must specify key+value or values"
                        }
                    }
            elif values:
                # Mode: full structure values (without group_key)
                if not isinstance(values, dict):
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Parameter values must be an object {group_key: {key: value}}"
                        }
                    }
                # Check structure: all values must be dictionaries
                for gk, group_data in values.items():
                    if not isinstance(group_data, dict):
                        return {
                            "result": "error",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": f"Invalid structure: group '{gk}' must be an object with keys, but got type {type(group_data).__name__}"
                            }
                        }
                final_values = values
                return_mode = "full"  # Return {group_key: {key: value}}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Must specify either values (full structure) or group_key with key+value or values"
                    }
                }
            
            # Use universal set method (batch for all groups)
            master_repo = self.database_manager.get_master_repository()
            success = await master_repo.set_storage_records(tenant_id, final_values)
            
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
                # Single value set (group_key + key + value) - return only value (like in get_storage for exact group_key + exact key)
                storage_values = final_values[group_key][key]
            elif return_mode == "group":
                # Group set (group_key + values) - return {key: value} (like in get_storage for exact group_key)
                storage_values = final_values[group_key]
            else:
                # Full structure set (values) - return {group_key: {key: value}} (like in get_storage for entire storage)
                storage_values = final_values
            
            # Base response with structured data
            response_data = {
                "storage_values": storage_values
            }
            
            # If formatted output requested
            if format_yaml:
                import yaml
                # For primitives (strings, numbers, bool) don't use YAML formatting,
                # to avoid adding document end marker (...)
                if isinstance(storage_values, (str, int, float, bool)) or storage_values is None:
                    formatted_text = str(storage_values) if storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        storage_values,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )
                    # Remove extra line breaks at end
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
        self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None, 
        key: Optional[str] = None, key_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete values or groups from storage
        If key or key_pattern specified - delete value, otherwise delete group
        """
        try:
            # Validation: must specify at least one group parameter
            if not (group_key or group_key_pattern):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Must specify group_key or group_key_pattern"
                    }
                }
            
            # Use universal delete method
            master_repo = self.database_manager.get_master_repository()
            deleted_count = await master_repo.delete_storage_records(
                tenant_id, group_key, group_key_pattern, key, key_pattern
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
    
    async def get_storage_groups(self, tenant_id: int) -> Dict[str, Any]:
        """
        Get list of unique group keys for tenant
        Returns only list of group_key without values (with limit on number of groups)
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            # Request limit + 1 to determine if there are more groups
            group_keys = await master_repo.get_storage_group_keys(tenant_id, limit=self.storage_groups_max_limit + 1)
            
            if group_keys is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Error getting group list"
                    }
                }
            
            # Check if list was truncated
            is_truncated = len(group_keys) > self.storage_groups_max_limit
            
            # If truncated, take only first limit groups
            if is_truncated:
                group_keys = group_keys[:self.storage_groups_max_limit]
            
            response_data = {
                "group_keys": group_keys
            }
            
            # Add information that list was truncated
            if is_truncated:
                response_data["is_truncated"] = True
            
            return {
                "result": "success",
                "response_data": response_data
            }
                
        except Exception as e:
            self.logger.error(f"Error getting storage group list: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_storage(self, tenant_id: int, storage_data: Dict[str, Dict[str, str]]) -> bool:
        """
        Synchronize attributes from config
        Optimized synchronization: delete only groups from config with one batch query,
        then load all data from config. Doesn't require getting all groups from DB.
        
        storage_data: dictionary {group_key: {key: value}}
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Get list of groups from config (only those that need to be synchronized)
            groups_to_sync = list(storage_data.keys())
            
            # Delete groups from config with one batch query (optimization)
            # Delete only groups that exist in config - don't touch others
            if groups_to_sync:
                deleted_count = await master_repo.delete_groups_batch(tenant_id, groups_to_sync)
                if deleted_count is None:
                    self.logger.warning(f"[Tenant-{tenant_id}] Error deleting groups for synchronization")
                elif deleted_count > 0:
                    self.logger.info(f"[Tenant-{tenant_id}] Deleted {deleted_count} records from {len(groups_to_sync)} groups")
            
            # Load new data from config (batch for all groups at once)
            if storage_data:
                success = await master_repo.set_storage_records(tenant_id, storage_data)
                if not success:
                    self.logger.warning(f"[Tenant-{tenant_id}] Failed to synchronize storage")
                    return False
            
            self.logger.info(f"[Tenant-{tenant_id}] Storage synchronization completed (processed {len(storage_data)} groups)")
            return True
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing storage: {e}")
            return False
