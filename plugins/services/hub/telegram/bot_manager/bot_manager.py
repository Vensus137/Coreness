"""
Telegram Bot Manager - service for managing Telegram bot lifecycle
Handles bot configuration sync, creation, start/stop, webhook/polling management
"""

from typing import Any, Dict

from .modules.bot_repository import BotRepository
from .modules.bot_lifecycle import BotLifecycle
from .modules.webhook_manager import WebhookManager
from .parsers.telegram_parser import TelegramBotParser


class TelegramBotManager:
    """
    Service for managing Telegram bot lifecycle and configuration
    - Syncs bots from YAML configs (bots/telegram.yaml)
    - Creates/updates bots in database
    - Starts/stops bots via polling OR webhooks
    - Manages bot commands
    - Provides bot information and status
    
    Supports two modes:
    - Polling mode: uses telegram_polling utility
    - Webhook mode: registers webhooks via Telegram API
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('telegram_bot_manager')
        
        # Initialize repository (handles DB + cache + Telegram API info)
        self.repository = BotRepository(
            database_manager=kwargs['database_manager'],
            cache_manager=kwargs['cache_manager'],
            telegram_api=kwargs['telegram_api'],
            settings_manager=self.settings_manager,
            logger=self.logger
        )
        
        # Initialize webhook manager (optional, for webhook mode)
        self.webhook_manager = None
        http_server = kwargs.get('http_server')
        if http_server:
            self.webhook_manager = WebhookManager(
                cache_manager=kwargs['cache_manager'],
                http_server=http_server,
                settings_manager=self.settings_manager,
                logger=self.logger
            )
        
        # Initialize lifecycle manager (handles start/stop logic)
        self.lifecycle = BotLifecycle(
            repository=self.repository,
            telegram_polling=kwargs['telegram_polling'],
            webhook_manager=self.webhook_manager,
            telegram_api=kwargs['telegram_api'],
            settings_manager=self.settings_manager,
            logger=self.logger
        )
        
        # Initialize config parser
        self.parser = TelegramBotParser(
            logger=self.logger,
            settings_manager=self.settings_manager
        )
        
        # Register in ActionHub
        self.action_hub.register('telegram_bot_manager', self)
        
        # Register webhook endpoint if using webhook mode
        use_webhooks = self.settings.get('use_webhooks', False)
        if use_webhooks and self.webhook_manager and http_server:
            self._register_webhook_endpoint(http_server)
        
        self.is_running = False
    
    async def run(self):
        """Service startup - load bot cache"""
        try:
            self.is_running = True
            self.logger.info("Started")
            
            # Preload all bots into cache
            await self.repository.load_all_bots_cache()
            
        except Exception as e:
            self.logger.error(f"Error in startup: {e}")
        finally:
            self.is_running = False
    
    # === Actions for ActionHub ===
    
    async def sync_telegram_bot(self, data: dict) -> Dict[str, Any]:
        """
        Synchronize Telegram bot for tenant from YAML config
        Called by tenant_hub when bots/telegram.yaml changes
        
        Flow: Parse YAML → Create/Update bot → Sync commands → Start bot
        """
        try:
            tenant_id = data['tenant_id']
            
            # Parse bots/telegram.yaml
            bot_config = await self.parser.parse_bot_config(tenant_id)
            
            if not bot_config:
                self.logger.warning(f"[Tenant-{tenant_id}] telegram.yaml not found")
                return {"result": "not_found"}
            
            # Sync bot configuration
            sync_result = await self.sync_bot_config({
                'tenant_id': tenant_id,
                'bot_token': bot_config.get('bot_token'),
                'is_active': bot_config.get('is_active', True)
            })
            
            if sync_result['result'] != 'success':
                return sync_result
            
            bot_id = sync_result['response_data']['bot_id']
            
            # Sync commands if present
            commands = bot_config.get('commands', [])
            if commands:
                command_list = [
                    {
                        "action_type": "register",
                        "command": cmd['command'],
                        "description": cmd['description'],
                        "scope": cmd.get('scope', 'default')
                    }
                    for cmd in commands
                ]
                
                commands_result = await self.sync_bot_commands({
                    'bot_id': bot_id,
                    'command_list': command_list
                })
                
                if commands_result['result'] != 'success':
                    self.logger.warning(f"[Bot-{bot_id}] Error syncing commands")
            
            self.logger.info(f"[Tenant-{tenant_id}] Bot {bot_id} synchronized")
            return sync_result
            
        except Exception as e:
            tenant_id = data.get('tenant_id', 'unknown')
            self.logger.error(f"[Tenant-{tenant_id}] Error syncing bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_bot_config(self, data: dict) -> Dict[str, Any]:
        """Create/update bot and start if active"""
        try:
            return await self.lifecycle.sync_config(data)
        except Exception as e:
            self.logger.error(f"Error syncing bot config: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def start_bot(self, data: dict) -> Dict[str, Any]:
        """Start bot (polling or webhook)"""
        try:
            return await self.lifecycle.start_bot(data['bot_id'])
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def stop_bot(self, data: dict) -> Dict[str, Any]:
        """Stop bot"""
        try:
            return await self.lifecycle.stop_bot(data['bot_id'])
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def stop_all_bots(self, data: dict) -> Dict[str, Any]:
        """Stop all bots"""
        try:
            return await self.lifecycle.stop_all_bots()
        except Exception as e:
            self.logger.error(f"Error stopping all bots: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_bot_commands(self, data: dict) -> Dict[str, Any]:
        """Sync bot commands to Telegram"""
        try:
            return await self.repository.sync_bot_commands(
                data['bot_id'],
                data['command_list']
            )
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Error syncing commands: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def set_bot_token(self, data: dict) -> Dict[str, Any]:
        """Set/update bot token"""
        try:
            return await self.lifecycle.set_bot_token(data)
        except Exception as e:
            self.logger.error(f"Error setting bot token: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_bot(self, data: dict) -> Dict[str, Any]:
        """
        Sync bot: config + commands
        Wrapper over sync_bot_config + sync_bot_commands
        """
        try:
            # Sync config first
            config_result = await self.sync_bot_config(data)
            if config_result['result'] != 'success':
                return config_result
            
            bot_id = config_result['response_data']['bot_id']
            
            # Sync commands if provided
            if data.get('bot_commands'):
                commands_result = await self.sync_bot_commands({
                    'bot_id': bot_id,
                    'command_list': data['bot_commands']
                })
                
                if commands_result['result'] != 'success':
                    self.logger.warning(f"[Bot-{bot_id}] Commands sync failed")
            
            return config_result
            
        except Exception as e:
            self.logger.error(f"Error syncing bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_bot_info(self, data: dict) -> Dict[str, Any]:
        """Get bot information from DB (with caching)"""
        try:
            return await self.repository.get_bot_info(
                data['bot_id'],
                data.get('force_refresh', False)
            )
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Error getting bot info: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_bot_status(self, data: dict) -> Dict[str, Any]:
        """Get bot status (polling/webhook, active/inactive)"""
        try:
            return await self.lifecycle.get_bot_status(data['bot_id'])
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Error getting bot status: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_telegram_bot_info(self, data: dict) -> Dict[str, Any]:
        """Get bot info from Telegram API (with caching)"""
        try:
            return await self.repository.get_telegram_bot_info_by_token(data['bot_token'])
        except Exception as e:
            self.logger.error(f"Error getting Telegram bot info: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    # === Private methods ===
    
    def _register_webhook_endpoint(self, http_server):
        """Register HTTP endpoint for receiving Telegram webhooks"""
        try:
            from .handlers.telegram_webhook import TelegramWebhookHandler
            
            endpoint = self.settings.get('webhook_endpoint', '/webhooks/telegram')
            
            handler = TelegramWebhookHandler(
                webhook_manager=self.webhook_manager,
                action_hub=self.action_hub,
                logger=self.logger
            )
            
            if http_server.register_endpoint('POST', endpoint, handler.handle):
                self.logger.info(f"Webhook endpoint registered: {endpoint}")
            else:
                self.logger.error(f"Failed to register webhook endpoint: {endpoint}")
                
        except Exception as e:
            self.logger.error(f"Error registering webhook endpoint: {e}")
