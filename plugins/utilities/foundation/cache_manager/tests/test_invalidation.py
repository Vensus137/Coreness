"""
Тесты инвалидации кэша по паттернам
"""
import pytest


@pytest.mark.asyncio
class TestInvalidation:
    """Тесты инвалидации кэша"""
    
    async def test_invalidate_pattern_prefix(self, cache_manager):
        """Проверка инвалидации по префиксу (bot:*)"""
        # Создаем несколько ключей с префиксом bot:
        keys = [
            "bot:1", "bot:2", "bot:3",
            "user:1:1", "user:2:1",  # Другие ключи
        ]
        
        for key in keys:
            await cache_manager.set(key, {"id": key})
        
        # Инвалидируем все ключи с префиксом bot:
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 3
        
        # Проверяем, что bot: ключи удалены
        assert await cache_manager.get("bot:1") is None
        assert await cache_manager.get("bot:2") is None
        assert await cache_manager.get("bot:3") is None
        
        # Проверяем, что другие ключи остались
        assert await cache_manager.get("user:1:1") is not None
        assert await cache_manager.get("user:2:1") is not None
    
    async def test_invalidate_pattern_suffix(self, cache_manager):
        """Проверка инвалидации по суффиксу (*:meta)"""
        keys = [
            "tenant:1:meta",
            "tenant:2:meta",
            "tenant:1:scenarios",  # Другой суффикс
            "bot:1",  # Другой префикс
        ]
        
        for key in keys:
            await cache_manager.set(key, {"data": key})
        
        # Инвалидируем все ключи с суффиксом :meta
        deleted_count = await cache_manager.invalidate_pattern("*:meta")
        
        assert deleted_count == 2
        
        # Проверяем удаление
        assert await cache_manager.get("tenant:1:meta") is None
        assert await cache_manager.get("tenant:2:meta") is None
        
        # Проверяем, что другие ключи остались
        assert await cache_manager.get("tenant:1:scenarios") is not None
        assert await cache_manager.get("bot:1") is not None
    
    async def test_invalidate_pattern_middle(self, cache_manager):
        """Проверка инвалидации по паттерну с * в середине"""
        keys = [
            "tenant:1:meta",
            "tenant:1:scenarios",
            "tenant:2:meta",
            "bot:1:meta",  # Другой префикс
        ]
        
        for key in keys:
            await cache_manager.set(key, {"data": key})
        
        # Инвалидируем tenant:*:meta
        deleted_count = await cache_manager.invalidate_pattern("tenant:*:meta")
        
        assert deleted_count == 2
        
        # Проверяем удаление
        assert await cache_manager.get("tenant:1:meta") is None
        assert await cache_manager.get("tenant:2:meta") is None
        
        # Проверяем, что другие ключи остались
        assert await cache_manager.get("tenant:1:scenarios") is not None
        assert await cache_manager.get("bot:1:meta") is not None
    
    async def test_invalidate_pattern_exact_match(self, cache_manager):
        """Проверка инвалидации точного совпадения"""
        key = "test:exact"
        await cache_manager.set(key, {"data": "value"})
        
        # Инвалидируем точное совпадение
        deleted_count = await cache_manager.invalidate_pattern("test:exact")
        
        assert deleted_count == 1
        assert await cache_manager.get(key) is None
    
    async def test_invalidate_pattern_nonexistent(self, cache_manager):
        """Проверка инвалидации несуществующего паттерна"""
        deleted_count = await cache_manager.invalidate_pattern("nonexistent:*")
        
        assert deleted_count == 0
    
    async def test_invalidate_pattern_with_ttl(self, cache_manager):
        """Проверка инвалидации ключей с TTL"""
        # Создаем ключи с TTL
        keys = ["user:1:1", "user:2:1", "user:3:1"]
        for key in keys:
            await cache_manager.set(key, {"user_id": key}, ttl=60)
        
        # Инвалидируем
        deleted_count = await cache_manager.invalidate_pattern("user:*")
        
        assert deleted_count == 3
        
        # Проверяем, что TTL тоже удалены
        for key in keys:
            assert key not in cache_manager._cache
            assert key not in cache_manager._cache_expires_at
    
    async def test_invalidate_pattern_with_eternal_cache(self, cache_manager):
        """Проверка инвалидации вечных кэшей"""
        # Создаем вечные кэши
        keys = ["bot:1", "bot:2", "bot:3"]
        for key in keys:
            await cache_manager.set(key, {"bot_id": key})
        
        # Инвалидируем
        deleted_count = await cache_manager.invalidate_pattern("bot:*")
        
        assert deleted_count == 3
        
        # Проверяем удаление
        for key in keys:
            assert await cache_manager.get(key) is None
    
    async def test_clear_all_cache(self, cache_manager):
        """Проверка очистки всего кэша"""
        # Создаем множество ключей
        keys = [
            "bot:1", "bot:2",
            "user:1:1", "user:2:1",
            "tenant:1:meta", "tenant:1:scenarios",
        ]
        
        for key in keys:
            await cache_manager.set(key, {"data": key})
        
        # Очищаем весь кэш
        result = await cache_manager.clear()
        
        assert result is True
        
        # Проверяем, что все ключи удалены
        for key in keys:
            assert await cache_manager.get(key) is None
        
        # Проверяем, что кэш пуст
        assert len(cache_manager._cache) == 0
        assert len(cache_manager._cache_expires_at) == 0
    
    async def test_clear_empty_cache(self, cache_manager):
        """Проверка очистки пустого кэша"""
        result = await cache_manager.clear()
        
        assert result is True
        assert len(cache_manager._cache) == 0

