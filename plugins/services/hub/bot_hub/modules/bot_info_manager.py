"""
BotInfoManager - submodule for collecting and caching bot information
"""

from typing import Any, Dict, List


class BotInfoManager:
    """
    Bot information manager
    Collects data from database and caches it for fast access
    """
    
    def __init__(self, database_manager, action_hub, telegram_api, telegram_polling, logger, cache_manager, settings_manager, webhook_manager):
        self.database_manager = database_manager
        self.action_hub = action_hub
        self.telegram_api = telegram_api
        self.telegram_polling = telegram_polling
        self.logger = logger
        self.cache_manager = cache_manager
        self.webhook_manager = webhook_manager
        
        # Get TTL from bot_hub config
        bot_hub_settings = settings_manager.get_plugin_settings("bot_hub")
        self._bot_ttl = bot_hub_settings.get('cache_ttl', 315360000)  # Eternal cache
        self._error_ttl = bot_hub_settings.get('error_cache_ttl', 300)  # Error cache
    
    def _get_bot_cache_key(self, bot_id: int) -> str:
        """Generate cache key for bot by bot_id"""
        return f"bot:{bot_id}"
    
    def _get_token_cache_key(self, bot_token: str) -> str:
        """Generate cache key for bot by token"""
        return f"bot:token:{bot_token}"
    
    def _format_token_for_logs(self, bot_token: str) -> str:
        """
        Format token for logs: first 15 characters
        Token format: {bot_id}:{secret}, where bot_id can be extracted from start
        """
        if not bot_token:
            return "[Bot-Token: unknown]"
        
        # Take first 15 characters (usually bot_id + part of secret)
        return f"[Bot-Token: {bot_token[:15]}...]"
    
    async def _get_telegram_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """
        Get bot information through Telegram API
        """
        try:
            result = await self.telegram_api.get_bot_info(bot_token)
            
            if result.get('result') == 'success':
                return result.get('response_data', {})
            else:
                token_info = self._format_token_for_logs(bot_token)
                self.logger.warning(f"{token_info} Failed to get bot information: {result.get('error', 'Unknown error')}")
                return {}
                
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Error getting bot information through Telegram API: {e}")
            return {}
    
    async def get_telegram_bot_info_by_token(self, bot_token: str) -> Dict[str, Any]:
        """
        Get full bot information by token (with eternal caching)
        Returns result in standard ActionHub format
        """
        try:
            if not bot_token:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "bot_token is required"
                    }
                }
            
            # Check cache
            cache_key = self._get_token_cache_key(bot_token)
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                # Check if it's error or data
                if cached_data.get('_error'):
                    # This is cached error
                    return {
                        "result": "error",
                        "error": {
                            "code": cached_data.get('code', 'UNKNOWN_ERROR'),
                            "message": cached_data.get('message', 'Unknown error')
                        }
                    }
                else:
                    # This is bot data
                    return {"result": "success", "response_data": cached_data}
            
            # Get bot information through Telegram API
            # bot_id unavailable in this method, as it's called only by token
            bot_info = await self._get_telegram_bot_info(bot_token)
            
            # Form result in standard format
            if bot_info and bot_info.get('telegram_bot_id'):
                # Save to cache only data (without wrapper)
                await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
                return {
                    "result": "success",
                    "response_data": bot_info
                }
            else:
                # Cache error with short TTL
                error_data = {
                    '_error': True,
                    'code': 'API_ERROR',
                    'message': 'Failed to get bot information'
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": "Failed to get bot information"
                    }
                }
            
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Error getting bot information: {e}")
            # Cache error with short TTL
            error_data = {
                '_error': True,
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
            await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def get_bot_info(self, bot_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get full bot information from database (with caching)
        Returns universal structure: {"result": "success/error", "error": "...", "response_data": {...}}
        """
        try:
            # Check cache
            cache_key = self._get_bot_cache_key(bot_id)
            if not force_refresh:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    # Check if it's error or data
                    if cached_data.get('_error'):
                        # This is cached error
                        return {
                            "result": "error",
                            "error": {
                                "code": cached_data.get('code', 'UNKNOWN_ERROR'),
                                "message": cached_data.get('message', 'Unknown error')
                            }
                        }
                    else:
                        # This is bot data
                        return {"result": "success", "response_data": cached_data}
            
            # Collect information from database
            result = await self._collect_bot_info_from_db(bot_id)
            
            # Check if there's an error
            if result.get('error'):
                error_info = result['error']
                error_type = error_info.get('type')
                
                if error_type == 'NOT_FOUND':
                    error_code = 'NOT_FOUND'
                    error_message = f'Bot {bot_id} not found in database'
                else:  # INTERNAL_ERROR
                    error_code = 'INTERNAL_ERROR'
                    error_message = error_info.get('message', 'Error getting bot information from DB')
                
                # Cache error with short TTL
                error_data = {
                    '_error': True,
                    'code': error_code,
                    'message': error_message
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": error_code,
                        "message": error_message
                    }
                }
            
            # Get bot data
            bot_info = result.get('bot_info')
            if not bot_info:
                # Just in case (shouldn't happen, but for safety)
                error_data = {
                    '_error': True,
                    'code': 'INTERNAL_ERROR',
                    'message': 'Failed to get bot data'
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to get bot data"
                    }
                }
            
            # Save to cache only data (without wrapper)
            await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
            
            # Save mapping tenant_id -> bot_id for fast access
            tenant_id = bot_info.get('tenant_id')
            if tenant_id:
                tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
                await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=self._bot_ttl)
            
            # Form universal structure for return
            return {"result": "success", "response_data": bot_info}
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Unexpected error getting bot information: {e}")
            # Cache error with short TTL
            error_data = {
                '_error': True,
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
            await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def get_bot_info_by_tenant_id(self, tenant_id: int) -> Dict[str, Any]:
        """
        Get bot information by tenant_id (with caching)
        Returns universal structure: {"result": "success/error", "error": "...", "response_data": {...}}
        """
        try:
            # Get master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Get bot_id through get_bot_id_by_tenant_id (uses cache mapping)
            # But we don't have direct access to tenant_cache, so use direct query
            bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
            
            if not bot_data:
                return {"result": "error", "error": f"Bot for tenant {tenant_id} not found"}
            
            # Raw data from DB uses 'id'
            bot_id = bot_data.get('id')
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot_id for tenant {tenant_id}"
                    }
                }
            
            # Use existing get_bot_info method (with caching)
            return await self.get_bot_info(bot_id, force_refresh=False)
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting bot information: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def load_all_bots_cache(self) -> List[Dict[str, Any]]:
        """Load cache for all bots on service startup"""
        try:
            # Get master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Get all bots
            all_bots = await master_repo.get_all_bots()
            
            loaded_count = 0
            loaded_bots = []
            
            for bot_data in all_bots:
                bot_id = bot_data.get('id')
                if bot_id:
                    # Get commands for this bot
                    commands = await master_repo.get_commands_by_bot(bot_id)
                    
                    # Form data structure using unified method
                    # This guarantees data format consistency in cache
                    bot_info = self._format_bot_info(bot_data, commands)
                    
                    # If data incorrect - skip (bot_token can be None - this is normal)
                    if not bot_info.get('tenant_id'):
                        self.logger.warning(f"[Bot-{bot_id}] Skipped on cache load: tenant_id missing")
                        continue
                    
                    # Save to cache only data (without wrapper)
                    cache_key = self._get_bot_cache_key(bot_id)
                    await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
                    
                    # Save mapping tenant_id -> bot_id for fast access
                    tenant_id = bot_info.get('tenant_id')
                    if tenant_id:
                        tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
                        await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=self._bot_ttl)
                    
                    # For return wrap in response format
                    loaded_bots.append({"result": "success", "response_data": bot_info})
                    loaded_count += 1
            
            self.logger.info(f"Loaded {loaded_count} bots into cache")
            
            return loaded_bots
            
        except Exception as e:
            self.logger.error(f"Error loading cache for all bots: {e}")
            return []
    
    async def refresh_bot_info(self, bot_id: int) -> bool:
        """Force refresh bot information"""
        try:
            await self.get_bot_info(bot_id, force_refresh=True)
            return True
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error refreshing bot information: {e}")
            return False
    
    async def clear_bot_cache(self, bot_id: int = None) -> bool:
        """Clear cache for specific bot or entire cache"""
        try:
            if bot_id:
                cache_key = self._get_bot_cache_key(bot_id)
                # Get bot_info to know tenant_id
                bot_info = await self.cache_manager.get(cache_key)
                if bot_info:
                    tenant_id = bot_info.get('tenant_id')
                    if tenant_id:
                        # Clear mapping tenant -> bot_id
                        tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
                        await self.cache_manager.delete(tenant_bot_id_key)
                
                # Clear structured bot data
                await self.cache_manager.delete(cache_key)
                self.logger.info(f"[Bot-{bot_id}] Cache cleared")
            else:
                # Clear all bot keys by pattern
                await self.cache_manager.invalidate_pattern("bot:*")
                # Clear all mappings tenant -> bot_id
                await self.cache_manager.invalidate_pattern("tenant:*:bot_id")
                self.logger.info("All bot cache cleared")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False
    
    async def sync_bot_commands(self, bot_id: int, command_list: List[Dict[str, Any]]) -> bool:
        """
        Sync bot commands: delete old → save new → update cache
        """
        try:
            # Get master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Delete all existing commands for bot
            await master_repo.delete_commands_by_bot(bot_id)
            
            # Save new commands
            saved_count = await master_repo.save_commands_by_bot(bot_id, command_list)
            
            # Update cache
            cache_key = self._get_bot_cache_key(bot_id)
            cached_bot_info = await self.cache_manager.get(cache_key)
            if cached_bot_info:
                cached_bot_info['bot_command'] = command_list
                await self.cache_manager.set(cache_key, cached_bot_info, ttl=self._bot_ttl)
            
            self.logger.info(f"[Bot-{bot_id}] Saved {saved_count} commands to DB")
            return True
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error syncing commands: {e}")
            return False
    
    async def create_or_update_bot(self, bot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update bot: manage DB + cache
        """
        try:
            tenant_id = bot_data.get('tenant_id')
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id is required in bot_data"
                    }
                }
            
            # Get master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Find existing bot for this tenant
            existing_bot = None
            all_bots = await master_repo.get_all_bots()
            for bot in all_bots:
                if bot.get('tenant_id') == tenant_id:
                    existing_bot = bot
                    break
            
            bot_id = None
            action = None
            
            # Get token from data (can be None if not provided from config)
            bot_token = bot_data.get('bot_token')
            # Normalize: empty strings and strings with only spaces convert to None
            # This is needed for correct handling when token not specified in config
            if bot_token is not None and not bot_token.strip():
                bot_token = None
            
            # Get bot information through Telegram API (only if token provided)
            telegram_info = {}
            if bot_token:
                telegram_info = await self._get_telegram_bot_info(bot_token)
                    
            if existing_bot:
                # Update existing bot
                bot_id = existing_bot.get('id')
                update_data = {
                    'is_active': bot_data.get('is_active', True)
                }
                
                # Update token only if provided (config priority)
                if bot_token is not None:
                    update_data['bot_token'] = bot_token
                
                # Add data from Telegram API (only if token was provided and valid)
                if telegram_info:
                    update_data.update({
                        'telegram_bot_id': telegram_info.get('telegram_bot_id'),
                        'username': telegram_info.get('username'),
                        'first_name': telegram_info.get('first_name')
                    })
                
                update_success = await master_repo.update_bot(bot_id, update_data)
                
                if not update_success:
                    return {"result": "error", "error": f"Failed to update bot {bot_id}"}
                
                action = "updated"
                if bot_token is not None:
                    self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Bot updated (token updated from config)")
                else:
                    self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Bot updated (token from DB preserved)")
            else:
                # Create new bot (token optional, can be set later through master bot)
                create_data = {
                    'tenant_id': tenant_id,
                    'bot_token': bot_token,  # Can be None if token not provided
                    'is_active': bot_data.get('is_active', True)
                }
                
                # Add data from Telegram API (only if token was provided and valid)
                if telegram_info:
                    create_data.update({
                        'telegram_bot_id': telegram_info.get('telegram_bot_id'),
                        'username': telegram_info.get('username'),
                        'first_name': telegram_info.get('first_name')
                    })
                
                bot_id = await master_repo.create_bot(create_data)
                
                if not bot_id:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Failed to create bot"
                        }
                    }
                
                action = "created"
                self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] New bot created")
            
            # Update cache - get fresh data from DB
            await self.get_bot_info(bot_id, force_refresh=True)
            
            return {
                "result": "success",
                "response_data": {
                    "bot_id": bot_id,
                    "action": action
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error creating/updating bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Private methods ===
    
    def _format_bot_info(self, bot_data: Dict[str, Any], commands: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Form unified bot_info structure from bot data and commands
        Used for data format consistency in cache
        """
        return {
            'bot_id': bot_data.get('id'),
            'telegram_bot_id': bot_data.get('telegram_bot_id'),
            'tenant_id': bot_data.get('tenant_id'),
            'bot_token': bot_data.get('bot_token'),
            'username': bot_data.get('username'),
            'first_name': bot_data.get('first_name'),
            'is_active': bot_data.get('is_active'),
            'bot_command': commands or []
        }
    
    async def _collect_bot_info_from_db(self, bot_id: int) -> Dict[str, Any]:
        """
        Collect all bot information from database
        Returns structure: {'bot_info': Dict | None, 'error': Dict | None}
        - If success: {'bot_info': {...}, 'error': None}
        - If NOT_FOUND: {'bot_info': None, 'error': {'type': 'NOT_FOUND'}}
        - If INTERNAL_ERROR: {'bot_info': None, 'error': {'type': 'INTERNAL_ERROR', 'message': '...'}}
        """
        try:
            # Get master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Get bot data
            bot_data = await master_repo.get_bot_by_id(bot_id)
            if not bot_data:
                self.logger.warning(f"Bot {bot_id} not found in database")
                return {
                    'bot_info': None,
                    'error': {'type': 'NOT_FOUND'}
                }
            
            # Get bot commands
            commands = await master_repo.get_commands_by_bot(bot_id)
            
            # Form result using unified method
            bot_info = self._format_bot_info(bot_data, commands)
            return {
                'bot_info': bot_info,
                'error': None
            }
            
        except Exception as e:
            # INTERNAL_ERROR - error on DB query
            self.logger.error(f"[Bot-{bot_id}] Error getting bot information from DB: {e}")
            return {
                'bot_info': None,
                'error': {
                    'type': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            }
    
    async def get_bot_status(self, data: dict) -> Dict[str, Any]:
        """
        Get bot working status: polling OR webhooks
        """
        try:
            bot_id = data.get('bot_id')
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "bot_id is required"
                    }
                }
            
            # Get bot information from DB (use cache)
            bot_info = await self.get_bot_info(bot_id, force_refresh=False)
            is_active = bot_info.get('response_data', {}).get('is_active')
            bot_token = bot_info.get('response_data', {}).get('bot_token')
            
            # Check polling activity
            is_polling = self.telegram_polling.is_bot_polling(bot_id)
            
            # Check webhook activity (if token exists)
            is_webhook_active = False
            if bot_token:
                try:
                    webhook_info = await self.webhook_manager.get_webhook_info(bot_token, bot_id)
                    if webhook_info.get('result') == 'success':
                        is_webhook_active = webhook_info.get('response_data', {}).get('is_webhook_active', False)
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
            self.logger.error(f"[Bot-{bot_id}] Error getting bot status: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }