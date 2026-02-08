"""
Bot Lifecycle Manager - handles bot start/stop logic
Supports both polling and webhook modes with proper switching logic
"""

from typing import Any, Dict, Optional


class BotLifecycle:
    """
    Manages bot lifecycle: start, stop, mode switching
    
    Modes:
    - Polling: bot receives updates via long-polling (telegram_polling utility)
    - Webhook: bot receives updates via HTTP webhooks (webhook_manager)
    
    Important: The service supports ONLY ONE mode at a time (global setting).
    When mode changes, all bots must be restarted.
    """
    
    def __init__(self, repository, telegram_polling, webhook_manager, telegram_api, settings_manager, logger):
        self.repository = repository
        self.telegram_polling = telegram_polling
        self.webhook_manager = webhook_manager
        self.telegram_api = telegram_api
        self.logger = logger
        
        # Determine mode from settings
        bot_manager_settings = settings_manager.get_plugin_settings("telegram_bot_manager")
        use_webhooks_setting = bot_manager_settings.get('use_webhooks', False)
        
        # Auto-fallback to polling if webhooks unavailable
        self.use_webhooks = use_webhooks_setting and webhook_manager is not None
        
        if use_webhooks_setting and not self.use_webhooks:
            self.logger.warning(
                "Webhooks enabled in settings but http_server unavailable - "
                "falling back to polling mode"
            )
        
        mode = "webhook" if self.use_webhooks else "polling"
        self.logger.info(f"Bot lifecycle mode: {mode}")
    
    async def sync_config(self, data: dict) -> Dict[str, Any]:
        """
        Sync bot configuration: create/update + conditional restart
        
        Smart restart logic:
        - Always restart if bot created for first time
        - Restart only if critical fields changed (token, is_active)
        - For webhooks: always re-set webhook on sync (idempotent operation)
        - For polling: restart only if not running or config changed
        """
        try:
            tenant_id = data['tenant_id']
            new_bot_token = data.get('bot_token')
            new_is_active = data.get('is_active', True)
            
            # Get old bot data BEFORE update
            old_bot_data = None
            old_bot_id = None
            bot_result = await self.repository.get_bot_info_by_tenant_id(tenant_id)
            if bot_result['result'] == 'success':
                old_bot_data = bot_result['response_data']
                old_bot_id = old_bot_data.get('bot_id')
            
            # Create or update bot
            create_result = await self.repository.create_or_update_bot(data)
            if create_result['result'] != 'success':
                return create_result
            
            bot_id = create_result['response_data']['bot_id']
            action = create_result['response_data']['action']
            
            # Determine if restart needed
            should_restart = self._should_restart_bot(
                action=action,
                old_bot_data=old_bot_data,
                old_bot_id=old_bot_id,
                bot_id=bot_id,
                new_bot_token=new_bot_token,
                new_is_active=new_is_active
            )
            
            # Restart if needed: use token from config, or from DB when config has no token (security: token only in DB / set via master bot)
            if should_restart:
                effective_token = new_bot_token
                if effective_token is None:
                    bot_info = await self.repository.get_bot_info(bot_id)
                    if bot_info.get('result') == 'success':
                        effective_token = bot_info['response_data'].get('bot_token')
                await self._restart_bot(bot_id, effective_token, new_is_active)
            
            return {
                "result": "success",
                "response_data": {"bot_id": bot_id, "action": action}
            }
            
        except Exception as e:
            self.logger.error(f"Error syncing config: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def start_bot(self, bot_id: int) -> Dict[str, Any]:
        """Start bot (polling or webhook depending on mode)"""
        try:
            # Get bot info
            bot_result = await self.repository.get_bot_info(bot_id)
            if bot_result['result'] != 'success':
                return bot_result
            
            bot_info = bot_result['response_data']
            bot_token = bot_info.get('bot_token')
            
            if not bot_token:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot {bot_id} token not found"
                    }
                }
            
            # Start based on mode
            if self.use_webhooks:
                result = await self.webhook_manager.set_webhook(bot_id, bot_token)
                return result if result['result'] == 'success' else result
            else:
                success = await self.telegram_polling.start_bot_polling(bot_id, bot_token)
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Failed to start polling for bot {bot_id}"
                        }
                    }
                    
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error starting bot: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def stop_bot(self, bot_id: int) -> Dict[str, Any]:
        """Stop bot"""
        try:
            # Get bot info to get token (needed for webhook deletion)
            bot_result = await self.repository.get_bot_info(bot_id)
            bot_token = None
            if bot_result['result'] == 'success':
                bot_token = bot_result['response_data'].get('bot_token')
            
            # Stop based on mode
            if self.use_webhooks:
                if bot_token:
                    return await self.webhook_manager.delete_webhook(bot_token, bot_id)
                else:
                    return {"result": "success"}  # No token, nothing to delete
            else:
                success = await self.telegram_polling.stop_bot_polling(bot_id)
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Failed to stop bot {bot_id}"
                        }
                    }
                    
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error stopping bot: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def get_bot_status(self, bot_id: int) -> Dict[str, Any]:
        """
        Get bot status: is it running via polling or webhook?
        
        Returns:
        - is_active: from database (config flag)
        - is_polling: whether polling is active
        - is_webhook_active: whether webhook is set
        - is_working: overall status (polling OR webhook)
        """
        try:
            # Get bot info from cache/DB
            bot_result = await self.repository.get_bot_info(bot_id)
            if bot_result['result'] != 'success':
                return bot_result
            
            bot_info = bot_result['response_data']
            is_active = bot_info.get('is_active')
            bot_token = bot_info.get('bot_token')
            
            # Check polling status
            is_polling = self.telegram_polling.is_bot_polling(bot_id)
            
            # Check webhook status (if token exists)
            is_webhook_active = False
            if bot_token and self.webhook_manager:
                try:
                    webhook_info = await self.webhook_manager.get_webhook_info(bot_token, bot_id)
                    if webhook_info.get('result') == 'success':
                        is_webhook_active = webhook_info['response_data'].get('is_webhook_active', False)
                except Exception as e:
                    self.logger.warning(f"[Bot-{bot_id}] Error checking webhook status: {e}")
            
            # Overall working status: polling OR webhooks
            is_working = is_polling or is_webhook_active
            
            return {
                "result": "success",
                "response_data": {
                    "is_active": is_active,
                    "is_polling": is_polling,
                    "is_webhook_active": is_webhook_active,
                    "is_working": is_working
                }
            }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error getting status: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def set_bot_token(self, data: dict) -> Dict[str, Any]:
        """
        Set/update bot token
        
        Flow:
        1. Validate bot exists
        2. Update token in DB
        3. Stop bot (old mode)
        4. Start bot with new token (if active and token not None)
        """
        try:
            tenant_id = data['tenant_id']
            
            if 'bot_token' not in data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "bot_token field is required"
                    }
                }
            
            bot_token = data.get('bot_token')  # Can be None for deletion
            
            # Get existing bot
            bot_result = await self.repository.get_bot_info_by_tenant_id(tenant_id)
            if bot_result['result'] != 'success':
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot for tenant {tenant_id} not found. Create bot first via sync_telegram_bot"
                    }
                }
            
            old_bot_data = bot_result['response_data']
            bot_id = old_bot_data['bot_id']
            old_token = old_bot_data.get('bot_token')
            
            # Update bot in DB
            update_data = {
                'tenant_id': tenant_id,
                'bot_token': bot_token,
                'is_active': old_bot_data.get('is_active', True)
            }
            
            update_result = await self.repository.create_or_update_bot(update_data)
            if update_result['result'] != 'success':
                return update_result
            
            # Stop old bot (with old token if exists)
            if self.use_webhooks and old_token:
                await self.webhook_manager.delete_webhook(old_token, bot_id)
            else:
                await self.telegram_polling.stop_bot_polling(bot_id)
            
            # Start with new token (if provided and bot active)
            if bot_token is not None and update_data['is_active']:
                if self.use_webhooks:
                    result = await self.webhook_manager.set_webhook(bot_id, bot_token)
                    if result['result'] != 'success':
                        self.logger.warning(f"[Bot-{bot_id}] Failed to set webhook (token may be invalid)")
                else:
                    success = await self.telegram_polling.start_bot_polling(bot_id, bot_token)
                    if not success:
                        self.logger.warning(f"[Bot-{bot_id}] Failed to start polling (token may be invalid)")
            elif bot_token is None:
                mode = "webhook" if self.use_webhooks else "polling"
                self.logger.info(f"[Bot-{bot_id}] Token deleted, {mode} stopped")
            
            return {"result": "success", "response_data": {}}
            
        except Exception as e:
            self.logger.error(f"Error setting bot token: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    # === Private methods ===
    
    def _should_restart_bot(
        self,
        action: str,
        old_bot_data: Optional[Dict],
        old_bot_id: Optional[int],
        bot_id: int,
        new_bot_token: Optional[str],
        new_is_active: bool
    ) -> bool:
        """
        Determine if bot needs to be restarted
        
        Logic:
        - If created: always restart (first start)
        - If updated:
          - For webhooks: always restart (idempotent webhook re-set)
          - For polling: restart only if critical fields changed OR not running
        """
        # New bot: always start
        if action == "created":
            return True
        
        # Updated bot: check if restart needed
        if action == "updated" and old_bot_data:
            old_token = old_bot_data.get('bot_token')
            old_is_active = old_bot_data.get('is_active')
            
            # Use old token if new token not provided
            if new_bot_token is None and old_bot_data:
                new_bot_token = old_token
            
            # Check if critical fields changed
            token_changed = old_token != new_bot_token
            active_changed = old_is_active != new_is_active
            
            # If nothing changed, check current status
            if not token_changed and not active_changed:
                if self.use_webhooks:
                    # For webhooks: always re-set (ensures webhook is set after system restart)
                    return True
                else:
                    # For polling: restart only if not running
                    is_running = self.telegram_polling.is_bot_polling(bot_id)
                    return not is_running
            
            # Critical fields changed: need restart
            return True
        
        # Default: restart
        return True
    
    async def _restart_bot(self, bot_id: int, bot_token: Optional[str], is_active: bool):
        """
        Restart bot: stop old mode + start new mode (if active)
        
        This method handles the transition properly:
        - Stops both polling AND webhooks (cleans up any previous state)
        - Starts only the current mode (if bot is active and has token)
        """
        try:
            # Stop BOTH modes (cleanup)
            # This ensures proper transition even if mode changed
            
            # Stop polling
            await self.telegram_polling.stop_bot_polling(bot_id)
            
            # Stop webhook (if token available and webhook manager exists)
            if bot_token and self.webhook_manager:
                await self.webhook_manager.delete_webhook(bot_token, bot_id)
            
            # Start bot in current mode (if active and token exists)
            if is_active and bot_token:
                if self.use_webhooks:
                    # Set webhook
                    result = await self.webhook_manager.set_webhook(bot_id, bot_token)
                    if result['result'] != 'success':
                        self.logger.error(f"[Bot-{bot_id}] Failed to set webhook")
                else:
                    # Start polling
                    success = await self.telegram_polling.start_bot_polling(bot_id, bot_token)
                    if not success:
                        self.logger.error(f"[Bot-{bot_id}] Failed to start polling")
            elif not bot_token:
                self.logger.warning(f"[Bot-{bot_id}] Token missing, bot not started")
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error restarting bot: {e}")
