"""
TelegramAPI - utility for working with Telegram Bot API
"""

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp


class TelegramAPI:
    """Utility for working with Telegram Bot API"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Settings
        settings = self.settings_manager.get_plugin_settings("telegram_api")
        self.request_timeout = settings.get('request_timeout', 30)
        self.connection_pool_limit = settings.get('connection_pool_limit', 100)
        self.connection_pool_limit_per_host = settings.get('connection_pool_limit_per_host', 50)
        self.dns_cache_ttl = settings.get('dns_cache_ttl', 300)
        self.keepalive_timeout = settings.get('keepalive_timeout', 30)
        self.connect_timeout = settings.get('connect_timeout', 10)
        self.sock_read_timeout = settings.get('sock_read_timeout', 30)
        
        # Get shutdown_timeout from global settings
        global_settings = self.settings_manager.get_global_settings()
        shutdown_settings = global_settings.get('shutdown', {})
        self.shutdown_timeout = shutdown_settings.get('plugin_timeout', 3.0)
        
        # HTTP client
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Components
        from .actions.bot_info_action import BotInfoAction
        from .actions.callback_action import CallbackAction
        from .actions.chat_action import ChatAction
        from .actions.command_action import CommandAction
        from .actions.invoice_action import InvoiceAction
        from .actions.message_action import MessageAction
        from .core.api_client import APIClient
        from .core.rate_limiter import RateLimiter
        from .utils.attachment_handler import AttachmentHandler
        from .utils.button_mapper import ButtonMapper
        
        # Initialize service immediately
        self._initialize_service()
        
        # Create components after initialization
        self.rate_limiter = RateLimiter(settings, **kwargs)
        self.api_client = APIClient(self.session, self.rate_limiter, **kwargs)
        
        # Create utilities
        self.button_mapper = ButtonMapper(**kwargs)
        self.attachment_handler = AttachmentHandler(api_client=self.api_client, **kwargs)
        
        # Create actions
        self.command_action = CommandAction(self.api_client, **kwargs)
        self.message_action = MessageAction(
            api_client=self.api_client,
            button_mapper=self.button_mapper,
            attachment_handler=self.attachment_handler,
            **kwargs
        )
        self.bot_info_action = BotInfoAction(self.api_client, **kwargs)
        self.invoice_action = InvoiceAction(self.api_client, **kwargs)
        self.callback_action = CallbackAction(self.api_client, **kwargs)
        self.chat_action = ChatAction(self.api_client, **kwargs)
    
    def _initialize_service(self):
        """Private service initialization"""
        try:
            # Create HTTP session with optimized connection pool
            connector = aiohttp.TCPConnector(
                limit=self.connection_pool_limit,              # Total connection limit
                limit_per_host=self.connection_pool_limit_per_host,  # Limit for api.telegram.org
                ttl_dns_cache=self.dns_cache_ttl,              # DNS cache
                use_dns_cache=True,                            # Enable DNS cache
                keepalive_timeout=self.keepalive_timeout,      # Keep-alive timeout
                enable_cleanup_closed=True                     # Auto-cleanup closed connections
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=self.request_timeout,
                    connect=self.connect_timeout,
                    sock_read=self.sock_read_timeout
                ),
                headers={
                    'User-Agent': 'TelegramAPI/1.0',
                    'Connection': 'keep-alive'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            # Close session if it was created
            if hasattr(self, 'session') and self.session:
                # Close session synchronously
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.session.close())
                    else:
                        loop.run_until_complete(self.session.close())
                except Exception:
                    pass  # Ignore errors when closing in case of initialization error
            raise
    
    def cleanup(self):
        """Synchronous resource cleanup"""
        try:
            if self.session:
                # Close session synchronously
                import asyncio
                try:
                    # Try to close session in existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If loop is running, create task for closing
                        loop.create_task(self.session.close())
                    else:
                        # If loop is not running, run it for closing
                        loop.run_until_complete(self.session.close())
                except RuntimeError:
                    # If no event loop, create new one
                    asyncio.run(self.session.close())
                except Exception as e:
                    self.logger.warning(f"Error closing session: {e}")
                
                self.session = None

            self.rate_limiter.cleanup()

            self.logger.info("TelegramAPI utility cleaned up")
            return True

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            return False
    
    def shutdown(self):
        """Synchronous graceful shutdown of utility"""
        if not self.session or self.session.closed:
            return


        async def _close():
            try:
                await asyncio.wait_for(self.session.close(), timeout=self.shutdown_timeout)
            except asyncio.TimeoutError:
                # On timeout close connector forcibly
                if hasattr(self.session, '_connector'):
                    self.session._connector.close()
            except Exception:
                # Just in case close connector on any unexpected errors
                if hasattr(self.session, '_connector'):
                    self.session._connector.close()

        try:
            # If event loop is already running (pytest-asyncio, production runtime) —
            # just create task for closing in existing loop
            loop = asyncio.get_running_loop()
            loop.create_task(_close())
        except RuntimeError:
            # No active loop — can safely block
            asyncio.run(_close())

        self.session = None

    # === Methods for working with commands ===
    
    async def sync_bot_commands(self, bot_token: str, bot_id: int, command_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync bot commands: apply commands in Telegram"""
        try:
            # Delegate execution to command_action
            result = await self.command_action.sync_bot_commands(bot_token, bot_id, command_list)
            
            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error syncing commands: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Methods for working with bot information ===
    
    def _format_token_for_logs(self, bot_token: str) -> str:
        """
        Format token for logs: first 15 characters
        Token format: {bot_id}:{secret}, where bot_id can be extracted from the beginning
        """
        if not bot_token:
            return "[Bot-Token: unknown]"
        
        # Take first 15 characters (usually bot_id + part of secret)
        return f"[Bot-Token: {bot_token[:15]}...]"
    
    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """Get bot information via Telegram API"""
        try:
            # Delegate execution to bot_info_action
            result = await self.bot_info_action.get_bot_info(bot_token)
            
            return result
            
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Error getting bot information: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Methods for working with messages ===
    
    async def send_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Send message via API"""
        try:
            # Delegate execution to message_action
            result = await self.message_action.send_message(bot_token, bot_id, data)

            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error sending message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

    async def delete_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Delete message via API"""
        try:
            # Delegate execution to message_action
            result = await self.message_action.delete_message(bot_token, bot_id, data)

            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error deleting message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Methods for working with callback query ===
    
    async def answer_callback_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Answer callback query via API"""
        try:
            # Delegate execution to callback_action
            result = await self.callback_action.answer_callback_query(bot_token, bot_id, data)

            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error answering callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

    # === Methods for chat member restrictions ===

    async def restrict_chat_member(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Restrict a user in a supergroup (simplified permission groups)."""
        try:
            result = await self.chat_action.restrict_chat_member(bot_token, bot_id, data)
            return result
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error restricting chat member: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }

    # === Methods for working with invoices ===
    
    async def send_invoice(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Send invoice via API"""
        try:
            # Delegate execution to invoice_action
            result = await self.invoice_action.send_invoice(bot_token, bot_id, data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error sending invoice: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def create_invoice_link(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Create invoice link via API"""
        try:
            # Delegate execution to invoice_action
            result = await self.invoice_action.create_invoice_link(bot_token, bot_id, data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error creating invoice link: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def answer_pre_checkout_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Answer payment confirmation request via API"""
        try:
            # Delegate execution to invoice_action
            result = await self.invoice_action.answer_pre_checkout_query(bot_token, bot_id, data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error answering pre_checkout_query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    
