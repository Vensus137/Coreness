"""
BotActions - actions for managing bots
"""

from typing import Any, Dict


class BotActions:
    """
    Actions for managing bots
    """
    
    def __init__(self, bot_info_manager, telegram_polling, telegram_api, webhook_manager, settings_manager, logger):
        self.bot_info_manager = bot_info_manager
        self.telegram_polling = telegram_polling
        self.telegram_api = telegram_api
        self.webhook_manager = webhook_manager
        self.settings_manager = settings_manager
        self.logger = logger
        
        # Get settings from bot_hub
        bot_hub_settings = self.settings_manager.get_plugin_settings("bot_hub")
        use_webhooks_setting = bot_hub_settings.get('use_webhooks', False)
        
        # Automatically switch to polling if webhooks are unavailable
        # Check http_server availability through webhook_manager
        self.use_webhooks = use_webhooks_setting and webhook_manager.http_server is not None
        
        if use_webhooks_setting and not self.use_webhooks:
            self.logger.warning("Webhooks enabled in settings, but http_server unavailable - automatically using polling")
    
    async def start_bot(self, data: dict) -> Dict[str, Any]:
        """
        Start bot
        """
        try:
            bot_id = data.get('bot_id')
            
            # Get bot information
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information for {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot token for {bot_id} not found"
                    }
                }
            
            # Start bot depending on mode
            if self.use_webhooks:
                # Set webhook
                result = await self.webhook_manager.set_webhook(bot_id, bot_info['bot_token'])
                if result.get('result') == 'success':
                    return {"result": "success"}
                else:
                    return result
            else:
                # Start polling
                success = await self.telegram_polling.start_bot_polling(bot_id, bot_info['bot_token'])
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Failed to start bot {bot_id}"
                        }
                    }
                
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
        """
        Stop specific bot
        """
        try:
            bot_id = data.get('bot_id')
            
            # Get bot information to get token
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information for {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            bot_token = bot_info.get('bot_token')
            
            # Stop bot depending on mode
            if self.use_webhooks:
                # Delete webhook
                if bot_token:
                    result = await self.webhook_manager.delete_webhook(bot_token, bot_id)
                    return result
                else:
                    return {"result": "success"}
            else:
                # Stop polling
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
            self.logger.error(f"Error stopping bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def stop_all_bots(self, data: dict) -> Dict[str, Any]:
        """
        Stop all bots
        """
        try:
            if self.use_webhooks:
                # For webhooks need to get all bots and delete webhooks
                # Get all bots from DB
                master_repo = self.bot_info_manager.database_manager.get_master_repository()
                all_bots = await master_repo.get_all_bots()
                
                errors = []
                for bot_data in all_bots:
                    bot_id = bot_data.get('id')
                    bot_token = bot_data.get('bot_token')
                    
                    if bot_token:
                        result = await self.webhook_manager.delete_webhook(bot_token, bot_id)
                        if result.get('result') != 'success':
                            errors.append(f"Bot-{bot_id}")
                
                if errors:
                    self.logger.warning(f"Errors stopping bots: {', '.join(errors)}")
                    return {
                        "result": "partial_success",
                        "error": {
                            "code": "PARTIAL_ERROR",
                            "message": f"Failed to stop some bots: {', '.join(errors)}"
                        }
                    }
                
                return {"result": "success"}
            else:
                # Stop all polling
                success = await self.telegram_polling.stop_all_polling()
                
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Failed to stop all bots"
                        }
                    }
                
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
        """
        Sync bot configuration: create/update bot + conditional polling restart
        Restarts polling only if critical fields changed (bot_token, is_active) or bot created for first time
        """
        try:
            tenant_id = data.get('tenant_id')
            
            # Get current bot data BEFORE update (for comparison)
            old_bot_data = None
            bot_id = None
            # Try to find existing bot by tenant_id
            bot_result = await self.bot_info_manager.get_bot_info_by_tenant_id(tenant_id)
            if bot_result.get('result') == 'success':
                old_bot_data = bot_result.get('response_data', {})
                bot_id = old_bot_data.get('bot_id')
            # If bot not found (result == 'error') - this is normal, means new bot will be created
            
            # Use BotInfoManager to create/update bot (DB + cache)
            # Pass data directly, as it already contains all bot data
            sync_result = await self.bot_info_manager.create_or_update_bot(data)
            
            if sync_result.get('result') != 'success':
                return sync_result
            
            bot_id = sync_result.get('response_data', {}).get('bot_id')
            action = sync_result.get('response_data', {}).get('action')
            
            # Determine if polling needs to be restarted
            # By default restart (safe approach)
            new_bot_token = data.get('bot_token')
            # If token not provided from config, use from DB (old)
            if new_bot_token is None and old_bot_data:
                new_bot_token = old_bot_data.get('bot_token')
            
            new_is_active = data.get('is_active', True)
            
            # Determine if bot needs to be restarted
            should_restart = True  # By default restart
            
            if action == "updated" and old_bot_data:
                # Bot updated - check if critical fields changed
                old_bot_token = old_bot_data.get('bot_token')
                old_is_active = old_bot_data.get('is_active')
                
                # Check current state
                if self.use_webhooks:
                    # For webhooks: always set webhook on sync if bot is active
                    # This guarantees webhook setup on first start and after system restart
                    # Telegram API will handle conflict (409) itself if webhook already set
                    is_active = False  # Always consider that webhook needs to be set/re-set
                else:
                    # For polling check actual status
                    is_active = self.telegram_polling.is_bot_polling(bot_id)
                
                # Do NOT restart only if:
                # 1. Critical fields match AND
                # 2. Bot already active (only for polling)
                if (old_bot_token == new_bot_token and 
                    old_is_active is not None and 
                    old_is_active == new_is_active):
                    if self.use_webhooks:
                        # For webhooks always restart (set webhook)
                        # This guarantees webhook setup on first start and after restart
                        should_restart = True
                    elif is_active:
                        # For polling don't restart if already running
                        should_restart = False
                    else:
                        # Polling not started - need to start
                        should_restart = True
            
            # Restart bot only if needed
            if should_restart:
                # Stop existing mode
                if self.use_webhooks:
                    # Delete webhook
                    if new_bot_token:
                        await self.webhook_manager.delete_webhook(new_bot_token, bot_id)
                else:
                    # Stop polling
                    await self.telegram_polling.stop_bot_polling(bot_id)
                
                # Start bot only if active
                if new_is_active:
                    if new_bot_token:
                        if self.use_webhooks:
                            # Set webhook
                            result = await self.webhook_manager.set_webhook(bot_id, new_bot_token)
                            if result.get('result') != 'success':
                                self.logger.error(f"[Bot-{bot_id}] Failed to set webhook")
                        else:
                            # Start polling
                            success = await self.telegram_polling.start_bot_polling(bot_id, new_bot_token)
                            if not success:
                                self.logger.error(f"[Bot-{bot_id}] Failed to start polling")
                    else:
                        self.logger.warning(f"[Bot-{bot_id}] Token missing, bot not started")
            
            return {
                "result": "success",
                "response_data": {
                    "bot_id": bot_id,
                    "action": action
                }
            }
                
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
        """
        Sync bot commands: save to DB → apply in Telegram
        """
        try:
            bot_id = data.get('bot_id')
            command_list = data.get('command_list', [])
            
            # Get bot information
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information for {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot token for {bot_id} not found"
                    }
                }
            
            # First sync commands in database
            sync_success = await self.bot_info_manager.sync_bot_commands(bot_id, command_list)
            if not sync_success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Failed to sync commands in DB for bot {bot_id}"
                    }
                }
            
            # Then apply commands in Telegram
            result = await self.telegram_api.sync_bot_commands(
                bot_info['bot_token'], 
                bot_id, 
                command_list
            )
            
            if result.get('result') == 'success':
                return {"result": "success"}
            else:
                error_msg = result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": error_msg
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error syncing commands: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def set_bot_token(self, data: dict) -> Dict[str, Any]:
        """
        Set bot token.
        Bot must be created through configuration sync (sync_bot_config).
        Token will be validated automatically when polling starts.
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Check that field is explicitly provided (present in data)
            if 'bot_token' not in data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No fields to update"
                    }
                }
            
            bot_token = data.get('bot_token')  # Can be None for deletion
            
            # Get current bot data BEFORE update
            # Check that bot exists (should be created through configuration)
            bot_result = await self.bot_info_manager.get_bot_info_by_tenant_id(tenant_id)
            if bot_result.get('result') != 'success':
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot for tenant {tenant_id} not found. First create bot through configuration sync (sync_bot_config)"
                    }
                }
            
            old_bot_data = bot_result.get('response_data', {})
            
            # Save token to DB through create_or_update_bot
            # Token will be validated automatically when polling starts
            bot_data = {
                'tenant_id': tenant_id,
                'bot_token': bot_token,  # Can be None for deletion
                'is_active': old_bot_data.get('is_active', True)
            }
            
            sync_result = await self.bot_info_manager.create_or_update_bot(bot_data)
            if sync_result.get('result') != 'success':
                return sync_result
            
            updated_bot_id = sync_result.get('response_data', {}).get('bot_id')
            
            # Stop existing mode (in any case, as token changed or deleted)
            if self.use_webhooks:
                # Delete webhook
                old_token = old_bot_data.get('bot_token')
                if old_token:
                    await self.webhook_manager.delete_webhook(old_token, updated_bot_id)
            else:
                # Stop polling
                await self.telegram_polling.stop_bot_polling(updated_bot_id)
            
            # If token not None and bot active - start bot with new token
            if bot_token is not None and bot_data.get('is_active', True):
                if self.use_webhooks:
                    # Set webhook
                    result = await self.webhook_manager.set_webhook(updated_bot_id, bot_token)
                    if result.get('result') != 'success':
                        self.logger.warning(f"[Bot-{updated_bot_id}] Failed to set webhook after setting token (token may be invalid)")
                else:
                    # Start polling
                    success = await self.telegram_polling.start_bot_polling(updated_bot_id, bot_token)
                    if not success:
                        self.logger.warning(f"[Bot-{updated_bot_id}] Failed to start polling after setting token (token may be invalid)")
            elif bot_token is None:
                # Token deleted - bot already stopped
                mode = "webhook" if self.use_webhooks else "polling"
                self.logger.info(f"[Bot-{updated_bot_id}] Bot token deleted, {mode} stopped")
            
            self.logger.info(f"[Tenant-{tenant_id}] [Bot-{updated_bot_id}] Token set")
            
            return {
                "result": "success",
                "response_data": {}
            }
                
        except Exception as e:
            self.logger.error(f"Error setting bot token: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }