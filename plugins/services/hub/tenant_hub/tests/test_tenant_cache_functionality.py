"""
Тесты функциональности TenantCache с проверкой кэширования
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
class TestTenantCacheFunctionality:
    """Тесты кэширования в TenantCache"""
    
    async def test_get_bot_by_tenant_id_uses_cache_on_second_request(self, tenant_cache, mock_master_repository):
        """Проверка: при повторном запросе данные берутся из кэша (не из БД)"""
        # Подготавливаем данные
        tenant_id = 1
        bot_id = 1
        bot_data = {
            'id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token',
            'telegram_bot_id': 123456,
            'username': 'test_bot',
            'first_name': 'Test Bot',
            'is_active': True
        }
        
        # Настраиваем мок для возврата данных
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # Первый запрос - должен вызвать get_bot_by_tenant_id
        result1 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        
        # Проверяем, что master_repository был вызван
        mock_master_repository.get_bot_by_tenant_id.assert_called_once_with(tenant_id)
        assert result1 is not None
        # Всегда структурированные данные с 'bot_id'
        assert result1['bot_id'] == bot_id
        assert result1['tenant_id'] == tenant_id
        
        # Проверяем, что маппинг сохранен в кэше
        tenant_bot_id_key = tenant_cache._get_tenant_bot_id_key(tenant_id)
        cached_bot_id = await tenant_cache.cache_manager.get(tenant_bot_id_key)
        assert cached_bot_id == bot_id
        
        # Сохраняем структурированные данные в кэше (как это делает BotInfoManager)
        # чтобы второй запрос использовал их вместо обращения к БД
        bot_cache_key = tenant_cache._get_bot_cache_key(bot_id)
        structured_bot_info = {
            'bot_id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token',
            'telegram_bot_id': 123456,
            'username': 'test_bot',
            'first_name': 'Test Bot',
            'is_active': True,
            'bot_command': []
        }
        await tenant_cache.cache_manager.set(bot_cache_key, structured_bot_info, ttl=315360000)
        
        # Сбрасываем счетчик вызовов
        mock_master_repository.get_bot_by_tenant_id.reset_mock()
        
        # Второй запрос - должен использовать кэш маппинга и структурированные данные
        result2 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        
        # Проверяем, что master_repository НЕ был вызван повторно
        mock_master_repository.get_bot_by_tenant_id.assert_not_called()
        
        # Проверяем, что результат тот же (из кэша)
        # Всегда структурированные данные с 'bot_id'
        assert result2 is not None
        assert result2['bot_id'] == bot_id
        assert result2['tenant_id'] == tenant_id
    
    async def test_get_bot_id_by_tenant_id_uses_cache(self, tenant_cache, mock_master_repository):
        """Проверка: get_bot_id_by_tenant_id использует кэш"""
        # Подготавливаем данные
        tenant_id = 1
        bot_id = 123
        bot_data = {
            'id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token'
        }
        
        # Настраиваем мок
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # Первый запрос
        result1 = await tenant_cache.get_bot_id_by_tenant_id(tenant_id)
        assert result1 == bot_id
        
        # Сохраняем структурированные данные в кэше (как это делает BotInfoManager)
        # чтобы второй запрос использовал их вместо обращения к БД
        bot_cache_key = tenant_cache._get_bot_cache_key(bot_id)
        structured_bot_info = {
            'bot_id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token',
            'bot_command': []
        }
        await tenant_cache.cache_manager.set(bot_cache_key, structured_bot_info, ttl=315360000)
        
        # Сбрасываем счетчик
        mock_master_repository.get_bot_by_tenant_id.reset_mock()
        
        # Второй запрос - должен использовать кэш
        result2 = await tenant_cache.get_bot_id_by_tenant_id(tenant_id)
        
        # Проверяем, что master_repository НЕ был вызван повторно
        mock_master_repository.get_bot_by_tenant_id.assert_not_called()
        assert result2 == bot_id
    
    async def test_invalidate_bot_cache_clears_cache(self, tenant_cache, mock_master_repository):
        """Проверка: invalidate_bot_cache очищает маппинг tenant -> bot_id"""
        # Подготавливаем данные
        tenant_id = 1
        bot_id = 1
        bot_data = {
            'id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token'
        }
        
        # Настраиваем мок
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # Первый запрос - загружает в кэш маппинг
        result1 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        assert result1 is not None
        
        # Проверяем, что маппинг сохранен в кэше
        tenant_bot_id_key = tenant_cache._get_tenant_bot_id_key(tenant_id)
        cached_bot_id = await tenant_cache.cache_manager.get(tenant_bot_id_key)
        assert cached_bot_id == bot_id
        
        # Инвалидируем кэш
        await tenant_cache.invalidate_bot_cache(tenant_id)
        
        # Проверяем, что маппинг очищен
        cached_bot_id_after = await tenant_cache.cache_manager.get(tenant_bot_id_key)
        assert cached_bot_id_after is None
        
        # Сбрасываем счетчик
        mock_master_repository.get_bot_by_tenant_id.reset_mock()
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # Второй запрос - должен загрузить из БД снова
        result2 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        
        # Проверяем, что master_repository был вызван снова
        mock_master_repository.get_bot_by_tenant_id.assert_called_once()
        assert result2 is not None
    
    async def test_set_last_updated_saves_metadata(self, tenant_cache, mock_datetime_formatter):
        """Проверка: set_last_updated сохраняет метаданные обновления"""
        tenant_id = 1
        mock_datetime = MagicMock()
        mock_datetime_formatter.now_local_tz = AsyncMock(return_value=mock_datetime)
        mock_datetime_formatter.to_string = AsyncMock(return_value='2024-01-01T12:00:00+00:00')
        
        # Устанавливаем метаданные
        await tenant_cache.set_last_updated(tenant_id)
        
        # Получаем метаданные
        cache_meta = await tenant_cache.get_tenant_cache(tenant_id)
        
        # Проверяем, что метаданные сохранены
        assert 'last_updated_at' in cache_meta
        assert cache_meta['last_updated_at'] == '2024-01-01T12:00:00+00:00'
        assert 'last_error' not in cache_meta
        assert 'last_failed_at' not in cache_meta
    
    async def test_set_last_failed_saves_error_metadata(self, tenant_cache, mock_datetime_formatter):
        """Проверка: set_last_failed сохраняет метаданные ошибки"""
        tenant_id = 1
        error = {
            'code': 'TEST_ERROR',
            'message': 'Test error message',
            'details': ['detail1', 'detail2']
        }
        
        mock_datetime = MagicMock()
        mock_datetime_formatter.now_local_tz = AsyncMock(return_value=mock_datetime)
        mock_datetime_formatter.to_string = AsyncMock(return_value='2024-01-01T12:00:00+00:00')
        
        # Устанавливаем метаданные ошибки
        await tenant_cache.set_last_failed(tenant_id, error)
        
        # Получаем метаданные
        cache_meta = await tenant_cache.get_tenant_cache(tenant_id)
        
        # Проверяем, что метаданные ошибки сохранены
        assert 'last_failed_at' in cache_meta
        assert cache_meta['last_failed_at'] == '2024-01-01T12:00:00+00:00'
        assert 'last_error' in cache_meta
        assert cache_meta['last_error']['code'] == 'TEST_ERROR'
        assert cache_meta['last_error']['message'] == 'Test error message'
        assert cache_meta['last_error']['details'] == ['detail1', 'detail2']
    
    async def test_get_tenant_cache_returns_metadata(self, tenant_cache, mock_datetime_formatter):
        """Проверка: get_tenant_cache возвращает метаданные тенанта"""
        tenant_id = 1
        
        # Устанавливаем метаданные
        mock_datetime = MagicMock()
        mock_datetime_formatter.now_local_tz = AsyncMock(return_value=mock_datetime)
        mock_datetime_formatter.to_string = AsyncMock(return_value='2024-01-01T12:00:00+00:00')
        
        await tenant_cache.set_last_updated(tenant_id)
        
        # Получаем метаданные
        cache_meta = await tenant_cache.get_tenant_cache(tenant_id)
        
        # Проверяем структуру метаданных
        assert isinstance(cache_meta, dict)
        assert 'last_updated_at' in cache_meta
        
        # Проверяем для несуществующего тенанта
        empty_meta = await tenant_cache.get_tenant_cache(999)
        assert isinstance(empty_meta, dict)
        assert len(empty_meta) == 0
    
    async def test_get_tenant_config_uses_cache_on_second_request(self, tenant_cache, mock_master_repository):
        """Проверка: get_tenant_config использует кэш при повторном запросе"""
        tenant_id = 1
        tenant_data = {
            'id': tenant_id,
            'openrouter_token': 'sk-test-token-123',
            'processed_at': '2024-01-01T00:00:00+00:00'
        }
        
        # Настраиваем мок для возврата данных
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=tenant_data)
        
        # Первый запрос - должен вызвать get_tenant_by_id
        result1 = await tenant_cache.get_tenant_config(tenant_id)
        
        # Проверяем, что master_repository был вызван
        mock_master_repository.get_tenant_by_id.assert_called_once_with(tenant_id)
        assert result1 is not None
        assert result1.get('openrouter_token') == 'sk-test-token-123'
        # Проверяем, что служебные поля исключены
        assert 'id' not in result1
        assert 'processed_at' not in result1
        
        # Сбрасываем счетчик вызовов
        mock_master_repository.get_tenant_by_id.reset_mock()
        
        # Второй запрос - должен использовать кэш
        result2 = await tenant_cache.get_tenant_config(tenant_id)
        
        # Проверяем, что master_repository НЕ был вызван повторно
        mock_master_repository.get_tenant_by_id.assert_not_called()
        
        # Проверяем, что результат тот же (из кэша)
        assert result2 is not None
        assert result2.get('openrouter_token') == 'sk-test-token-123'
    
    async def test_get_tenant_config_returns_none_for_missing_tenant(self, tenant_cache, mock_master_repository):
        """Проверка: get_tenant_config возвращает None для несуществующего тенанта"""
        tenant_id = 999
        
        # Настраиваем мок для возврата None
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=None)
        
        # Запрос
        result = await tenant_cache.get_tenant_config(tenant_id)
        
        # Проверяем, что вернулся None
        assert result is None
    
    async def test_get_tenant_config_excludes_service_fields(self, tenant_cache, mock_master_repository):
        """Проверка: get_tenant_config исключает служебные поля (id, processed_at)"""
        tenant_id = 1
        tenant_data = {
            'id': tenant_id,
            'openrouter_token': 'sk-test-token-123',
            'processed_at': '2024-01-01T00:00:00+00:00'
        }
        
        # Настраиваем мок
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=tenant_data)
        
        # Запрос
        result = await tenant_cache.get_tenant_config(tenant_id)
        
        # Проверяем, что служебные поля исключены
        assert result is not None
        assert 'id' not in result
        assert 'processed_at' not in result
        # Проверяем, что конфигурационные поля включены
        assert 'openrouter_token' in result
        assert result['openrouter_token'] == 'sk-test-token-123'
    
    async def test_get_tenant_config_excludes_none_values(self, tenant_cache, mock_master_repository):
        """Проверка: get_tenant_config исключает поля со значением None"""
        tenant_id = 1
        tenant_data = {
            'id': tenant_id,
            'openrouter_token': None,  # None значение
            'processed_at': '2024-01-01T00:00:00+00:00'
        }
        
        # Настраиваем мок
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=tenant_data)
        
        # Запрос
        result = await tenant_cache.get_tenant_config(tenant_id)
        
        # Проверяем, что None значения исключены
        assert result is not None
        assert 'openrouter_token' not in result
        # Проверяем, что словарь может быть пустым, но не None
        assert isinstance(result, dict)

