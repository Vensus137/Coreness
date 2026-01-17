"""
Тесты TTL (время жизни кэша)
"""
import asyncio

import pytest


@pytest.mark.asyncio
class TestTTL:
    """Тесты TTL функциональности"""
    
    async def test_eternal_cache_large_ttl(self, cache_manager):
        """Проверка вечного кэша (большой TTL)"""
        key = "bot:123"
        value = {"bot_id": 123}
        large_ttl = 315360000  # 10 лет
        
        await cache_manager.set(key, value, ttl=large_ttl)
        
        # Ждем немного
        await asyncio.sleep(0.01)
        
        # Значение должно остаться (тестируем ПОВЕДЕНИЕ, а не внутренние данные)
        retrieved = await cache_manager.get(key)
        assert retrieved == value
        
        # Проверяем, что ключ существует
        assert await cache_manager.exists(key) is True
    
    async def test_ttl_expiration(self, cache_manager_with_short_ttl):
        """Проверка истечения TTL"""
        key = "user:123:1"
        value = {"user_id": 123}
        short_ttl = 0.01  # 0.01 секунды для быстрого теста
        
        await cache_manager_with_short_ttl.set(key, value, ttl=short_ttl)
        
        # Сразу после установки значение должно быть доступно
        retrieved = await cache_manager_with_short_ttl.get(key)
        assert retrieved == value
        
        # Ждем истечения TTL (0.01 сек + небольшой запас)
        await asyncio.sleep(0.02)
        
        # Значение должно истечь
        retrieved = await cache_manager_with_short_ttl.get(key)
        assert retrieved is None
        assert await cache_manager_with_short_ttl.exists(key) is False
    
    async def test_lazy_cleanup_on_get(self, cache_manager_with_short_ttl):
        """Проверка ленивой очистки при обращении"""
        key = "user:123:1"
        value = {"user_id": 123}
        short_ttl = 0.01  # 0.01 секунды для быстрого теста
        
        await cache_manager_with_short_ttl.set(key, value, ttl=short_ttl)
        
        # Ждем истечения TTL (0.01 сек + небольшой запас)
        await asyncio.sleep(0.02)
        
        # При обращении должна произойти ленивая очистка (тестируем ПОВЕДЕНИЕ)
        retrieved = await cache_manager_with_short_ttl.get(key)
        assert retrieved is None
        
        # Проверяем, что элемент действительно удален
        assert await cache_manager_with_short_ttl.exists(key) is False
    
    async def test_explicit_ttl_override(self, cache_manager):
        """Проверка явного указания TTL (переопределение настроек)"""
        key = "test:explicit_ttl"
        value = "test_value"
        explicit_ttl = 0.01  # 0.01 секунды (10 мс) для быстрого теста
        
        await cache_manager.set(key, value, ttl=explicit_ttl)
        
        # Сразу доступно
        assert await cache_manager.get(key) == value
        
        # Ждем истечения явного TTL (0.01 сек + небольшой запас)
        await asyncio.sleep(0.02)
        
        # Значение должно истечь
        assert await cache_manager.get(key) is None
    
    async def test_explicit_ttl_override_large(self, cache_manager):
        """Проверка явного указания большого TTL (вечный кэш)"""
        key = "user:123:1"
        value = {"user_id": 123}
        large_ttl = 315360000  # 10 лет
        
        # Устанавливаем с явным большим TTL
        await cache_manager.set(key, value, ttl=large_ttl)
        
        # Проверяем, что есть время истечения
        assert key in cache_manager._cache_expires_at
        
        # Значение должно остаться
        await asyncio.sleep(0.01)
        assert await cache_manager.get(key) == value
    
    async def test_default_ttl_when_not_specified(self, cache_manager):
        """Проверка дефолтного TTL когда TTL не указан"""
        key = "test:123"
        value = "test_value"
        
        await cache_manager.set(key, value)  # TTL не указан
        
        # Должен быть установлен дефолтный TTL (3600 секунд)
        assert key in cache_manager._cache_expires_at
        
        # Значение должно быть доступно сразу
        assert await cache_manager.get(key) == value
    
    async def test_ttl_refresh_on_set(self, cache_manager):
        """Проверка обновления TTL при перезаписи"""
        key = "test:ttl_refresh"
        value1 = {"user_id": 123}
        value2 = {"user_id": 456}
        short_ttl = 0.05  # 50 мс для быстрого теста
        
        await cache_manager.set(key, value1, ttl=short_ttl)
        
        # Ждем почти истечения (но не полностью) - 40% от TTL
        await asyncio.sleep(0.02)
        
        # Перезаписываем значение (TTL должен обновиться)
        await cache_manager.set(key, value2, ttl=short_ttl)
        
        # Ждем еще немного (но не больше нового TTL) - еще 40% от нового TTL
        await asyncio.sleep(0.02)
        
        # Значение должно быть доступно (TTL обновился)
        retrieved = await cache_manager.get(key)
        assert retrieved == value2
    
    async def test_multiple_keys_different_ttl(self, cache_manager):
        """Проверка работы с множественными ключами с разным TTL"""
        # Вечный кэш (большой TTL)
        eternal_key = "bot:123"
        eternal_value = {"bot_id": 123}
        large_ttl = 315360000  # 10 лет
        await cache_manager.set(eternal_key, eternal_value, ttl=large_ttl)
        
        # Кэш с TTL (через явное указание, короткий для быстрого теста)
        ttl_key = "test:ttl"
        ttl_value = "ttl_value"
        short_ttl = 0.01  # 0.01 секунды
        await cache_manager.set(ttl_key, ttl_value, ttl=short_ttl)
        
        # Оба должны быть доступны сразу
        assert await cache_manager.get(eternal_key) == eternal_value
        assert await cache_manager.get(ttl_key) == ttl_value
        
        # Ждем истечения TTL для второго ключа (0.01 сек + небольшой запас)
        await asyncio.sleep(0.02)
        
        # Первый должен остаться (вечный)
        assert await cache_manager.get(eternal_key) == eternal_value
        
        # Второй должен истечь
        assert await cache_manager.get(ttl_key) is None
    
    async def test_ttl_after_delete(self, cache_manager):
        """Проверка, что TTL удаляется при удалении ключа"""
        key = "user:123:1"
        value = {"user_id": 123}
        
        await cache_manager.set(key, value)  # Используется default_ttl
        assert key in cache_manager._cache_expires_at
        
        await cache_manager.delete(key)
        
        # TTL должен быть удален
        assert key not in cache_manager._cache
        assert key not in cache_manager._cache_expires_at

