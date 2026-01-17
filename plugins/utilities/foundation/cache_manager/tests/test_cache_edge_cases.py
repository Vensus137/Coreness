"""
Тесты граничных случаев и неочевидных паттернов
"""
import asyncio

import pytest


@pytest.mark.asyncio
class TestEdgeCases:
    """Тесты граничных случаев"""
    
    async def test_concurrent_set_same_key(self, cache_manager):
        """Проверка конкурентной установки одного ключа"""
        key = "test:concurrent"
        
        # Устанавливаем значение несколько раз подряд
        await cache_manager.set(key, "value1")
        await cache_manager.set(key, "value2")
        await cache_manager.set(key, "value3")
        
        # Должно остаться последнее значение
        assert await cache_manager.get(key) == "value3"
    
    async def test_concurrent_get_set(self, cache_manager):
        """Проверка конкурентного чтения и записи"""
        key = "test:concurrent_get_set"
        
        # Устанавливаем значение
        await cache_manager.set(key, "initial")
        
        # Читаем и записываем одновременно
        async def read_write():
            for i in range(10):
                await cache_manager.set(key, f"value{i}")
                await asyncio.sleep(0.001)
                value = await cache_manager.get(key)
                assert value is not None
        
        await read_write()
    
    async def test_delete_and_recreate(self, cache_manager):
        """Проверка удаления и повторного создания ключа"""
        key = "test:recreate"
        value1 = "value1"
        value2 = "value2"
        
        # Создаем, удаляем, создаем снова
        await cache_manager.set(key, value1)
        await cache_manager.delete(key)
        await cache_manager.set(key, value2)
        
        assert await cache_manager.get(key) == value2
    
    async def test_delete_after_ttl_expired(self, cache_manager_with_short_ttl):
        """Проверка удаления после истечения TTL"""
        key = "user:123:1"
        value = {"user_id": 123}
        
        await cache_manager_with_short_ttl.set(key, value)
        
        # Ждем истечения TTL (0.01 сек + небольшой запас)
        await asyncio.sleep(0.02)
        
        # Попытка удаления истекшего ключа (ленивая очистка уже удалила)
        result = await cache_manager_with_short_ttl.delete(key)
        
        # Должно вернуть False (ключ уже не существует после ленивой очистки)
        assert result is False
    
    async def test_exists_after_ttl_expired(self, cache_manager_with_short_ttl):
        """Проверка exists после истечения TTL"""
        key = "user:123:1"
        value = {"user_id": 123}
        
        await cache_manager_with_short_ttl.set(key, value)
        
        # Сразу после установки
        assert await cache_manager_with_short_ttl.exists(key) is True
        
        # Ждем истечения TTL (0.01 сек + небольшой запас)
        await asyncio.sleep(0.02)
        
        # После истечения
        assert await cache_manager_with_short_ttl.exists(key) is False
    
    async def test_invalidate_pattern_empty_cache(self, cache_manager):
        """Проверка инвалидации паттерна в пустом кэше"""
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 0
    
    async def test_invalidate_pattern_no_match(self, cache_manager):
        """Проверка инвалидации паттерна без совпадений"""
        await cache_manager.set("user:1:1", {"user_id": 1})
        
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 0
        assert await cache_manager.get("user:1:1") is not None
    
    async def test_set_with_zero_ttl(self, cache_manager):
        """Проверка установки с TTL=0 (должен истечь сразу)"""
        key = "test:zero_ttl"
        value = "test_value"
        
        await cache_manager.set(key, value, ttl=0)
        
        # Должен истечь сразу
        await asyncio.sleep(0.01)
        assert await cache_manager.get(key) is None
    
    async def test_set_with_negative_ttl(self, cache_manager):
        """Проверка установки с отрицательным TTL (должен истечь сразу)"""
        key = "test:negative_ttl"
        value = "test_value"
        
        await cache_manager.set(key, value, ttl=-1)
        
        # Должен истечь сразу
        await asyncio.sleep(0.01)
        assert await cache_manager.get(key) is None
    
    async def test_very_long_key(self, cache_manager):
        """Проверка работы с очень длинным ключом"""
        key = "test:" + "x" * 1000
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
    
    async def test_key_with_colons(self, cache_manager):
        """Проверка работы с ключом содержащим множество двоеточий"""
        key = "test:key:with:many:colons:123"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
    
    async def test_key_without_colon(self, cache_manager):
        """Проверка работы с ключом без двоеточия"""
        key = "simple_key"
        value = "test_value"
        
        await cache_manager.set(key, value)
        assert await cache_manager.get(key) == value
        
        # Тип должен определяться как "simple_key"
        # Должен использоваться дефолтный TTL
        assert key in cache_manager._cache_expires_at
    
    async def test_complex_nested_structure(self, cache_manager):
        """Проверка работы со сложной вложенной структурой"""
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
        """Проверка работы со смешанными типами в значении"""
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
        """Проверка очистки и повторного использования"""
        # Создаем ключи
        await cache_manager.set("bot:1", {"bot_id": 1})
        await cache_manager.set("user:1:1", {"user_id": 1})
        
        # Очищаем
        await cache_manager.clear()
        
        # Создаем новые ключи
        await cache_manager.set("bot:2", {"bot_id": 2})
        await cache_manager.set("user:2:1", {"user_id": 2})
        
        # Проверяем, что старые ключи не вернулись
        assert await cache_manager.get("bot:1") is None
        assert await cache_manager.get("user:1:1") is None
        
        # Проверяем новые ключи
        assert await cache_manager.get("bot:2") is not None
        assert await cache_manager.get("user:2:1") is not None

