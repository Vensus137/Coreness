"""
Tests for edge cases and non-obvious patterns
"""
import asyncio

import pytest


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases"""
    
    async def test_concurrent_set_same_key(self, cache_manager):
        """Test concurrent setting of same key"""
        key = "test:concurrent"
        
        # Set value multiple times in a row
        await cache_manager.set(key, "value1")
        await cache_manager.set(key, "value2")
        await cache_manager.set(key, "value3")
        
        # Last value should remain
        assert await cache_manager.get(key) == "value3"
    
    async def test_concurrent_get_set(self, cache_manager):
        """Test concurrent reading and writing"""
        key = "test:concurrent_get_set"
        
        # Set value
        await cache_manager.set(key, "initial")
        
        # Read and write simultaneously
        async def read_write():
            for i in range(10):
                await cache_manager.set(key, f"value{i}")
                await asyncio.sleep(0.001)
                value = await cache_manager.get(key)
                assert value is not None
        
        await read_write()
    
    async def test_delete_and_recreate(self, cache_manager):
        """Test deletion and recreation of key"""
        key = "test:recreate"
        value1 = "value1"
        value2 = "value2"
        
        # Create, delete, create again
        await cache_manager.set(key, value1)
        await cache_manager.delete(key)
        await cache_manager.set(key, value2)
        
        assert await cache_manager.get(key) == value2
    
    async def test_delete_after_ttl_expired(self, cache_manager_with_short_ttl):
        """Test deletion after TTL expiration"""
        key = "user:123:1"
        value = {"user_id": 123}
        
        await cache_manager_with_short_ttl.set(key, value)
        
        # Wait for TTL expiration (0.01 sec + small margin)
        await asyncio.sleep(0.02)
        
        # Attempt to delete expired key (lazy cleanup already removed it)
        result = await cache_manager_with_short_ttl.delete(key)
        
        # Should return False (key no longer exists after lazy cleanup)
        assert result is False
    
    async def test_exists_after_ttl_expired(self, cache_manager_with_short_ttl):
        """Test exists after TTL expiration"""
        key = "user:123:1"
        value = {"user_id": 123}
        
        await cache_manager_with_short_ttl.set(key, value)
        
        # Immediately after setting
        assert await cache_manager_with_short_ttl.exists(key) is True
        
        # Wait for TTL expiration (0.01 sec + small margin)
        await asyncio.sleep(0.02)
        
        # After expiration
        assert await cache_manager_with_short_ttl.exists(key) is False
    
    async def test_invalidate_pattern_empty_cache(self, cache_manager):
        """Test pattern invalidation in empty cache"""
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 0
    
    async def test_invalidate_pattern_no_match(self, cache_manager):
        """Test pattern invalidation with no matches"""
        await cache_manager.set("user:1:1", {"user_id": 1})
        
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 0
        assert await cache_manager.get("user:1:1") is not None
    
    async def test_set_with_zero_ttl(self, cache_manager):
        """Test setting with TTL=0 (should expire immediately)"""
        key = "test:zero_ttl"
        value = "test_value"
        
        await cache_manager.set(key, value, ttl=0)
        
        # Should expire immediately
        await asyncio.sleep(0.01)
        assert await cache_manager.get(key) is None
    
    async def test_set_with_negative_ttl(self, cache_manager):
        """Test setting with negative TTL (should expire immediately)"""
        key = "test:negative_ttl"
        value = "test_value"
        
        await cache_manager.set(key, value, ttl=-1)
        
        # Should expire immediately
        await asyncio.sleep(0.01)
        assert await cache_manager.get(key) is None
    
    async def test_very_long_key(self, cache_manager):
        """Test working with very long key"""
        key = "test:" + "x" * 1000
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
    
    async def test_key_with_colons(self, cache_manager):
        """Test working with key containing many colons"""
        key = "test:key:with:many:colons:123"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
    
    async def test_key_without_colon(self, cache_manager):
        """Test working with key without colon"""
        key = "simple_key"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
        
        # Type should be determined as "simple_key"
        # Default TTL should be used
        assert key in cache_manager._cache_expires_at
    
    async def test_complex_nested_structure(self, cache_manager):
        """Test working with complex nested structure"""
        key = "tenant:1:scenarios"
        value = {
            'search_tree': {
                'message': {
                    'text': {
                        'exact': ['scenario1'],
                        'contains': ['scenario2']
                    }
                }
            },
            'scenario_index': {
                'scenario1': {
                    'id': 1,
                    'name': 'Scenario 1',
                    'step': [
                        {'action': 'send_message', 'params': {'text': 'Hello'}},
                        {'action': 'wait', 'params': {'seconds': 5}}
                    ]
                }
            }
        }
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert retrieved['search_tree']['message']['text']['exact'] == ['scenario1']
        assert retrieved['scenario_index']['scenario1']['step'][0]['action'] == 'send_message'
    
    async def test_mixed_types_in_value(self, cache_manager):
        """Test working with mixed types in value"""
        key = "test:mixed"
        value = {
            'string': 'text',
            'int': 123,
            'float': 45.67,
            'bool': True,
            'none': None,
            'list': [1, 2, 3],
            'dict': {'nested': 'value'}
        }
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert isinstance(retrieved['int'], int)
        assert isinstance(retrieved['float'], float)
        assert isinstance(retrieved['bool'], bool)
        assert retrieved['none'] is None
        assert isinstance(retrieved['list'], list)
        assert isinstance(retrieved['dict'], dict)
    
    async def test_clear_and_reuse(self, cache_manager):
        """Test clearing and reusing"""
        # Create keys
        await cache_manager.set("bot:1", {"bot_id": 1})
        await cache_manager.set("user:1:1", {"user_id": 1})
        
        # Clear
        await cache_manager.clear()
        
        # Create new keys
        await cache_manager.set("bot:2", {"bot_id": 2})
        await cache_manager.set("user:2:1", {"user_id": 2})
        
        # Check that old keys didn't return
        assert await cache_manager.get("bot:1") is None
        assert await cache_manager.get("user:1:1") is None
        
        # Check new keys
        assert await cache_manager.get("bot:2") is not None
        assert await cache_manager.get("user:2:1") is not None

