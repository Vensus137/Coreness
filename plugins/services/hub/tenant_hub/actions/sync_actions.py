"""
Sync Actions - synchronization-related ActionHub methods
Handles tenant synchronization operations
"""

from typing import Any, Dict

from ..domain.error_handlers import handle_action_errors


class SyncActions:
    """Synchronization actions for tenant hub"""
    
    def __init__(self, logger, sync_orchestrator, block_sync_executor):
        self.logger = logger
        self.sync_orchestrator = sync_orchestrator
        self.block_sync_executor = block_sync_executor
    
    @handle_action_errors()
    async def sync_tenant(self, data: Dict[str, Any], pull_from_github: bool = True) -> Dict[str, Any]:
        """
        Sync tenant configuration with database.
        By default updates data from GitHub before sync.
        Delegates execution to sync orchestrator.
        """
        tenant_id = data.get('tenant_id')
        
        # Use orchestrator to sync tenant (both blocks)
        return await self.sync_orchestrator.sync_tenant(tenant_id, pull_from_github)
    
    @handle_action_errors()
    async def sync_all_tenants(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync all tenants: system (locally) + public (from GitHub).
        Delegates execution to sync orchestrator.
        """
        return await self.sync_orchestrator.sync_all_tenants()
    
    @handle_action_errors()
    async def sync_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenant config: pull from GitHub + parsing + sync.
        """
        tenant_id = data.get('tenant_id')
        
        # Single entry point: sync only config
        return await self.block_sync_executor.sync_blocks(
            tenant_id,
            {"bots": [], "scenarios": False, "storage": False, "config": True},
            pull_from_github=True
        )
