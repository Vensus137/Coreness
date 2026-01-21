"""
Tests for TTL (cache time to live)
"""
import asyncio

import pytest


@pytest.mark.asyncio
class TestTTL:
    """Tests for TTL functionality"""
    
    async def test_eternal_cache_large_ttl(self, cache_manager):
        """Test eternal cache (large TTL)"""
        key = "bot:123"
        value = {"bot_id": 123}
        large_ttl = 315360000  # 10 years
        
        await cache_manager.set(key, value, ttl=large_ttl)
        
        # Wait a bit
        await asyncio.sleep(0.01)
        
        # Value should remain (test BEHAVIOR, not internal data)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
        
        # Check that key exists
        assert await cache_manager.exists(key) is True
    
    async def test_ttl_expiration(self, cache_manager_with_short_ttl):
        """Test TTL expiration"""
        key = "user:123:1"
        value = {"user_id": 123}
        short_ttl = 0.01  # 0.01 seconds for fast test
        
        await cache_manager_with_short_ttl.set(key, value, ttl=short_ttl)
        
        # Immediately after setting value should be available
        retrieved = await cache_manager_with_short_ttl.get(key)
        assert retrieved == value
        
        # Wait for TTL expiration (0.01 sec + small margin)
        await asyncio.sleep(0.02)
        
        # Value should expire
        retrieved = await cache_manager_with_short_ttl.get(key)
        assert retrieved is None
        assert await cache_manager_with_short_ttl.exists(key) is False
    
    async def test_lazy_cleanup_on_get(self, cache_manager_with_short_ttl):
        """Test lazy cleanup on access"""
        key = "user:123:1"
        value = {"user_id": 123}
        short_ttl = 0.01  # 0.01 seconds for fast test
        
        await cache_manager_with_short_ttl.set(key, value, ttl=short_ttl)
        
        # Wait for TTL expiration (0.01 sec + small margin)
        await asyncio.sleep(0.02)
        
        # Lazy cleanup should occur on access (test BEHAVIOR)
        retrieved = await cache_manager_with_short_ttl.get(key)
        assert retrieved is None
        
        # Check that item is actually deleted
        assert await cache_manager_with_short_ttl.exists(key) is False
    
    async def test_explicit_ttl_override(self, cache_manager):
        """Test explicit TTL specification (override settings)"""
        key = "test:explicit_ttl"
        value = "test_value"
        explicit_ttl = 0.01  # 0.01 seconds (10 ms) for fast test
        
        await cache_manager.set(key, value, ttl=explicit_ttl)
        
        # Immediately available
        assert await cache_manager.get(key) == value
        
        # Wait for explicit TTL expiration (0.01 sec + small margin)
        await asyncio.sleep(0.02)
        
        # Value should expire
        assert await cache_manager.get(key) is None
    
    async def test_explicit_ttl_override_large(self, cache_manager):
        """Test explicit large TTL specification (eternal cache)"""
        key = "user:123:1"
        value = {"user_id": 123}
        large_ttl = 315360000  # 10 years
        
        # Set with explicit large TTL
        await cache_manager.set(key, value, ttl=large_ttl)
        
        # Check that expiration time exists
        assert key in cache_manager._cache_expires_at
        
        # Value should remain
        await asyncio.sleep(0.01)
        assert await cache_manager.get(key) == value
    
    async def test_default_ttl_when_not_specified(self, cache_manager):
        """Test default TTL when TTL not specified"""
        key = "test:123"
        value = "test_value"
        
        await cache_manager.set(key, value)  # TTL not specified
        
        # Default TTL should be set (3600 seconds)
        assert key in cache_manager._cache_expires_at
        
        # Value should be available immediately
        assert await cache_manager.get(key) == value
    
    async def test_ttl_refresh_on_set(self, cache_manager):
        """Test TTL refresh on overwrite"""
        key = "test:ttl_refresh"
        value1 = {"user_id": 123}
        value2 = {"user_id": 456}
        short_ttl = 0.05  # 50 ms for fast test
        
        await cache_manager.set(key, value1, ttl=short_ttl)
        
        # Wait almost to expiration (but not fully) - 40% of TTL
        await asyncio.sleep(0.02)
        
        # Overwrite value (TTL should update)
        await cache_manager.set(key, value2, ttl=short_ttl)
        
        # Wait a bit more (but not more than new TTL) - another 40% of new TTL
        await asyncio.sleep(0.02)
        
        # Value should be available (TTL updated)
        retrieved = await cache_manager.get(key)
        assert retrieved == value2
    
    async def test_multiple_keys_different_ttl(self, cache_manager):
        """Test working with multiple keys with different TTL"""
        # Eternal cache (large TTL)
        eternal_key = "bot:123"
        eternal_value = {"bot_id": 123}
        large_ttl = 315360000  # 10 years
        await cache_manager.set(eternal_key, eternal_value, ttl=large_ttl)
        
        # Cache with TTL (via explicit specification, short for fast test)
        ttl_key = "test:ttl"
        ttl_value = "ttl_value"
        short_ttl = 0.01  # 0.01 seconds
        await cache_manager.set(ttl_key, ttl_value, ttl=short_ttl)
        
        # Both should be available immediately
        assert await cache_manager.get(eternal_key) == eternal_value
        assert await cache_manager.get(ttl_key) == ttl_value
        
        # Wait for TTL expiration for second key (0.01 sec + small margin)
        await asyncio.sleep(0.02)
        
        # First should remain (eternal)
        assert await cache_manager.get(eternal_key) == eternal_value
        
        # Second should expire
        assert await cache_manager.get(ttl_key) is None
    
    async def test_ttl_after_delete(self, cache_manager):
        """Test that TTL is deleted when key is deleted"""
        key = "user:123:1"
        value = {"user_id": 123}
        
        await cache_manager.set(key, value)  # Uses default_ttl
        assert key in cache_manager._cache_expires_at
        
        await cache_manager.delete(key)
        
        # TTL should be deleted
        assert key not in cache_manager._cache
        assert key not in cache_manager._cache_expires_at

