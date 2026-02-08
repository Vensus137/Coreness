"""
Block Sync Executor - executor for tenant block synchronization
Delegates synchronization to specialized services through Action Hub
"""

from pathlib import Path
from typing import Any, Dict, List


class BlockSyncExecutor:
    """
    Executor for tenant block synchronization
    Delegates synchronization to specialized services:
    - sync_tenant_scenarios → scenario_processor
    - sync_tenant_storage → storage_hub
    - sync_{bot_name}_bot → corresponding bot service (e.g., sync_telegram_bot → telegram_bot_manager)
    """
    
    def __init__(self, logger, action_hub, github_sync, settings_manager, tenant_cache):
        self.logger = logger
        self.action_hub = action_hub
        self.github_sync = github_sync
        self.settings_manager = settings_manager
        self.tenant_cache = tenant_cache
        
        # Get system tenant boundary once on initialization
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 99)
        
        # Get tenants path
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
    
    def _get_available_bots(self, tenant_id: int) -> List[str]:
        """
        Get list of available bots for tenant by scanning bots/ folder
        
        Returns list of bot names (e.g., ["telegram", "whatsapp"])
        """
        try:
            tenant_name = f"tenant_{tenant_id}"
            tenant_path = self.tenants_path / tenant_name
            bots_path = tenant_path / "bots"
            
            if not bots_path.exists() or not bots_path.is_dir():
                return []
            
            # Scan for .yaml/.yml files in bots/ directory
            bot_names = []
            for file in bots_path.iterdir():
                if file.is_file() and file.suffix in ['.yaml', '.yml']:
                    bot_name = file.stem  # filename without extension
                    bot_names.append(bot_name)
            
            return bot_names
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error scanning bots folder: {e}")
            return []
    
    def _extract_error_message(self, error: dict) -> str:
        """
        Extract error message from error object
        """
        return error.get('message', 'Unknown error') if error else 'Unknown error'
    
    async def _prepare_tenant_data(self, tenant_id: int, pull_from_github: bool = False) -> Dict[str, Any]:
        """
        Prepare tenant data: pull from GitHub (optional) + create tenant if it doesn't exist
        """
        try:
            # For system tenants always skip pull from GitHub
            if pull_from_github and tenant_id <= self.max_system_tenant_id:
                pull_from_github = False
            
            # Update data from GitHub (if needed)
            if pull_from_github:
                self.logger.info(f"[Tenant-{tenant_id}] Updating data from GitHub...")
                pull_result = await self.github_sync.pull_tenant(tenant_id)
                
                if pull_result.get("result") != "success":
                    error_msg = self._extract_error_message(pull_result.get('error', 'Unknown error'))
                    self.logger.warning(f"[Tenant-{tenant_id}] Error updating from GitHub: {error_msg}, continuing with local data")
                else:
                    self.logger.info(f"[Tenant-{tenant_id}] Data from GitHub updated")
            
            # Create tenant if it doesn't exist
            sync_tenant_result = await self.action_hub.execute_action('sync_tenant_data', {'tenant_id': tenant_id})
            
            if sync_tenant_result.get('result') != 'success':
                error_obj = sync_tenant_result.get('error', {})
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Error creating/synchronizing tenant: {error_msg}")
                return {"result": "error", "error": error_obj}
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error preparing tenant data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _sync_scenarios_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Synchronize scenarios block through scenario_processor
        """
        try:
            # Call sync_tenant_scenarios action (scenario_processor handles it)
            result = await self.action_hub.execute_action(
                'sync_tenant_scenarios',
                {'tenant_id': tenant_id}
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error synchronizing scenarios: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _sync_bot_block(self, tenant_id: int, bot_name: str) -> Dict[str, Any]:
        """
        Synchronize bot block by bot name (universal method)
        
        Dynamically calls action: sync_{bot_name}_bot
        Examples:
        - bot_name="telegram" → calls sync_telegram_bot
        - bot_name="whatsapp" → calls sync_whatsapp_bot
        """
        try:
            action_name = f"sync_{bot_name}_bot"
            
            self.logger.info(f"[Tenant-{tenant_id}] Synchronizing {bot_name} bot via action: {action_name}")
            
            # Call action dynamically
            result = await self.action_hub.execute_action(
                action_name,
                {'tenant_id': tenant_id}
            )
            
            # not_found is OK - tenant may not have this bot
            if result.get('result') == 'not_found':
                self.logger.info(f"[Tenant-{tenant_id}] No {bot_name} bot configuration to synchronize")
                return {"result": "success"}
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing {bot_name} bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": f"Failed to sync {bot_name} bot: {str(e)}"
                }
            }
    
    async def _sync_storage_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Synchronize storage block through storage_hub
        """
        try:
            # Call sync_tenant_storage action (storage_hub handles it)
            result = await self.action_hub.execute_action(
                'sync_tenant_storage',
                {'tenant_id': tenant_id}
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error synchronizing storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_config_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Synchronize tenant config block (tenant attributes like ai_token)
        Note: config.yaml is optional, updates cache from DB if file not found
        """
        try:
            # Call update_tenant_config action (tenant_hub handles it)
            # Config parsing will be done by tenant_hub action itself
            # For now, just update cache from DB
            await self.tenant_cache.update_tenant_config_cache(tenant_id)
            
            self.logger.info(f"[Tenant-{tenant_id}] Tenant config cache updated")
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant config: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_blocks(self, tenant_id: int, blocks: Dict[str, Any], pull_from_github: bool = False) -> Dict[str, Any]:
        """
        Synchronize specified tenant blocks with optimization
        Delegates to specialized services through Action Hub
        
        blocks structure:
        {
            "bots": ["telegram", "whatsapp"],  # List of bot names to sync
            "scenarios": True/False,
            "storage": True/False,
            "config": True/False
        }
        """
        try:
            bots_to_sync = blocks.get("bots", [])
            scenarios_changed = blocks.get("scenarios", False)
            storage_changed = blocks.get("storage", False)
            config_changed = blocks.get("config", False)
            
            if not bots_to_sync and not scenarios_changed and not storage_changed and not config_changed:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No blocks to synchronize"
                    }
                }
            
            bots_str = ', '.join(bots_to_sync) if bots_to_sync else '-'
            self.logger.info(
                f"Synchronizing tenant [Tenant-{tenant_id}] "
                f"(bots: {bots_str}, scenarios: {'+' if scenarios_changed else '-'}, "
                f"storage: {'+' if storage_changed else '-'}, config: {'+' if config_changed else '-'})..."
            )
            
            # Data preparation (pull + tenant creation) executed once
            prepare_result = await self._prepare_tenant_data(tenant_id, pull_from_github)
            if prepare_result.get("result") != "success":
                error_obj = prepare_result.get("error", {})
                await self.tenant_cache.set_last_failed(tenant_id, error_obj)
                return {"result": "error", "error": error_obj}

            # Synchronize blocks as needed
            # IMPORTANT: First synchronize scenarios, storage and config, then bots (which start polling)
            # This guarantees all data is ready before event processing starts
            
            if scenarios_changed:
                scenarios_result = await self._sync_scenarios_block(tenant_id)
                if scenarios_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, scenarios_result.get("error"))
                    return scenarios_result
            
            if storage_changed:
                storage_result = await self._sync_storage_block(tenant_id)
                if storage_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, storage_result.get("error"))
                    return storage_result
            
            if config_changed:
                config_result = await self._sync_config_block(tenant_id)
                if config_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, config_result.get("error"))
                    return config_result
            
            # Bots synchronization at the end - starts polling/webhooks after all data is ready
            # Sync each bot independently
            for bot_name in bots_to_sync:
                bot_result = await self._sync_bot_block(tenant_id, bot_name)
                if bot_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, bot_result.get("error"))
                    return bot_result
            
            await self.tenant_cache.set_last_updated(tenant_id)
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant blocks {tenant_id}: {e}")
            error_obj = {
                "code": "INTERNAL_ERROR",
                "message": f"Internal error: {str(e)}"
            }
            await self.tenant_cache.set_last_failed(tenant_id, error_obj)
            return {"result": "error", "error": error_obj}
