"""
Tenant Actions - tenant management ActionHub methods
Handles tenant data operations (status, list, config updates)
"""

from typing import Any, Dict

from ..domain.error_handlers import handle_action_errors


class TenantActions:
    """Tenant management actions for tenant hub"""
    
    def __init__(self, logger, action_hub, database_manager, tenant_cache, tenant_repository, max_system_tenant_id):
        self.logger = logger
        self.action_hub = action_hub
        self.database_manager = database_manager
        self.tenant_cache = tenant_cache
        self.tenant_repository = tenant_repository
        self.max_system_tenant_id = max_system_tenant_id
    
    @handle_action_errors()
    async def sync_tenant_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync tenant data: create/update tenant"""
        # Use TenantRepository to sync tenant data
        # Pass data directly, as it already contains all tenant data
        return await self.tenant_repository.sync_tenant_data(data)
    
    @handle_action_errors()
    async def get_tenant_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get tenant status from cache only: last_updated_at, last_failed_at, last_error. No bot data."""
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            return {
                "result": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "tenant_id is required"}
            }
        cache_meta = await self.tenant_cache.get_tenant_cache(int(tenant_id))
        return {
            "result": "success",
            "response_data": {
                "last_updated_at": cache_meta.get("last_updated_at"),
                "last_failed_at": cache_meta.get("last_failed_at"),
                "last_error": cache_meta.get("last_error"),
            }
        }

    @handle_action_errors()
    async def get_bot_id_by_tenant_id(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get bot_id by tenant_id and bot_type. Database lookup; only telegram supported for now."""
        tenant_id = data.get('tenant_id')
        if not tenant_id:
            return {
                "result": "error",
                "error": {"code": "VALIDATION_ERROR", "message": "tenant_id is required"}
            }
        bot_type = (data.get('bot_type') or 'telegram').strip().lower()
        if bot_type != 'telegram':
            return {
                "result": "error",
                "error": {"code": "UNSUPPORTED_BOT_TYPE", "message": f"Unsupported bot_type: {bot_type}. Only telegram is supported."}
            }
        bot_id = await self.tenant_cache.get_bot_id_by_tenant_id(int(tenant_id))
        if bot_id is None:
            return {
                "result": "error",
                "error": {"code": "NOT_FOUND", "message": f"No bot for tenant {tenant_id} (type={bot_type})"}
            }
        return {"result": "success", "response_data": {"bot_id": bot_id}}

    @handle_action_errors()
    async def get_tenants_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of all tenant IDs with separation into public and system.
        """
        master_repo = self.database_manager.get_master_repository()
        all_tenant_ids = await master_repo.get_all_tenant_ids()
        
        if all_tenant_ids is None:
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to get tenant list from database"
                }
            }
        
        # Sort all IDs in ascending order
        all_tenant_ids = sorted(all_tenant_ids)
        
        # Separate into public (ID > max_system_tenant_id) and system (ID <= max_system_tenant_id)
        public_tenant_ids = sorted([tid for tid in all_tenant_ids if tid > self.max_system_tenant_id])
        system_tenant_ids = sorted([tid for tid in all_tenant_ids if tid <= self.max_system_tenant_id])
        
        return {
            "result": "success",
            "response_data": {
                "tenant_ids": all_tenant_ids,
                "public_tenant_ids": public_tenant_ids,
                "system_tenant_ids": system_tenant_ids,
                "tenant_count": len(all_tenant_ids)
            }
        }
    
    @handle_action_errors()
    async def update_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update tenant config.
        Updates only provided fields, leaves others untouched.
        """
        tenant_id = data.get('tenant_id')
        ai_token = data.get('ai_token')
        
        # Check that tenant exists
        master_repo = self.database_manager.get_master_repository()
        tenant_data = await master_repo.get_tenant_by_id(tenant_id)
        if not tenant_data:
            return {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Tenant {tenant_id} not found"
                }
            }
        
        # Prepare data for update (only provided fields)
        # If field explicitly provided (even if None) - update it
        update_data = {}
        updated_fields = []
        
        if 'ai_token' in data:
            update_data['ai_token'] = ai_token  # Can be None for deletion
            updated_fields.append('ai_token')
        
        if not update_data:
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "No fields to update"
                }
            }
        
        # Update DB
        update_success = await master_repo.update_tenant(tenant_id, update_data)
        if not update_success:
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to update tenant {tenant_id}"
                }
            }
        
        # Update config cache from DB (so all services immediately get current data)
        await self.tenant_cache.update_tenant_config_cache(tenant_id)
        
        self.logger.info(f"[Tenant-{tenant_id}] Tenant config updated: {', '.join(updated_fields)}")
        
        return {
            "result": "success"
        }
