"""
CacheManager - unified utility for global data caching
In-memory cache for all services with TTL and invalidation support
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class CacheManager:
    """
    Unified utility for global data caching
    - In-memory cache (Python dicts)
    - TTL support
    - Pattern-based invalidation
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Get settings
        settings = self.settings_manager.get_plugin_settings("cache_manager")
        
        # Main cache (flat dictionary, keys like "group:key")
        self._cache: Dict[str, Any] = {}
        
        # Expiration time for TTL items (like Redis - store expired_at)
        self._cache_expires_at: Dict[str, datetime] = {}
        
        # Default TTL to prevent memory leaks (if not explicitly specified in set())
        self._default_ttl = settings.get('default_ttl', 3600)  # 1 hour by default
        
        # Periodic cleanup settings (algorithm like Redis)
        self._cleanup_interval = settings.get('cleanup_interval', 60)  # 1 minute by default
        self._cleanup_sample_size = settings.get('cleanup_sample_size', 50)  # Sample size
        self._cleanup_expired_threshold = settings.get('cleanup_expired_threshold', 0.25)  # 25% threshold
        
        # Background task for periodic cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Start background task on initialization
        self._start_background_cleanup()

    # === Background tasks ===

    def _start_background_cleanup(self):
        """
        Start background task on initialization (synchronous method)
        """
        if self._is_running:
            return
        
        try:
            # Try to create task (like in task_manager)
            # asyncio.ensure_future() works if loop is already running or will be started
            self._is_running = True
            self._cleanup_task = asyncio.ensure_future(self._cleanup_loop())
            self.logger.info(f"Background cache cleanup task scheduled (interval: {self._cleanup_interval} sec)")
        except RuntimeError as e:
            # Event loop not available - this is a problem, task won't start
            self._is_running = False
            self.logger.error(f"Failed to start background cache cleanup task on initialization: {e}. Periodic cleanup will not work!")
    
    async def _cleanup_loop(self):
        """
        Background loop for periodic cache cleanup
        """
        try:
            while self._is_running:
                await asyncio.sleep(self._cleanup_interval)
                if self._is_running:
                    await self._clean_expired_cache()
        except asyncio.CancelledError:
            self.logger.info("Background cache cleanup task stopped")
        except Exception as e:
            self.logger.error(f"Error in background cache cleanup task: {e}")
    
    def stop_background_cleanup(self):
        """
        Stop background cache cleanup task (synchronous method for shutdown)
        """
        if not self._is_running:
            return
        
        self._is_running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            # Don't wait for task completion here, as this is a synchronous method
            # Task will complete when event loop stops
        self.logger.info("Background cache cleanup task stopped")

    # === Cache methods ===
    
    def _is_cache_valid(self, key: str) -> bool:
        """
        Check cache item validity (lazy cleanup, like Redis)
        If item expired - removed immediately
        """
        # Check if value exists in cache
        if key not in self._cache:
            return False
        
        # If no expiration time - cache is eternal
        if key not in self._cache_expires_at:
            return True
        
        # Simple time comparison (like Redis - store expired_at)
        current_time = datetime.now()
        if current_time >= self._cache_expires_at[key]:
            # Remove expired item
            self._cache.pop(key, None)
            self._cache_expires_at.pop(key, None)
            return False
        
        return True
    
    async def _clean_expired_cache(self):
        """
        Periodic cleanup of expired cache items (algorithm like Redis)
        1. Take random sample from all items with TTL
        2. If >25% expired - do full cleanup
        3. If <25% - only sample
        """
        
        current_time = datetime.now()
        
        # Get all keys with TTL
        keys_with_ttl = list(self._cache_expires_at.keys())
        
        if not keys_with_ttl:
            return
        
        # Take random sample (like Redis)
        sample_size = min(self._cleanup_sample_size, len(keys_with_ttl))
        sample_keys = random.sample(keys_with_ttl, sample_size)
        
        # Check sample
        expired_in_sample = 0
        for key in sample_keys:
            if current_time >= self._cache_expires_at[key]:
                expired_in_sample += 1
        
        # Calculate percentage of expired in sample
        expired_ratio = expired_in_sample / sample_size if sample_size > 0 else 0
        
        # If >25% expired - do full cleanup
        if expired_ratio >= self._cleanup_expired_threshold:
            # Full cleanup - iterate all items
            expired_keys = []
            for key in keys_with_ttl:
                if current_time >= self._cache_expires_at[key]:
                    expired_keys.append(key)
            
            # Remove expired
            for key in expired_keys:
                self._cache.pop(key, None)
                self._cache_expires_at.pop(key, None)
        else:
            # <25% expired - remove only those found in sample
            expired_keys = [key for key in sample_keys 
                           if current_time >= self._cache_expires_at[key]]
            
            for key in expired_keys:
                self._cache.pop(key, None)
                self._cache_expires_at.pop(key, None)
    
    # === Basic methods ===
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache by key
        Lazy cleanup: check specific item on access (like Redis)
        """
        try:
            # Lazy cleanup: check validity of specific item
            if not self._is_cache_valid(key):
                return None
            
            return self._cache.get(key)
            
        except Exception as e:
            self.logger.error(f"Error getting value from cache for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache
        If TTL not specified - uses default_ttl (memory leak protection)
        """
        try:
            # Set value
            self._cache[key] = value
            
            # Determine TTL (store expired_at like Redis)
            # If TTL not specified - use default
            final_ttl = ttl if ttl is not None else self._default_ttl
            
            # Set expiration time (always has TTL)
            self._cache_expires_at[key] = datetime.now() + timedelta(seconds=final_ttl)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting value in cache for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        """
        try:
            # Check validity before deletion (lazy cleanup)
            if not self._is_cache_valid(key):
                # Key expired or doesn't exist
                return False
            
            deleted = False
            if key in self._cache:
                del self._cache[key]
                deleted = True
            
            if key in self._cache_expires_at:
                del self._cache_expires_at[key]
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error deleting value from cache for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        """
        return self._is_cache_valid(key)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate keys by pattern
        Supports simple patterns: 'bot:*', 'tenant:123:*', '*:meta'
        """
        try:
            deleted_count = 0
            keys_to_delete = []
            
            # Simple pattern implementation
            if pattern.endswith(':*'):
                prefix = pattern[:-2]  # Remove ':*'
                keys_to_delete = [key for key in self._cache.keys() if key.startswith(prefix + ':')]
            elif pattern.startswith('*:'):
                suffix = pattern[2:]  # Remove '*:'
                keys_to_delete = [key for key in self._cache.keys() if key.endswith(':' + suffix)]
            elif '*' in pattern:
                # More complex pattern (can be extended later)
                prefix, suffix = pattern.split('*', 1)
                keys_to_delete = [
                    key for key in self._cache.keys()
                    if key.startswith(prefix) and key.endswith(suffix)
                ]
            else:
                # Exact match
                keys_to_delete = [pattern] if pattern in self._cache else []
            
            for key in keys_to_delete:
                if await self.delete(key):
                    deleted_count += 1
            
            if deleted_count > 0:
                self.logger.info(f"Invalidated {deleted_count} keys by pattern '{pattern}'")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error invalidating by pattern '{pattern}': {e}")
            return 0
    
    async def clear(self) -> bool:
        """
        Clear entire cache
        """
        try:
            count = len(self._cache)
            self._cache.clear()
            self._cache_expires_at.clear()
            self.logger.info(f"Cleared entire cache ({count} items)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
            return False
    
    # === Helper methods ===
    
    def shutdown(self):
        """
        Stop background cache cleanup task (for graceful shutdown)
        """
        self.stop_background_cleanup()
    

