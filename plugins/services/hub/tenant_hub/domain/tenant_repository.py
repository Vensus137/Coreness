"""
TenantRepository - repository for working with tenant data
"""

from typing import Any, Dict


class TenantRepository:
    """
    Repository for working with tenant data.
    Contains logic for synchronizing tenant settings with database.
    """
    
    def __init__(self, database_manager, logger):
        self.database_manager = database_manager
        self.logger = logger
    
    async def sync_tenant_data(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronize tenant data: create/update tenant"""
        try:
            tenant_id = tenant_data.get('tenant_id')
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id is required in tenant_data"
                    }
                }
            
            # Synchronize tenant settings (create without data from settings.yaml)
            try:
                await self._sync_tenant_settings(tenant_id, tenant_data)
            except Exception as e:
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": f"Error synchronizing tenant settings: {str(e)}"
                    }
                }
            
            return {
                "result": "success",
                "response_data": {
                    "tenant_id": tenant_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_tenant_settings(self, tenant_id: int, tenant_data: Dict[str, Any]):
        """Synchronize tenant settings - create tenant without data from settings.yaml"""
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Search for existing tenant
            existing_tenant = await master_repo.get_tenant_by_id(tenant_id)
            
            if not existing_tenant:
                # Create new tenant
                created_id = await master_repo.create_tenant({
                    'id': tenant_id
                })
                
                if created_id:
                    self.logger.info(f"[Tenant-{tenant_id}] Created new tenant (without data from settings.yaml)")
                else:
                    self.logger.warning(f"[Tenant-{tenant_id}] Failed to create tenant")
                
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant settings {tenant_id}: {e}")
            # Don't re-raise exception, as it's handled in sync_tenant_data
