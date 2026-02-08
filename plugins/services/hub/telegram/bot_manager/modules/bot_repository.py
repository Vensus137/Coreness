"""
Bot Repository - handles data access for bots
Manages database operations, caching, and Telegram API info retrieval
"""

from typing import Any, Dict, List, Optional


class BotRepository:
    """
    Repository for bot data management
    - CRUD operations with database
    - Caching strategy for bot information
    - Integration with Telegram API for bot validation
    """
    
    def __init__(self, database_manager, cache_manager, telegram_api, settings_manager, logger):
        self.database_manager = database_manager
        self.cache_manager = cache_manager
        self.telegram_api = telegram_api
        self.logger = logger
        
        # Get cache TTL settings
        bot_manager_settings = settings_manager.get_plugin_settings("telegram_bot_manager")
        self._bot_ttl = bot_manager_settings.get('cache_ttl', 315360000)  # 10 years
        self._error_ttl = bot_manager_settings.get('error_cache_ttl', 300)  # 5 minutes
    
    def _get_bot_cache_key(self, bot_id: int) -> str:
        """Generate cache key for bot"""
        return f"bot:{bot_id}"
    
    def _get_token_cache_key(self, bot_token: str) -> str:
        """Generate cache key for token lookup"""
        return f"bot:token:{bot_token}"
    
    async def get_bot_info(self, bot_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get full bot information (with caching)
        Returns: {"result": "success/error", "response_data": {...}, "error": {...}}
        """
        try:
            cache_key = self._get_bot_cache_key(bot_id)
            
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached = await self.cache_manager.get(cache_key)
                if cached:
                    if cached.get('_error'):
                        return {
                            "result": "error",
                            "error": {
                                "code": cached.get('code', 'UNKNOWN_ERROR'),
                                "message": cached.get('message', 'Unknown error')
                            }
                        }
                    return {"result": "success", "response_data": cached}
            
            # Fetch from database
            result = await self._fetch_bot_from_db(bot_id)
            
            if result.get('error'):
                error_info = result['error']
                error_code = 'NOT_FOUND' if error_info['type'] == 'NOT_FOUND' else 'INTERNAL_ERROR'
                error_message = error_info.get('message', 'Error fetching bot')
                
                # Cache error with short TTL
                error_data = {'_error': True, 'code': error_code, 'message': error_message}
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                
                return {
                    "result": "error",
                    "error": {"code": error_code, "message": error_message}
                }
            
            # Cache successful result
            bot_info = result['bot_info']
            await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
            
            # Cache tenant_id -> bot_id mapping
            tenant_id = bot_info.get('tenant_id')
            if tenant_id:
                tenant_key = f"tenant:{tenant_id}:bot_id"
                await self.cache_manager.set(tenant_key, bot_id, ttl=self._bot_ttl)
            
            return {"result": "success", "response_data": bot_info}
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error getting bot info: {e}")
            error_data = {'_error': True, 'code': 'INTERNAL_ERROR', 'message': str(e)}
            cache_key = self._get_bot_cache_key(bot_id)
            await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
            
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def get_bot_info_by_tenant_id(self, tenant_id: int) -> Dict[str, Any]:
        """Get bot information by tenant_id"""
        try:
            master_repo = self.database_manager.get_master_repository()
            bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
            
            if not bot_data:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Bot for tenant {tenant_id} not found"
                    }
                }
            
            bot_id = bot_data.get('id')
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Invalid bot data for tenant {tenant_id}"
                    }
                }
            
            return await self.get_bot_info(bot_id, force_refresh=False)
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting bot info: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def get_telegram_bot_info_by_token(self, bot_token: str) -> Dict[str, Any]:
        """
        Get bot info from Telegram API (with caching)
        Returns bot info directly from Telegram
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
            cached = await self.cache_manager.get(cache_key)
            if cached:
                if cached.get('_error'):
                    return {
                        "result": "error",
                        "error": {
                            "code": cached.get('code', 'API_ERROR'),
                            "message": cached.get('message', 'Unknown error')
                        }
                    }
                return {"result": "success", "response_data": cached}
            
            # Fetch from Telegram API
            result = await self.telegram_api.get_bot_info(bot_token)
            
            if result.get('result') == 'success':
                bot_info = result['response_data']
                await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
                return {"result": "success", "response_data": bot_info}
            else:
                # Cache error
                error_data = {
                    '_error': True,
                    'code': 'API_ERROR',
                    'message': 'Failed to get bot info from Telegram'
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": "Failed to get bot info from Telegram"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error getting Telegram bot info: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def create_or_update_bot(self, bot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update bot in database
        Returns: {"result": "success", "response_data": {"bot_id": int, "action": "created/updated"}}
        """
        try:
            tenant_id = bot_data.get('tenant_id')
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id is required"
                    }
                }
            
            master_repo = self.database_manager.get_master_repository()
            
            # Check if bot exists
            existing_bot = None
            all_bots = await master_repo.get_all_bots()
            for bot in all_bots:
                if bot.get('tenant_id') == tenant_id:
                    existing_bot = bot
                    break
            
            bot_token = bot_data.get('bot_token')
            # Normalize empty strings to None
            if bot_token is not None and not bot_token.strip():
                bot_token = None
            
            # Get bot info from Telegram if token provided
            telegram_info = {}
            if bot_token:
                tg_result = await self.telegram_api.get_bot_info(bot_token)
                if tg_result.get('result') == 'success':
                    telegram_info = tg_result['response_data']
            
            bot_id = None
            action = None
            
            if existing_bot:
                # Update existing bot
                bot_id = existing_bot['id']
                update_data = {'is_active': bot_data.get('is_active', True)}
                
                if bot_token is not None:
                    update_data['bot_token'] = bot_token
                
                if telegram_info:
                    update_data.update({
                        'telegram_bot_id': telegram_info.get('telegram_bot_id'),
                        'username': telegram_info.get('username'),
                        'first_name': telegram_info.get('first_name')
                    })
                
                success = await master_repo.update_bot(bot_id, update_data)
                if not success:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Failed to update bot {bot_id}"
                        }
                    }
                
                action = "updated"
                self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Bot updated")
            else:
                # Create new bot
                create_data = {
                    'tenant_id': tenant_id,
                    'bot_token': bot_token,
                    'is_active': bot_data.get('is_active', True)
                }
                
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
                self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Bot created")
            
            # Refresh cache
            await self.get_bot_info(bot_id, force_refresh=True)
            
            return {
                "result": "success",
                "response_data": {"bot_id": bot_id, "action": action}
            }
            
        except Exception as e:
            self.logger.error(f"Error creating/updating bot: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def sync_bot_commands(self, bot_id: int, command_list: List[Dict]) -> Dict[str, Any]:
        """
        Sync bot commands: save to DB and apply to Telegram
        """
        try:
            # Get bot info
            bot_result = await self.get_bot_info(bot_id)
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
            
            # Save to database
            master_repo = self.database_manager.get_master_repository()
            await master_repo.delete_commands_by_bot(bot_id)
            saved_count = await master_repo.save_commands_by_bot(bot_id, command_list)
            
            # Update cache
            cache_key = self._get_bot_cache_key(bot_id)
            cached_bot = await self.cache_manager.get(cache_key)
            if cached_bot and not cached_bot.get('_error'):
                cached_bot['bot_command'] = command_list
                await self.cache_manager.set(cache_key, cached_bot, ttl=self._bot_ttl)
            
            # Apply to Telegram
            tg_result = await self.telegram_api.sync_bot_commands(bot_token, bot_id, command_list)
            
            if tg_result['result'] != 'success':
                self.logger.warning(f"[Bot-{bot_id}] Failed to sync commands to Telegram")
                return tg_result
            
            self.logger.info(f"[Bot-{bot_id}] Synced {saved_count} commands")
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error syncing commands: {e}")
            return {
                "result": "error",
                "error": {"code": "INTERNAL_ERROR", "message": str(e)}
            }
    
    async def load_all_bots_cache(self) -> List[Dict]:
        """Load all bots into cache on startup"""
        try:
            master_repo = self.database_manager.get_master_repository()
            all_bots = await master_repo.get_all_bots()
            
            loaded_count = 0
            for bot_data in all_bots:
                bot_id = bot_data.get('id')
                if not bot_id:
                    continue
                
                # Get commands
                commands = await master_repo.get_commands_by_bot(bot_id)
                
                # Format bot info
                bot_info = self._format_bot_info(bot_data, commands)
                
                if not bot_info.get('tenant_id'):
                    self.logger.warning(f"[Bot-{bot_id}] Skipped: missing tenant_id")
                    continue
                
                # Cache bot info
                cache_key = self._get_bot_cache_key(bot_id)
                await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
                
                # Cache tenant mapping
                tenant_id = bot_info['tenant_id']
                tenant_key = f"tenant:{tenant_id}:bot_id"
                await self.cache_manager.set(tenant_key, bot_id, ttl=self._bot_ttl)
                
                loaded_count += 1
            
            self.logger.info(f"Loaded {loaded_count} bots into cache")
            return []
            
        except Exception as e:
            self.logger.error(f"Error loading bots cache: {e}")
            return []
    
    async def clear_bot_cache(self, bot_id: Optional[int] = None):
        """Clear cache for specific bot or all bots"""
        try:
            if bot_id:
                cache_key = self._get_bot_cache_key(bot_id)
                bot_info = await self.cache_manager.get(cache_key)
                
                if bot_info and not bot_info.get('_error'):
                    tenant_id = bot_info.get('tenant_id')
                    if tenant_id:
                        tenant_key = f"tenant:{tenant_id}:bot_id"
                        await self.cache_manager.delete(tenant_key)
                
                await self.cache_manager.delete(cache_key)
                self.logger.info(f"[Bot-{bot_id}] Cache cleared")
            else:
                await self.cache_manager.invalidate_pattern("bot:*")
                await self.cache_manager.invalidate_pattern("tenant:*:bot_id")
                self.logger.info("All bot cache cleared")
                
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    # === Private methods ===
    
    def _format_bot_info(self, bot_data: Dict, commands: List[Dict] = None) -> Dict:
        """Format bot info for caching"""
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
    
    async def _fetch_bot_from_db(self, bot_id: int) -> Dict:
        """
        Fetch bot from database
        Returns: {'bot_info': Dict | None, 'error': Dict | None}
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            bot_data = await master_repo.get_bot_by_id(bot_id)
            if not bot_data:
                return {'bot_info': None, 'error': {'type': 'NOT_FOUND'}}
            
            commands = await master_repo.get_commands_by_bot(bot_id)
            bot_info = self._format_bot_info(bot_data, commands)
            
            return {'bot_info': bot_info, 'error': None}
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error fetching from DB: {e}")
            return {
                'bot_info': None,
                'error': {'type': 'INTERNAL_ERROR', 'message': str(e)}
            }
