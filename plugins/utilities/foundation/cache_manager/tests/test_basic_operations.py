"""
Tests for basic cache_manager operations (get, set, delete, exists)
"""
import pytest


@pytest.mark.asyncio
class TestBasicOperations:
    """Tests for basic cache operations"""
    
    async def test_set_and_get_simple_value(self, cache_manager):
        """Test setting and getting simple value"""
        key = "test:123"
        value = "test_value"
        
        result = await cache_manager.set(key, value)
        assert result is True
        
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_set_and_get_dict(self, cache_manager):
        """Test setting and getting dictionary"""
        key = "bot:123"
        value = {
            'bot_id': 123,
            'tenant_id': 1,
            'bot_token': 'token123',
            'bot_name': 'Test Bot'
        }
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert retrieved['bot_id'] == 123
        assert retrieved['bot_name'] == 'Test Bot'
    
    async def test_set_and_get_list(self, cache_manager):
        """Test setting and getting list"""
        key = "tenant:1:scenarios"
        value = ['scenario1', 'scenario2', 'scenario3']
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert len(retrieved) == 3
    
    async def test_set_and_get_none(self, cache_manager):
        """Test setting and getting None"""
        key = "test:none"
        value = None
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved is None
    
    async def test_set_and_get_empty_string(self, cache_manager):
        """Test setting and getting empty string"""
        key = "test:empty"
        value = ""
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == ""
    
    async def test_set_and_get_empty_dict(self, cache_manager):
        """Test setting and getting empty dictionary"""
        key = "test:empty_dict"
        value = {}
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == {}
        assert isinstance(retrieved, dict)
    
    async def test_set_and_get_empty_list(self, cache_manager):
        """Test setting and getting empty list"""
        key = "test:empty_list"
        value = []
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == []
        assert isinstance(retrieved, list)
    
    async def test_get_nonexistent_key(self, cache_manager):
        """Test getting non-existent key"""
        key = "test:nonexistent"
        
        retrieved = await cache_manager.get(key)
        assert retrieved is None
    
    async def test_delete_existing_key(self, cache_manager):
        """Test deleting existing key"""
        key = "test:delete"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.exists(key) is True
        
        result = await cache_manager.delete(key)
        assert result is True
        
        assert await cache_manager.exists(key) is False
        assert await cache_manager.get(key) is None
    
    async def test_delete_nonexistent_key(self, cache_manager):
        """Test deleting non-existent key"""
        key = "test:nonexistent"
        
        result = await cache_manager.delete(key)
        assert result is False
    
    async def test_exists_existing_key(self, cache_manager):
        """Test existence of existing key"""
        key = "test:exists"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.exists(key) is True
    
    async def test_exists_nonexistent_key(self, cache_manager):
        """Test existence of non-existent key"""
        key = "test:nonexistent"
        
        assert await cache_manager.exists(key) is False
    
    async def test_overwrite_existing_key(self, cache_manager):
        """Test overwriting existing key"""
        key = "test:overwrite"
        value1 = "value1"
        value2 = "value2"
        
        await cache_manager.set(key, value1)
        assert await cache_manager.get(key) == value1
        
        await cache_manager.set(key, value2)
        assert await cache_manager.get(key) == value2
        assert await cache_manager.get(key) != value1
    
    async def test_multiple_keys(self, cache_manager):
        """Test working with multiple keys"""
        keys_values = {
            "bot:1": {"bot_id": 1},
            "bot:2": {"bot_id": 2},
            "bot:3": {"bot_id": 3},
            "user:1:1": {"user_id": 1, "tenant_id": 1},
            "user:2:1": {"user_id": 2, "tenant_id": 1},
        }
        
        # Set all keys
        for key, value in keys_values.items():
            await cache_manager.set(key, value)
        
        # Check all keys
        for key, expected_value in keys_values.items():
            retrieved = await cache_manager.get(key)
            assert retrieved == expected_value
    
    async def test_special_characters_in_key(self, cache_manager):
        """Test working with special characters in key"""
        key = "test:key-with-dashes:123"
        value = "test_value"
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_unicode_in_key(self, cache_manager):
        """Test working with unicode characters in key"""
        key = "test:key:test"
        value = "test_value"
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_unicode_in_value(self, cache_manager):
        """Test working with unicode characters in value"""
        key = "test:unicode"
        value = "Test value 🚀"
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_large_value(self, cache_manager):
        """Test working with large value"""
        key = "test:large"
        value = {"data": ["item"] * 1000}
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert len(retrieved["data"]) == 1000
    
    async def test_nested_structure(self, cache_manager):
        """Test working with nested structures"""
        key = "tenant:1:scenarios"
        value = {
            'search_tree': {
                'message': {
                    'text': ['scenario1', 'scenario2']
                }
            },
            'scenario_index': {
                'scenario1': {'id': 1, 'name': 'Scenario 1'},
                'scenario2': {'id': 2, 'name': 'Scenario 2'}
            }
        }
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert retrieved['search_tree']['message']['text'] == ['scenario1', 'scenario2']
        assert retrieved['scenario_index']['scenario1']['id'] == 1

