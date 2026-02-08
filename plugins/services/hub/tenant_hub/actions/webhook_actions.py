"""
Webhook Actions - webhook-related ActionHub methods
Handles synchronization from file changes (webhooks/polling)
"""

from typing import Any, Dict

from ..domain.error_handlers import handle_action_errors


class WebhookActions:
    """Webhook actions for tenant hub"""
    
    def __init__(self, logger, github_sync, block_sync_executor):
        self.logger = logger
        self.github_sync = github_sync
        self.block_sync_executor = block_sync_executor
    
    @handle_action_errors()
    async def sync_tenants_from_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenants from list of changed files (universal method for webhooks and polling).
        Accepts file list in format [{"filename": "path"}, ...] or ["path1", "path2", ...].
        """
        files = data.get('files', [])
        
        if not files:
            return {
                "result": "error",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "File list is empty"
                }
            }
        
        # Convert format to universal (if needed)
        normalized_files = []
        for file_item in files:
            if isinstance(file_item, str):
                # Format from webhook: ["path1", "path2"]
                normalized_files.append({"filename": file_item})
            elif isinstance(file_item, dict):
                # Format from Compare API: [{"filename": "path"}, ...]
                normalized_files.append(file_item)
        
        # Use existing logic from github_sync for parsing
        changed_tenants = self.github_sync._extract_tenant_changes_with_protection(normalized_files)
        
        if not changed_tenants:
            self.logger.info("No changed tenants in file list")
            return {"result": "success", "response_data": {"synced_tenants": 0}}
        
        # Sync each changed tenant
        self.logger.info(f"Changes detected in {len(changed_tenants)} tenants")
        synced_count = 0
        errors = []
        
        for tenant_id, blocks in changed_tenants.items():
            try:
                bots_str = ', '.join(blocks.get('bots', [])) if blocks.get('bots') else '-'
                blocks_str = f"(bots: {bots_str}, scenarios: {'+' if blocks.get('scenarios') else '-'}, storage: {'+' if blocks.get('storage') else '-'}, config: {'+' if blocks.get('config') else '-'})"
                self.logger.info(f"[Tenant-{tenant_id}] Sync via webhook {blocks_str}")
                
                # Use existing block sync method
                result = await self.block_sync_executor.sync_blocks(
                    tenant_id,
                    blocks,
                    pull_from_github=True  # Always update from GitHub on webhook
                )
                
                if result.get('result') == 'success':
                    synced_count += 1
                else:
                    error_obj = result.get('error', {})
                    errors.append(f"Tenant-{tenant_id}: {error_obj.get('message', 'Unknown error')}")
                    
            except Exception as e:
                self.logger.error(f"[Tenant-{tenant_id}] Error syncing via webhook: {e}")
                errors.append(f"Tenant-{tenant_id}: {str(e)}")
        
        if errors:
            return {
                "result": "partial_success",
                "response_data": {
                    "synced_tenants": synced_count,
                    "total_tenants": len(changed_tenants),
                    "errors": errors
                }
            }
        
        return {
            "result": "success",
            "response_data": {
                "synced_tenants": synced_count,
                "total_tenants": len(changed_tenants)
            }
        }
