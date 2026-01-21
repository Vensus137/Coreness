"""
Tests for cache invalidation by patterns
"""
import pytest


@pytest.mark.asyncio
class TestInvalidation:
    """Tests for cache invalidation"""
    
    async def test_invalidate_pattern_prefix(self, cache_manager):
        """Test invalidation by prefix (bot:*)"""
        # Create several keys with bot: prefix
        keys = [
            "bot:1", "bot:2", "bot:3",
            "user:1:1", "user:2:1",  # Other keys
        ]
        
        for key in keys:
            await cache_manager.set(key, {"id": key})
        
        # Invalidate all keys with bot: prefix
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 3
        
        # Check that bot: keys are deleted
        assert await cache_manager.get("bot:1") is None
        assert await cache_manager.get("bot:2") is None
        assert await cache_manager.get("bot:3") is None
        
        # Check that other keys remained
        assert await cache_manager.get("user:1:1") is not None
        assert await cache_manager.get("user:2:1") is not None
    
    async def test_invalidate_pattern_suffix(self, cache_manager):
        """Test invalidation by suffix (*:meta)"""
        keys = [
            "tenant:1:meta",
            "tenant:2:meta",
            "tenant:1:scenarios",  # Different suffix
            "bot:1",  # Different prefix
        ]
        
        for key in keys:
            await cache_manager.set(key, {"data": key})
        
        # Invalidate all keys with :meta suffix
        deleted_count = await cache_manager.invalidate_pattern("*:meta")
        
        assert deleted_count == 2
        
        # Check deletion
        assert await cache_manager.get("tenant:1:meta") is None
        assert await cache_manager.get("tenant:2:meta") is None
        
        # Check that other keys remained
        assert await cache_manager.get("tenant:1:scenarios") is not None
        assert await cache_manager.get("bot:1") is not None
    
    async def test_invalidate_pattern_middle(self, cache_manager):
        """Test invalidation by pattern with * in middle"""
        keys = [
            "tenant:1:meta",
            "tenant:1:scenarios",
            "tenant:2:meta",
            "bot:1:meta",  # Different prefix
        ]
        
        for key in keys:
            await cache_manager.set(key, {"data": key})
        
        # Invalidate tenant:*:meta
        deleted_count = await cache_manager.invalidate_pattern("tenant:*:meta")
        
        assert deleted_count == 2
        
        # Check deletion
        assert await cache_manager.get("tenant:1:meta") is None
        assert await cache_manager.get("tenant:2:meta") is None
        
        # Check that other keys remained
        assert await cache_manager.get("tenant:1:scenarios") is not None
        assert await cache_manager.get("bot:1:meta") is not None
    
    async def test_invalidate_pattern_exact_match(self, cache_manager):
        """Test invalidation of exact match"""
        key = "test:exact"
        await cache_manager.set(key, {"data": "value"})
        
        # Invalidate exact match
        deleted_count = await cache_manager.invalidate_pattern("test:exact")
        
        assert deleted_count == 1
        assert await cache_manager.get(key) is None
    
    async def test_invalidate_pattern_nonexistent(self, cache_manager):
        """Test invalidation of non-existent pattern"""
        deleted_count = await cache_manager.invalidate_pattern("nonexistent:*")
        
        assert deleted_count == 0
    
    async def test_invalidate_pattern_with_ttl(self, cache_manager):
        """Test invalidation of keys with TTL"""
        # Create keys with TTL
        keys = ["user:1:1", "user:2:1", "user:3:1"]
        for key in keys:
            await cache_manager.set(key, {"user_id": key}, ttl=60)
        
        # Invalidate
        deleted_count = await cache_manager.invalidate_pattern("user:*")
        
        assert deleted_count == 3
        
        # Check that TTL are also deleted
        for key in keys:
            assert key not in cache_manager._cache
            assert key not in cache_manager._cache_expires_at
    
    async def test_invalidate_pattern_with_eternal_cache(self, cache_manager):
        """Test invalidation of eternal caches"""
        # Create eternal caches
        keys = ["bot:1", "bot:2", "bot:3"]
        for key in keys:
            await cache_manager.set(key, {"bot_id": key})
        
        # Invalidate
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 3
        
        # Check deletion
        for key in keys:
            assert await cache_manager.get(key) is None
    
    async def test_clear_all_cache(self, cache_manager):
        """Test clearing entire cache"""
        # Create many keys
        keys = [
            "bot:1", "bot:2",
            "user:1:1", "user:2:1",
            "tenant:1:meta", "tenant:1:scenarios",
        ]
        
        for key in keys:
            await cache_manager.set(key, {"data": key})
        
        # Clear entire cache
        result = await cache_manager.clear()
        
        assert result is True
        
        # Check that all keys are deleted
        for key in keys:
            assert await cache_manager.get(key) is None
        
        # Check that cache is empty
        assert len(cache_manager._cache) == 0
        assert len(cache_manager._cache_expires_at) == 0
    
    async def test_clear_empty_cache(self, cache_manager):
        """Test clearing empty cache"""
        result = await cache_manager.clear()
        
        assert result is True
        assert len(cache_manager._cache) == 0

