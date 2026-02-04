"""
Tenant Hub - service for managing tenant configurations
Coordinator for loading tenant data through specialized services
"""

from typing import Any, Dict

from .core_sync.block_sync_executor import BlockSyncExecutor
from .core_sync.sync_orchestrator import SyncOrchestrator
from .github_sync.base import GitHubSyncBase
from .github_sync.smart_sync import SmartGitHubSync
from .storage.storage_manager import StorageManager
from .utils.tenant_cache import TenantCache
from .utils.tenant_data_manager import TenantDataManager
from .utils.tenant_parser import TenantParser


class TenantHub:
    """
    Service for managing tenant configurations
    - Coordinates tenant data loading
    - Delegates loading of specific parts to specialized services
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        self.condition_parser = kwargs['condition_parser']
        self.task_manager = kwargs['task_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.http_server = kwargs.get('http_server')
        
        # Get max system tenant ID from global settings
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 99)
        
        # Webhook settings
        plugin_settings = self.settings_manager.get_plugin_settings('tenant_hub')
        use_webhooks_setting = plugin_settings.get('use_webhooks', False)
        
        # Automatically switch to polling if webhooks unavailable
        self.use_webhooks = use_webhooks_setting and self.http_server is not None
        
        if use_webhooks_setting and not self.use_webhooks:
            self.logger.warning("GitHub webhooks enabled in settings, but http_server unavailable - automatically using polling")
        
        self.github_webhook_secret = plugin_settings.get('github_webhook_secret', '')
        self.github_webhook_endpoint = plugin_settings.get('github_webhook_endpoint', '/webhooks/github')
        
        # Register GitHub webhook endpoint (if webhooks enabled and available)
        if self.use_webhooks:
            self._register_github_webhook_endpoint()
        
        # Create tenant data manager
        self.tenant_data_manager = TenantDataManager(self.database_manager, self.logger)
        
        # Create tenant cache
        self.tenant_cache = TenantCache(self.database_manager, self.logger, self.datetime_formatter, kwargs['cache_manager'], self.settings_manager)
        
        # Create tenants folder (once on initialization)
        self._ensure_tenants_directory_exists()
        
        # Create submodules
        self.tenant_parser = TenantParser(self.logger, self.settings_manager, self.condition_parser)
        
        # Create tenant storage manager
        self.storage_manager = StorageManager(
            self.database_manager,
            self.logger,
            self.tenant_parser,
            self.settings_manager
        )
        self.github_sync = GitHubSyncBase(self.logger, self.settings_manager)
        self.smart_github_sync = SmartGitHubSync(self.logger, self.settings_manager)
        
        # Create block sync executor
        self.block_sync_executor = BlockSyncExecutor(
            self.logger,
            self.tenant_parser,
            self.action_hub,
            self.github_sync,
            self.settings_manager,
            self.tenant_cache,
            self.storage_manager
        )
        
        # Create sync orchestrator
        self.sync_orchestrator = SyncOrchestrator(
            self.logger,
            self.smart_github_sync,
            self.github_sync,
            self.block_sync_executor,
            self.settings_manager,
            self.task_manager
        )
        
        # Register ourselves in ActionHub
        self.action_hub.register('tenant_hub', self)
    
    def _ensure_tenants_directory_exists(self):
        """Create tenants folder if it doesn't exist"""
        try:
            from pathlib import Path
            global_settings = self.settings_manager.get_global_settings()
            tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
            project_root = self.settings_manager.get_project_root()
            self.tenants_path = Path(project_root) / tenants_config_path
            
            if not self.tenants_path.exists():
                self.tenants_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created tenants folder: {self.tenants_path}")
                
        except Exception as e:
            self.logger.error(f"Error creating tenants folder: {e}")
    
    async def run(self):
        """Main service loop with regular background synchronization"""
        try:
            import asyncio
            
            # Get sync settings
            plugin_settings = self.settings_manager.get_plugin_settings("tenant_hub")
            sync_interval = plugin_settings.get('sync_interval', 60)
            
            # First sync on startup (execute directly, not through queue)
            # Sync all tenants (system locally + public from GitHub)
            self.logger.info("Initial synchronization of all tenants...")
            await self.sync_all_tenants({})
            
            # If webhooks enabled - endpoint already registered on initialization
            # Server will start through http_api_service (if available)
            if self.use_webhooks:
                if self.http_server:
                    self.logger.info("Webhooks enabled, endpoint registered, server will start through http_api_service")
                    # Service exits - HTTP server runs in background, events processed through webhooks
                    return
                else:
                    self.logger.warning("Webhooks enabled, but http_server unavailable - using polling as fallback")
            
            # If webhooks disabled - work as before (polling)
            # If interval = 0, auto-sync disabled
            if sync_interval <= 0:
                self.logger.info("Automatic synchronization disabled (sync_interval = 0)")
                return
            
            # Regular sync loop - send tasks in background
            self.logger.info(f"Background update loop started (interval: {sync_interval} sec)")
            
            while True:
                await asyncio.sleep(sync_interval)
                
                # Sequential check and update of public tenants without background task
                try:
                    await self.sync_orchestrator.sync_public_tenants()
                except Exception as e:
                    self.logger.error(f"Error in background sync of public tenants: {e}")
                    
        except asyncio.CancelledError:
            self.logger.info("Sync loop interrupted")
            raise
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            raise
    
    # === Webhook management methods ===
    
    def _register_github_webhook_endpoint(self):
        """Register endpoint for GitHub webhook (called on initialization)"""
        try:
            from .handlers.github_webhook import GitHubWebhookHandler
            
            if not self.http_server:
                self.logger.warning("http_server not found, failed to register GitHub webhook endpoint")
                return
            
            # Check secret presence
            if not self.github_webhook_secret:
                self.logger.warning("GitHub webhook secret not set, webhooks may be insecure")
            
            # Create handler
            handler_instance = GitHubWebhookHandler(
                self.action_hub,
                self.github_webhook_secret,
                self.logger
            )
            
            # Register endpoint (synchronously, on initialization)
            success = self.http_server.register_endpoint(
                'POST',
                self.github_webhook_endpoint,
                handler_instance.handle
            )
            
            if success:
                self.logger.info(f"GitHub webhook endpoint registered on {self.github_webhook_endpoint}")
            else:
                self.logger.error("Failed to register GitHub webhook endpoint")
                
        except Exception as e:
            self.logger.error(f"Error registering GitHub webhook endpoint: {e}")
            
    # === Actions for ActionHub ===
    
    async def sync_tenant(self, data: Dict[str, Any], pull_from_github: bool = True) -> Dict[str, Any]:
        """
        Sync tenant configuration with database
        By default updates data from GitHub before sync
        Delegates execution to sync orchestrator
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Use orchestrator to sync tenant (both blocks)
            return await self.sync_orchestrator.sync_tenant(tenant_id, pull_from_github)
                
        except Exception as e:
            self.logger.error(f"Error syncing tenant: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_all_tenants(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync all tenants: system (locally) + public (from GitHub)
        Delegates execution to sync orchestrator
        """
        try:
            # Validation is done centrally in ActionRegistry
            return await self.sync_orchestrator.sync_all_tenants()
        except Exception as e:
            self.logger.error(f"Error syncing all tenants: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_tenant_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync tenant data: create/update tenant"""
        try:
            # Validation is done centrally in ActionRegistry
            # Use TenantDataManager to sync tenant data
            # Pass data directly, as it already contains all tenant data
            return await self.tenant_data_manager.sync_tenant_data(data)
                
        except Exception as e:
            self.logger.error(f"Error syncing tenant data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_tenant_scenarios(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenant scenarios: pull from GitHub + parsing + sync
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Single entry point: sync only scenarios
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": False, "scenarios": True, "storage": False, "config": False},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"Error syncing scenarios: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_tenant_bot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenant bot: pull from GitHub + parsing + sync
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Single entry point: sync only bot
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": True, "scenarios": False, "storage": False, "config": False},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"Error syncing bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_tenant_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenant storage: pull from GitHub + parsing + sync
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Single entry point: sync only storage
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": False, "scenarios": False, "storage": True, "config": False},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error syncing storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenant config: pull from GitHub + parsing + sync
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Single entry point: sync only config
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": False, "scenarios": False, "storage": False, "config": True},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error syncing config: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
            
    async def sync_tenants_from_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync tenants from list of changed files (universal method for webhooks and polling)
        Accepts file list in format [{"filename": "path"}, ...] or ["path1", "path2", ...]
        """
        try:
            # Validation is done centrally in ActionRegistry
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
            
            # Use existing logic from smart_sync for parsing
            changed_tenants = self.smart_github_sync._extract_tenant_changes_with_protection(normalized_files)
            
            if not changed_tenants:
                self.logger.info("No changed tenants in file list")
                return {"result": "success", "response_data": {"synced_tenants": 0}}
            
            # Sync each changed tenant
            self.logger.info(f"Changes detected in {len(changed_tenants)} tenants")
            synced_count = 0
            errors = []
            
            for tenant_id, blocks in changed_tenants.items():
                try:
                    blocks_str = f"(bot: {'+' if blocks.get('bot') else '-'}, scenarios: {'+' if blocks.get('scenarios') else '-'}, storage: {'+' if blocks.get('storage') else '-'}, config: {'+' if blocks.get('config') else '-'})"
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
            
        except Exception as e:
            self.logger.error(f"Error syncing tenants from files: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_tenant_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get tenant status:
        - bot_is_active, bot_is_polling, bot_is_webhook_active, bot_is_working (via bot_hub)
        - last_updated_at, last_failed_at, last_error (from TenantCache)
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Get bot_id for tenant
            bot_id = await self.tenant_cache.get_bot_id_by_tenant_id(tenant_id)
            
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot for tenant {tenant_id} not found"
                    }
                }
            
            # Get bot status via bot_hub
            bot_status = await self.action_hub.execute_action('get_bot_status', {'bot_id': bot_id})
            
            if bot_status.get('result') != 'success':
                return bot_status
            
            # Rename fields for clarity and add cache metadata
            response_data = bot_status.get('response_data', {})
            cache_meta = await self.tenant_cache.get_tenant_cache(tenant_id)

            return {
                "result": "success",
                "response_data": {
                    "bot_is_active": response_data.get('is_active'),
                    "bot_is_polling": response_data.get('is_polling'),
                    "bot_is_webhook_active": response_data.get('is_webhook_active'),
                    "bot_is_working": response_data.get('is_working'),
                    "last_updated_at": cache_meta.get('last_updated_at'),
                    "last_failed_at": cache_meta.get('last_failed_at'),
                    "last_error": cache_meta.get('last_error')
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting tenant status: {e}")
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
    
    async def get_tenants_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of all tenant IDs with separation into public and system
        """
        try:
            # Validation is done centrally in ActionRegistry
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
                
        except Exception as e:
            self.logger.error(f"Error getting tenant list: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def update_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update tenant config
        Updates only provided fields, leaves others untouched
        """
        try:
            # Validation is done centrally in ActionRegistry
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
            
        except Exception as e:
            self.logger.error(f"Error updating tenant attributes: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }