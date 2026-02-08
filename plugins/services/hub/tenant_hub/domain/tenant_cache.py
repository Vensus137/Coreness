"""
TenantCache - submodule for caching tenant information
"""

from typing import Any, Dict, Optional


class TenantCache:
    """
    Cache for storing tenant information
    Permanent cache, filled on first request
    """
    
    def __init__(self, database_manager, logger, datetime_formatter, cache_manager, settings_manager):
        self.database_manager = database_manager
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        self.cache_manager = cache_manager
        
        # Get TTL from tenant_hub config
        tenant_hub_settings = settings_manager.get_plugin_settings("tenant_hub")
        self._cache_ttl = tenant_hub_settings.get('cache_ttl', 315360000)  # Permanent cache
    
    def _get_tenant_bot_id_key(self, tenant_id: int) -> str:
        """Generate cache key for tenant_id -> bot_id mapping"""
        return f"tenant:{tenant_id}:bot_id"
    
    def _get_bot_cache_key(self, bot_id: int) -> str:
        """Generate cache key for structured bot data by bot_id"""
        return f"bot:{bot_id}"
    
    def _get_tenant_meta_cache_key(self, tenant_id: int) -> str:
        """Generate cache key for tenant metadata"""
        return f"tenant:{tenant_id}:meta"
    
    def _get_tenant_config_key(self, tenant_id: int) -> str:
        """Generate cache key for tenant config"""
        return f"tenant:{tenant_id}:config"
    
    async def get_bot_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get bot information by tenant_id
        Always returns structured data with 'bot_id' field
        Uses mapping tenant:{tenant_id}:bot_id and structured data bot:{bot_id}
        """
        try:
            # Step 1: Get bot_id from mapping
            tenant_bot_id_key = self._get_tenant_bot_id_key(tenant_id)
            cached_bot_id = await self.cache_manager.get(tenant_bot_id_key)
            
            bot_id = None
            bot_data = None
            
            if cached_bot_id:
                # Mapping exists in cache
                bot_id = cached_bot_id
            else:
                # Mapping not found - get from DB
                master_repo = self.database_manager.get_master_repository()
                bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
                
                if not bot_data:
                    self.logger.warning(f"[Tenant-{tenant_id}] Bot not found in DB")
                    return None
                
                bot_id = bot_data.get('id')
                if not bot_id:
                    self.logger.warning(f"[Tenant-{tenant_id}] Bot found but bot_id missing")
                    return None
                
                # Save mapping to cache
                await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=self._cache_ttl)
            
            # Step 2: Try to get structured data from bot:{bot_id}
            bot_cache_key = self._get_bot_cache_key(bot_id)
            structured_bot_info = await self.cache_manager.get(bot_cache_key)
            
            if structured_bot_info:
                # Structured data exists - return it
                return structured_bot_info
            
            # Step 3: Structured data not found - create from raw DB data
            if not bot_data:
                master_repo = self.database_manager.get_master_repository()
                bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
                if not bot_data:
                    return None
            
            # Get bot commands
            master_repo = self.database_manager.get_master_repository()
            commands = await master_repo.get_commands_by_bot(bot_id)
            
            # Form structured data (like in BotInfoManager._format_bot_info)
            structured_bot_info = {
                'bot_id': bot_data.get('id'),
                'telegram_bot_id': bot_data.get('telegram_bot_id'),
                'tenant_id': bot_data.get('tenant_id'),
                'bot_token': bot_data.get('bot_token'),
                'username': bot_data.get('username'),
                'first_name': bot_data.get('first_name'),
                'is_active': bot_data.get('is_active'),
                'bot_command': commands or []
            }
            
            # Save structured data to cache
            await self.cache_manager.set(bot_cache_key, structured_bot_info, ttl=self._cache_ttl)
            
            return structured_bot_info
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting bot data: {e}")
            return None
    
    async def get_bot_id_by_tenant_id(self, tenant_id: int) -> Optional[int]:
        """
        Get only bot_id by tenant_id
        """
        bot_data = await self.get_bot_by_tenant_id(tenant_id)
        if not bot_data:
            return None
        # Always structured data with 'bot_id'
        return bot_data.get('bot_id')
    
    async def invalidate_bot_cache(self, tenant_id: int):
        """
        Invalidate bot cache for specified tenant_id
        Deletes mapping tenant:{tenant_id}:bot_id
        """
        tenant_bot_id_key = self._get_tenant_bot_id_key(tenant_id)
        await self.cache_manager.delete(tenant_bot_id_key)
    
    async def clear_bot_cache(self):
        """
        Clear cache of tenant -> bot_id mappings
        """
        await self.cache_manager.invalidate_pattern("tenant:*:bot_id")

    # === In-memory tenant data ===
    async def set_last_updated(self, tenant_id: int) -> None:
        cache_key = self._get_tenant_meta_cache_key(tenant_id)
        meta = await self.cache_manager.get(cache_key) or {}
        now_tz = await self.datetime_formatter.now_local_tz()
        meta['last_updated_at'] = await self.datetime_formatter.to_string(now_tz)
        meta.pop('last_error', None)
        meta.pop('last_failed_at', None)
        await self.cache_manager.set(cache_key, meta, ttl=self._cache_ttl)

    async def set_last_failed(self, tenant_id: int, error: dict) -> None:
        """
        Save error to tenant cache
        Expects error object with fields: code, message, details (optional)
        """
        cache_key = self._get_tenant_meta_cache_key(tenant_id)
        meta = await self.cache_manager.get(cache_key) or {}
        now_tz = await self.datetime_formatter.now_local_tz()
        meta['last_failed_at'] = await self.datetime_formatter.to_string(now_tz)
        # Save entire error object for access through placeholders ({last_error.message}, {last_error.code})
        meta['last_error'] = error
        await self.cache_manager.set(cache_key, meta, ttl=self._cache_ttl)

    async def get_tenant_cache(self, tenant_id: int) -> Dict[str, Any]:
        cache_key = self._get_tenant_meta_cache_key(tenant_id)
        return await self.cache_manager.get(cache_key) or {}
    
    async def get_tenant_config(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tenant config with caching
        Returns dictionary with config (e.g., {"ai_token": "..."})
        """
        try:
            # Step 1: Check cache
            cache_key = self._get_tenant_config_key(tenant_id)
            cached_config = await self.cache_manager.get(cache_key)
            
            if cached_config is not None:
                return cached_config
            
            # Step 2: Cache not found - get from DB
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            
            if not tenant_data:
                return None
            
            # Form config dictionary from all DB fields (exclude system fields)
            # System fields: id, processed_at (and relationship fields, but they don't get into dictionary)
            config = {}
            excluded_fields = {'id', 'processed_at'}
            for key, value in tenant_data.items():
                if key not in excluded_fields and value is not None:
                    config[key] = value
            
            # Save to cache (even if empty, to avoid querying DB every time)
            await self.cache_manager.set(cache_key, config, ttl=self._cache_ttl)
            
            return config
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting tenant config: {e}")
            return None
    
    async def update_tenant_config_cache(self, tenant_id: int) -> None:
        """
        Update tenant config cache from DB
        Gets current data from DB and saves to cache
        Used after updating config in DB to synchronize cache
        """
        try:
            # Get data from DB
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            
            if not tenant_data:
                # Tenant not found - delete cache
                cache_key = self._get_tenant_config_key(tenant_id)
                await self.cache_manager.delete(cache_key)
                return
            
            # Form config dictionary from all DB fields (exclude system fields)
            config = {}
            excluded_fields = {'id', 'processed_at'}
            for key, value in tenant_data.items():
                if key not in excluded_fields and value is not None:
                    config[key] = value
            
            # Update cache (overwrite with current data)
            cache_key = self._get_tenant_config_key(tenant_id)
            await self.cache_manager.set(cache_key, config, ttl=self._cache_ttl)
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error updating tenant config cache: {e}")

