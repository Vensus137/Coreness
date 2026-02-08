"""
Tenant Hub - service for managing tenant configurations
Coordinator for loading tenant data through specialized services
"""

from typing import Any, Dict

from .actions.sync_actions import SyncActions
from .actions.tenant_actions import TenantActions
from .actions.webhook_actions import WebhookActions
from .core_sync.block_sync_executor import BlockSyncExecutor
from .core_sync.sync_orchestrator import SyncOrchestrator
from .domain.tenant_cache import TenantCache
from .domain.tenant_repository import TenantRepository
from .github_sync.github_sync import GitHubSync


class TenantHub:
    """
    Orchestrator service for tenant management
    
    Responsibilities:
    - GitHub synchronization (webhooks/polling)
    - Determines which blocks changed (scenarios, storage, bots, config)
    - Delegates sync to specialized services via Action Hub:
      * scenario_processor (sync_tenant_scenarios)
      * storage_hub (sync_tenant_storage)
      * telegram_bot_manager (sync_telegram_bot)
    
    Does NOT know internal structure of tenant configs (YAML parsing)
    Does NOT manage storage/scenarios/bots directly
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
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
        
        # Create tenant repository
        self.tenant_repository = TenantRepository(self.database_manager, self.logger)
        
        # Create tenant cache
        self.tenant_cache = TenantCache(self.database_manager, self.logger, self.datetime_formatter, kwargs['cache_manager'], self.settings_manager)
        
        # Create tenants folder (once on initialization)
        self._ensure_tenants_directory_exists()
        
        # Create GitHub sync modules (unified)
        self.github_sync = GitHubSync(self.logger, self.settings_manager)
        
        # Create block sync executor (simplified - uses Action Hub)
        self.block_sync_executor = BlockSyncExecutor(
            self.logger,
            self.action_hub,
            self.github_sync,
            self.settings_manager,
            self.tenant_cache
        )
        
        # Create sync orchestrator
        self.sync_orchestrator = SyncOrchestrator(
            self.logger,
            self.github_sync,
            self.github_sync,
            self.block_sync_executor,
            self.settings_manager,
            self.task_manager
        )
        
        # Create action handlers
        self.sync_actions = SyncActions(
            self.logger,
            self.sync_orchestrator,
            self.block_sync_executor
        )
        
        self.tenant_actions = TenantActions(
            self.logger,
            self.action_hub,
            self.database_manager,
            self.tenant_cache,
            self.tenant_repository,
            self.max_system_tenant_id
        )
        
        self.webhook_actions = WebhookActions(
            self.logger,
            self.github_sync,
            self.block_sync_executor
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
        """Sync tenant configuration with database"""
        return await self.sync_actions.sync_tenant(data, pull_from_github)
    
    async def sync_all_tenants(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync all tenants: system (locally) + public (from GitHub)"""
        return await self.sync_actions.sync_all_tenants(data)
    
    async def sync_tenant_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync tenant data: create/update tenant"""
        return await self.tenant_actions.sync_tenant_data(data)
    
    async def sync_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync tenant config: pull from GitHub + parsing + sync"""
        return await self.sync_actions.sync_tenant_config(data)
    
    async def sync_tenants_from_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sync tenants from list of changed files (universal method for webhooks and polling)"""
        return await self.webhook_actions.sync_tenants_from_files(data)
    
    async def get_tenant_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get tenant status"""
        return await self.tenant_actions.get_tenant_status(data)
    
    async def get_tenants_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of all tenant IDs with separation into public and system"""
        return await self.tenant_actions.get_tenants_list(data)
    
    async def update_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update tenant config"""
        return await self.tenant_actions.update_tenant_config(data)