"""
User Hub Service - central service for managing user states
"""

from typing import Any, Dict

from .storage.user_storage_manager import UserStorageManager


class UserHubService:
    """
    Central service for managing user states
    Wrapper over user_manager for use in scenarios
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.user_manager = kwargs['user_manager']
        self.database_manager = kwargs['database_manager']
        
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('user_hub')
        
        # Register ourselves in ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('user_hub', self)
        
        # Create user storage manager
        self.user_storage_manager = UserStorageManager(
            self.database_manager,
            self.logger,
            self.settings_manager
        )
    
    # === Actions for ActionHub ===
    
    async def set_user_state(self, data: dict) -> Dict[str, Any]:
        """
        Set user state
        """
        try:
            # Validation is done centrally in ActionRegistry
            user_id = data.get('user_id')
            tenant_id = data.get('tenant_id')
            state = data.get('state')
            expires_in_seconds = data.get('expires_in_seconds')
            
            # Call user_manager method (now returns full data)
            user_data = await self.user_manager.set_user_state(
                user_id=user_id,
                tenant_id=tenant_id,
                state=state,
                expires_in_seconds=expires_in_seconds
            )
            
            if user_data is not None:
                return {
                    "result": "success",
                    "response_data": {
                        "user_state": user_data.get('user_state'),
                        "user_state_expired_at": user_data.get('user_state_expired_at')
                    }
                }
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to set user state"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error setting user state: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_user_state(self, data: dict) -> Dict[str, Any]:
        """
        Get user state
        """
        try:
            # Validation is done centrally in ActionRegistry
            user_id = data.get('user_id')
            tenant_id = data.get('tenant_id')
            
            # Get state and expiration time in one call
            state_data = await self.user_manager.get_user_state(user_id, tenant_id)
            
            if state_data:
                return {
                    "result": "success",
                    "response_data": {
                        "user_state": state_data.get('user_state'),
                        "user_state_expired_at": state_data.get('user_state_expired_at')
                    }
                }
            else:
                return {
                    "result": "success",
                    "response_data": {
                        "user_state": None,
                        "user_state_expired_at": None
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting user state: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def clear_user_state(self, data: dict) -> Dict[str, Any]:
        """
        Clear user state
        """
        try:
            # Validation is done centrally in ActionRegistry
            user_id = data.get('user_id')
            tenant_id = data.get('tenant_id')
            
            # Call user_manager method to clear state
            success = await self.user_manager.clear_user_state(
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            if success:
                return {"result": "success"}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to clear user state"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error clearing user state: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    # === User Storage Actions ===
    
    async def get_user_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get storage values for user"""
        try:
            # Validation is done centrally in ActionRegistry
            # Convert number to string for key (if number passed)
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.user_storage_manager.get_storage(
                data.get('tenant_id'),
                data.get('user_id'),
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
    
    async def set_user_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set storage values for user
        Supports mixed approach with priority: key -> value -> values
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            user_id = data.get('user_id')
            key = data.get('key')
            # Convert number to string for key (if number passed)
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            value = data.get('value')
            values = data.get('values')
            
            return await self.user_storage_manager.set_storage(
                tenant_id,
                user_id,
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
    
    async def delete_user_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Delete values from storage"""
        try:
            # Validation is done centrally in ActionRegistry
            # Convert number to string for key (if number passed)
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.user_storage_manager.delete_storage(
                data.get('tenant_id'),
                data.get('user_id'),
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
    
    async def get_tenant_users(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of all user_ids for specified tenant
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            master_repo = self.database_manager.get_master_repository()
            user_ids = await master_repo.get_user_ids_by_tenant(tenant_id)
            
            return {
                "result": "success",
                "response_data": {
                    "user_ids": user_ids,
                    "user_count": len(user_ids)
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting user list: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_users_by_storage_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search users by key and value in storage
        Allows finding all users who have a specific key with a specific value in storage
        For example, find all users with active subscription
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            key = data.get('key')
            value = data.get('value')
            
            # Use UserStorageManager for search
            user_ids = await self.user_storage_manager.find_users_by_storage_value(
                tenant_id=tenant_id,
                key=key,
                value=value
            )
            
            return {
                "result": "success",
                "response_data": {
                    "user_ids": user_ids,
                    "user_count": len(user_ids)
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error searching users by storage key={key}, value={value}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }