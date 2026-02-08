"""
Storage Hub - service for managing tenant storage
Handles parsing and synchronization of tenant storage data
"""

from typing import Any, Dict

from .managers.storage_manager import StorageManager
from .parsers.storage_parser import StorageParser


class StorageHub:
    """
    Service for managing tenant storage
    - Parses storage/*.yaml files
    - Synchronizes storage data with database
    - Provides CRUD operations for storage
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        
        # Create storage parser
        self.storage_parser = StorageParser(
            logger=self.logger,
            settings_manager=self.settings_manager
        )
        
        # Create storage manager
        self.storage_manager = StorageManager(
            database_manager=self.database_manager,
            logger=self.logger,
            settings_manager=self.settings_manager
        )
        
        # Register ourselves in ActionHub
        self.action_hub.register('storage_hub', self)
    
    # === Actions for ActionHub ===
    
    async def sync_tenant_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronize tenant storage: parse storage/*.yaml + sync to database
        Called by Tenant Hub when storage/ files change
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Parse storage files
            parse_result = await self.storage_parser.parse_storage(tenant_id)
            
            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = error_obj.get('message', 'Unknown error') if isinstance(error_obj, dict) else str(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Error parsing storage: {error_msg}")
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Failed to parse storage for tenant {tenant_id}: {error_msg}"
                    }
                }
            
            storage_data = parse_result.get('response_data', {}).get('storage', {})
            
            if not storage_data:
                self.logger.info(f"[Tenant-{tenant_id}] No storage data to synchronize")
                return {"result": "success"}
            
            # Synchronize storage to database
            groups_count = len(storage_data)
            if groups_count > 0:
                success = await self.storage_manager.sync_storage(tenant_id, storage_data)
                
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing storage")
                    return {
                        "result": "error",
                        "error": {
                            "code": "SYNC_ERROR",
                            "message": "Failed to synchronize storage"
                        }
                    }
                
                self.logger.info(f"[Tenant-{tenant_id}] Storage successfully synchronized ({groups_count} groups)")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] No storage to synchronize")
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get storage values for tenant"""
        try:
            # Validation is done centrally in ActionRegistry
            # Convert numbers to strings for group_key and key (if numbers passed)
            group_key = data.get('group_key')
            if group_key is not None and not isinstance(group_key, str):
                group_key = str(group_key)
            
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.storage_manager.get_storage(
                data.get('tenant_id'),
                group_key=group_key,
                group_key_pattern=data.get('group_key_pattern'),
                key=key,
                key_pattern=data.get('key_pattern'),
                format_yaml=data.get('format', False)
            )
        except Exception as e:
            self.logger.error(f"Error getting storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }

    async def set_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set storage values for tenant
        Supports mixed approach with priority: group_key -> key -> value -> values
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            group_key = data.get('group_key')
            # Convert number to string for group_key (if number passed)
            if group_key is not None and not isinstance(group_key, str):
                group_key = str(group_key)
            
            key = data.get('key')
            # Convert number to string for key (if number passed)
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            value = data.get('value')
            values = data.get('values')
            
            return await self.storage_manager.set_storage(
                tenant_id,
                group_key=group_key,
                key=key,
                value=value,
                values=values,
                format_yaml=data.get('format', False)
            )
        except Exception as e:
            self.logger.error(f"Error setting storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def delete_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete values or groups from storage"""
        try:
            # Validation is done centrally in ActionRegistry
            # Convert numbers to strings for group_key and key (if numbers passed)
            group_key = data.get('group_key')
            if group_key is not None and not isinstance(group_key, str):
                group_key = str(group_key)
            
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.storage_manager.delete_storage(
                data.get('tenant_id'),
                group_key=group_key,
                group_key_pattern=data.get('group_key_pattern'),
                key=key,
                key_pattern=data.get('key_pattern')
            )
        except Exception as e:
            self.logger.error(f"Error deleting storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_storage_groups(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of unique group keys for tenant"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.storage_manager.get_storage_groups(data.get('tenant_id'))
        except Exception as e:
            self.logger.error(f"Error getting storage groups list: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
