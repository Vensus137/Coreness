"""
Bot Hub Service - central service for managing all bots
"""

from typing import Any, Dict

from .actions.bot_actions import BotActions
from .actions.message_actions import MessageActions
from .modules.bot_info_manager import BotInfoManager
from .modules.webhook_manager import WebhookManager


class BotHubService:
    """
    Central service for managing all bots
    Integrates various utilities for complete bot management
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.telegram_polling = kwargs['telegram_polling']
        self.telegram_api = kwargs['telegram_api']
        self.database_manager = kwargs['database_manager']
        self.http_server = kwargs.get('http_server')
        self.cache_manager = kwargs['cache_manager']
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('bot_hub')
        
        # Register ourselves in ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('bot_hub', self)
        
        # Initialize submodules
        self.webhook_manager = WebhookManager(self.cache_manager, self.logger, self.settings_manager, self.http_server)
        self.bot_info_manager = BotInfoManager(self.database_manager, self.action_hub, self.telegram_api, self.telegram_polling, self.logger, self.cache_manager, self.settings_manager, self.webhook_manager)
        
        # Initialize actions
        self.bot_actions = BotActions(self.bot_info_manager, self.telegram_polling, self.telegram_api, self.webhook_manager, self.settings_manager, self.logger)
        self.message_actions = MessageActions(self.bot_info_manager, self.telegram_api, self.logger, self.settings)
        
        # Register webhook endpoint (if enabled and available)
        # use_webhooks flag automatically switches in BotActions on initialization
        use_webhooks_setting = self.settings.get('use_webhooks', False)
        
        if use_webhooks_setting and self.http_server:
            self._register_telegram_webhook_endpoint()
            # SSL certificate automatically generated on http_server initialization if external_url is set
        
        # Service state
        self.is_running = False
    
    async def run(self):
        """Main service loop"""
        try:
            self.is_running = True
            self.logger.info("Started")
            
            # Load cache of all bots on startup
            await self.bot_info_manager.load_all_bots_cache()
            
            # Polling starts through Tenant Hub on sync
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
        finally:
            self.is_running = False
    
    # === Actions for ActionHub ===
    
    async def start_bot(self, data: dict) -> Dict[str, Any]:
        """Start bot"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.bot_actions.start_bot(data)
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
            # Validation is done centrally in ActionRegistry
            return await self.bot_actions.stop_bot(data)
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
            # Validation is done centrally in ActionRegistry
            return await self.bot_actions.stop_all_bots(data)
        except Exception as e:
            self.logger.error(f"Error stopping all bots: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_bot_config(self, data: dict) -> Dict[str, Any]:
        """Sync bot configuration: create/update bot + start polling"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.bot_actions.sync_bot_config(data)
        except Exception as e:
            self.logger.error(f"Error syncing bot configuration: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_bot_commands(self, data: dict) -> Dict[str, Any]:
        """Sync bot commands"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.bot_actions.sync_bot_commands(data)
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Error syncing bot commands: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def set_bot_token(self, data: dict) -> Dict[str, Any]:
        """Set bot token through master bot"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.bot_actions.set_bot_token(data)
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
        Sync bot: configuration + commands (wrapper over sync_bot_config + sync_bot_commands)
        """
        try:
            # Validation is done centrally in ActionRegistry
            # 1. Sync bot configuration
            sync_config_result = await self.sync_bot_config(data)
            if sync_config_result.get('result') != 'success':
                return sync_config_result
            
            bot_id = sync_config_result.get('response_data', {}).get('bot_id')
            
            # 2. If commands exist, sync them
            if data.get('bot_commands'):
                sync_commands_result = await self.sync_bot_commands({
                    'bot_id': bot_id,
                    'command_list': data.get('bot_commands', [])
                })
                
                if sync_commands_result.get('result') != 'success':
                    error_msg = sync_commands_result.get('error', 'Unknown error')
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Unknown error')
                    self.logger.warning(f"[Bot-{bot_id}] Error syncing commands: {error_msg}")
                    # Don't return error, as configuration already updated
            
            return sync_config_result
                
        except Exception as e:
            self.logger.error(f"Error syncing bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def send_message(self, data: dict) -> Dict[str, Any]:
        """Send message to bot"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.message_actions.send_message(data)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def delete_message(self, data: dict) -> Dict[str, Any]:
        """Delete bot message"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.message_actions.delete_message(data)
        except Exception as e:
            self.logger.error(f"Error deleting message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def build_keyboard(self, data: dict) -> Dict[str, Any]:
        """Build keyboard from array of IDs using templates"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.message_actions.build_keyboard(data)
        except Exception as e:
            self.logger.error(f"Error building keyboard: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def answer_callback_query(self, data: dict) -> Dict[str, Any]:
        """Answer callback query (popup notification or simple notification)"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.message_actions.answer_callback_query(data)
        except Exception as e:
            self.logger.error(f"Error answering callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_telegram_bot_info(self, data: dict) -> Dict[str, Any]:
        """Get bot information through Telegram API (with caching)"""
        try:
            # Validation is done centrally in ActionRegistry
            bot_token = data.get('bot_token', 'unknown')
            return await self.bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        except Exception as e:
            bot_token = data.get('bot_token', '')
            # Format token for logs: first 15 characters
            if bot_token:
                token_info = f"[Bot-Token: {bot_token[:15]}...]"
            else:
                token_info = "[Bot-Token: unknown]"
            self.logger.error(f"{token_info} Error getting bot information: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_bot_status(self, data: dict) -> Dict[str, Any]:
        """Get bot polling status"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.bot_info_manager.get_bot_status(data)
        except Exception as e:
            self.logger.error(f"Error getting bot status: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_bot_info(self, data: dict) -> Dict[str, Any]:
        """Get bot information from database (with caching)"""
        try:
            # Validation is done centrally in ActionRegistry
            bot_id = data.get('bot_id')
            force_refresh = data.get('force_refresh', False)
            
            # Get bot information from DB (with caching)
            # BotInfoManager.get_bot_info() already returns universal structure
            return await self.bot_info_manager.get_bot_info(bot_id, force_refresh)
            
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Error getting bot information: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    # === Webhook management methods ===
    
    def _register_telegram_webhook_endpoint(self):
        """Register endpoint for Telegram webhook (called on initialization)"""
        try:
            from .handlers.telegram_webhook import TelegramWebhookHandler
            
            if not self.http_server:
                self.logger.error("http_server not found, failed to register Telegram webhook endpoint")
                return
            
            # Get endpoint path from settings
            webhook_endpoint = self.settings.get('webhook_endpoint', '/webhooks/telegram')
            
            # Create handler
            handler_instance = TelegramWebhookHandler(
                self.webhook_manager,
                self.action_hub,
                self.logger
            )
            
            # Register endpoint (synchronously, on initialization)
            success = self.http_server.register_endpoint(
                'POST',
                webhook_endpoint,
                handler_instance.handle
            )
            
            if success:
                self.logger.info(f"Telegram webhook endpoint registered on {webhook_endpoint}")
            else:
                self.logger.error(f"Failed to register Telegram webhook endpoint on {webhook_endpoint}")
                
        except Exception as e:
            self.logger.error(f"Error registering Telegram webhook endpoint: {e}")
    
