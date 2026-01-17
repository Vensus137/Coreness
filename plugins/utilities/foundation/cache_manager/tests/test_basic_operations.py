"""
Тесты базовых операций cache_manager (get, set, delete, exists)
"""
import pytest


@pytest.mark.asyncio
class TestBasicOperations:
    """Тесты базовых операций с кэшем"""
    
    async def test_set_and_get_simple_value(self, cache_manager):
        """Проверка установки и получения простого значения"""
        key = "test:123"
        value = "test_value"
        
        result = await cache_manager.set(key, value)
        assert result is True
        
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_set_and_get_dict(self, cache_manager):
        """Проверка установки и получения словаря"""
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
        """Проверка установки и получения списка"""
        key = "tenant:1:scenarios"
        value = ['scenario1', 'scenario2', 'scenario3']
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert len(retrieved) == 3
    
    async def test_set_and_get_none(self, cache_manager):
        """Проверка установки и получения None"""
        key = "test:none"
        value = None
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved is None
    
    async def test_set_and_get_empty_string(self, cache_manager):
        """Проверка установки и получения пустой строки"""
        key = "test:empty"
        value = ""
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == ""
    
    async def test_set_and_get_empty_dict(self, cache_manager):
        """Проверка установки и получения пустого словаря"""
        key = "test:empty_dict"
        value = {}
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == {}
        assert isinstance(retrieved, dict)
    
    async def test_set_and_get_empty_list(self, cache_manager):
        """Проверка установки и получения пустого списка"""
        key = "test:empty_list"
        value = []
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == []
        assert isinstance(retrieved, list)
    
    async def test_get_nonexistent_key(self, cache_manager):
        """Проверка получения несуществующего ключа"""
        key = "test:nonexistent"
        
        retrieved = await cache_manager.get(key)
        assert retrieved is None
    
    async def test_delete_existing_key(self, cache_manager):
        """Проверка удаления существующего ключа"""
        key = "test:delete"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.exists(key) is True
        
        result = await cache_manager.delete(key)
        assert result is True
        
        assert await cache_manager.exists(key) is False
        assert await cache_manager.get(key) is None
    
    async def test_delete_nonexistent_key(self, cache_manager):
        """Проверка удаления несуществующего ключа"""
        key = "test:nonexistent"
        
        result = await cache_manager.delete(key)
        assert result is False
    
    async def test_exists_existing_key(self, cache_manager):
        """Проверка существования существующего ключа"""
        key = "test:exists"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.exists(key) is True
    
    async def test_exists_nonexistent_key(self, cache_manager):
        """Проверка существования несуществующего ключа"""
        key = "test:nonexistent"
        
        assert await cache_manager.exists(key) is False
    
    async def test_overwrite_existing_key(self, cache_manager):
        """Проверка перезаписи существующего ключа"""
        key = "test:overwrite"
        value1 = "value1"
        value2 = "value2"
        
        await cache_manager.set(key, value1)
        assert await cache_manager.get(key) == value1
        
        await cache_manager.set(key, value2)
        assert await cache_manager.get(key) == value2
        assert await cache_manager.get(key) != value1
    
    async def test_multiple_keys(self, cache_manager):
        """Проверка работы с множественными ключами"""
        keys_values = {
            "bot:1": {"bot_id": 1},
            "bot:2": {"bot_id": 2},
            "bot:3": {"bot_id": 3},
            "user:1:1": {"user_id": 1, "tenant_id": 1},
            "user:2:1": {"user_id": 2, "tenant_id": 1},
        }
        
        # Устанавливаем все ключи
        for key, value in keys_values.items():
            await cache_manager.set(key, value)
        
        # Проверяем все ключи
        for key, expected_value in keys_values.items():
            retrieved = await cache_manager.get(key)
            assert retrieved == expected_value
    
    async def test_special_characters_in_key(self, cache_manager):
        """Проверка работы с специальными символами в ключе"""
        key = "test:key-with-dashes:123"
        value = "test_value"
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_unicode_in_key(self, cache_manager):
        """Проверка работы с unicode символами в ключе"""
        key = "test:ключ:тест"
        value = "test_value"
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_unicode_in_value(self, cache_manager):
        """Проверка работы с unicode символами в значении"""
        key = "test:unicode"
        value = "Тестовое значение 🚀"
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
    
    async def test_large_value(self, cache_manager):
        """Проверка работы с большим значением"""
        key = "test:large"
        value = {"data": ["item"] * 1000}
        
        await cache_manager.set(key, value)
        retrieved = await cache_manager.get(key)
        
        assert retrieved == value
        assert len(retrieved["data"]) == 1000
    
    async def test_nested_structure(self, cache_manager):
        """Проверка работы с вложенными структурами"""
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

