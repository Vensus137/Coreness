"""
Scenario cache by tenants
Manages scenario caching and metadata retrieval for isolated event processing
"""

from typing import Any, Dict, Optional


class ScenarioCache:
    """
    Scenario cache by tenants
    - Store scenarios in memory through cache_manager
    - Get scenario metadata for isolated event processing
    - Reload cache for specific tenant
    """
    
    def __init__(self, logger, cache_manager, settings_manager):
        self.logger = logger
        self.cache_manager = cache_manager
        
        # Get TTL from scenario_processor config
        scenario_settings = settings_manager.get_plugin_settings("scenario_processor")
        self._scenarios_ttl = scenario_settings.get('cache_ttl', 315360000)  # Permanent cache
    
    def _get_cache_key(self, tenant_id: int) -> str:
        """Generate cache key in cache_manager format"""
        return f"tenant:{tenant_id}:scenarios"
    
    async def get_scenario_metadata(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get tenant scenario metadata for isolated event processing"""
        try:
            cache_key = self._get_cache_key(tenant_id)
            original_cache = await self.cache_manager.get(cache_key)
            
            if original_cache is None:
                return None
            
            # Use references to all structures (don't copy)
            # Safe because all structures are only read during scenario execution
            # Changes only occur during reload_tenant_scenarios, which deletes old cache
            # References remain valid until event processing completes (GC will delete old cache after)
            metadata = {
                'search_tree': original_cache['search_tree'],  # Reference
                'scenario_index': original_cache['scenario_index'],  # Reference
                'scenario_name_index': original_cache['scenario_name_index']  # Reference
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error getting scenario metadata for tenant {tenant_id}: {e}")
            return None
    
    async def get_tenant_cache(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get cache for tenant"""
        cache_key = self._get_cache_key(tenant_id)
        return await self.cache_manager.get(cache_key)
    
    async def set_tenant_cache(self, tenant_id: int, cache: Dict[str, Any]) -> None:
        """Set cache for tenant"""
        cache_key = self._get_cache_key(tenant_id)
        await self.cache_manager.set(cache_key, cache, ttl=self._scenarios_ttl)
    
    async def has_tenant_cache(self, tenant_id: int) -> bool:
        """Check if cache exists for tenant"""
        cache_key = self._get_cache_key(tenant_id)
        return await self.cache_manager.exists(cache_key)
    
    async def reload_tenant_scenarios(self, tenant_id: int) -> bool:
        """Reload scenario cache for specific tenant. Deletes old cache"""
        try:
            # Clear cache for specific tenant
            cache_key = self._get_cache_key(tenant_id)
            await self.cache_manager.delete(cache_key)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reloading scenarios for tenant {tenant_id}: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up all resources"""
        try:
            # Clear scenario cache by pattern
            await self.cache_manager.invalidate_pattern("tenant:*:scenarios")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up: {e}")

