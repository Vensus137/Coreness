"""
Тесты функциональности BotInfoManager с проверкой кэширования
"""
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
class TestBotInfoManagerCache:
    """Тесты кэширования в BotInfoManager"""
    
    async def test_get_bot_info_uses_cache_on_second_request(self, bot_info_manager, mock_master_repository):
        """Проверка: при повторном запросе данные берутся из кэша (не из БД)"""
        # Подготавливаем данные (формат как в БД)
        bot_id = 1
        bot_data = {
            'id': bot_id,
            'tenant_id': 1,
            'bot_token': 'test_token',
            'telegram_bot_id': 123456,
            'username': 'test_bot',
            'first_name': 'Test Bot',
            'is_active': True
        }
        
        # Настраиваем моки для возврата данных
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Первый запрос - должен вызвать get_bot_by_id и get_commands_by_bot
        result1 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что master_repository был вызван
        mock_master_repository.get_bot_by_id.assert_called_once()
        mock_master_repository.get_commands_by_bot.assert_called_once()
        assert result1['result'] == 'success'
        assert result1['response_data']['bot_id'] == bot_id
        
        # Сбрасываем счетчики вызовов
        mock_master_repository.get_bot_by_id.reset_mock()
        mock_master_repository.get_commands_by_bot.reset_mock()
        
        # Второй запрос - должен использовать кэш
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что master_repository НЕ был вызван повторно
        mock_master_repository.get_bot_by_id.assert_not_called()
        mock_master_repository.get_commands_by_bot.assert_not_called()
        
        # Проверяем, что результат тот же (из кэша)
        assert result2['result'] == 'success'
        assert result2['response_data']['bot_id'] == bot_id
    
    async def test_get_bot_info_force_refresh_reloads_from_db(self, bot_info_manager, mock_master_repository):
        """Проверка: force_refresh=True принудительно обновляет данные из БД"""
        # Подготавливаем данные (формат как в БД)
        bot_id = 1
        bot_data_1 = {
            'id': bot_id,
            'tenant_id': 1,
            'bot_token': 'token1',
            'first_name': 'Old Name',
            'is_active': True
        }
        bot_data_2 = {
            'id': bot_id,
            'tenant_id': 1,
            'bot_token': 'token2',
            'first_name': 'New Name',
            'is_active': False
        }
        
        # Настраиваем моки для первого запроса
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data_1)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Первый запрос
        result1 = await bot_info_manager.get_bot_info(bot_id)
        assert result1['response_data']['first_name'] == 'Old Name'
        
        # Настраиваем моки для второго запроса (другие данные)
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data_2)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Второй запрос с force_refresh=True
        result2 = await bot_info_manager.get_bot_info(bot_id, force_refresh=True)
        
        # Проверяем, что master_repository был вызван снова
        assert mock_master_repository.get_bot_by_id.call_count == 1
        
        # Проверяем, что данные обновились
        assert result2['response_data']['first_name'] == 'New Name'
    
    async def test_get_telegram_bot_info_by_token_uses_cache(self, bot_info_manager, mock_telegram_api):
        """Проверка: get_telegram_bot_info_by_token использует кэш при повторных запросах"""
        bot_token = 'test_token_123'
        
        # Настраиваем мок для первого запроса
        mock_telegram_api.get_bot_info = AsyncMock(return_value={
            'result': 'success',
            'response_data': {
                'telegram_bot_id': 123456,
                'username': 'test_bot'
            }
        })
        
        # Первый запрос - должен вызвать telegram_api
        result1 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Проверяем, что telegram_api был вызван
        mock_telegram_api.get_bot_info.assert_called_once()
        assert result1['result'] == 'success'
        
        # Сбрасываем счетчик вызовов
        mock_telegram_api.get_bot_info.reset_mock()
        
        # Второй запрос - должен использовать кэш
        result2 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Проверяем, что telegram_api НЕ был вызван повторно
        mock_telegram_api.get_bot_info.assert_not_called()
        
        # Проверяем, что результат тот же (из кэша)
        assert result2['result'] == 'success'
        assert result2['response_data']['telegram_bot_id'] == 123456
    
    async def test_load_all_bots_cache_fills_cache(self, bot_info_manager, mock_master_repository):
        """Проверка: load_all_bots_cache заполняет кэш при запуске"""
        # Подготавливаем данные (формат как в БД)
        bots_data = [
            {
                'id': 1,
                'tenant_id': 1,
                'bot_token': 'token1',
                'telegram_bot_id': 111,
                'username': 'bot1',
                'first_name': 'Bot 1',
                'is_active': True
            },
            {
                'id': 2,
                'tenant_id': 2,
                'bot_token': 'token2',
                'telegram_bot_id': 222,
                'username': 'bot2',
                'first_name': 'Bot 2',
                'is_active': True
            }
        ]
        
        # Настраиваем моки
        mock_master_repository.get_all_bots = AsyncMock(return_value=bots_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Загружаем кэш
        result = await bot_info_manager.load_all_bots_cache()
        
        # Проверяем, что все боты загружены
        assert len(result) == 2
        
        # Проверяем, что кэш заполнен через cache_manager
        cache_key_1 = bot_info_manager._get_bot_cache_key(1)
        cache_key_2 = bot_info_manager._get_bot_cache_key(2)
        cached_bot1_data = await bot_info_manager.cache_manager.get(cache_key_1)
        cached_bot2_data = await bot_info_manager.cache_manager.get(cache_key_2)
        
        assert cached_bot1_data is not None
        assert cached_bot2_data is not None
        
        # Проверяем структуру данных в кэше (в кэше хранятся только данные, без обертки)
        assert cached_bot1_data['bot_id'] == 1
        assert cached_bot1_data['tenant_id'] == 1
        assert cached_bot1_data['bot_token'] == 'token1'
        
        assert cached_bot2_data['bot_id'] == 2
        assert cached_bot2_data['tenant_id'] == 2
        assert cached_bot2_data['bot_token'] == 'token2'
    
    async def test_clear_bot_cache_clears_cache(self, bot_info_manager, mock_master_repository):
        """Проверка: clear_bot_cache очищает кэш"""
        # Подготавливаем данные (формат как в БД)
        bot_id = 1
        bot_data = {
            'id': bot_id,
            'tenant_id': 1,
            'bot_token': 'test_token',
            'telegram_bot_id': 123456,
            'username': 'test_bot',
            'first_name': 'Test Bot',
            'is_active': True
        }
        
        # Настраиваем моки
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Первый запрос - загружает в кэш
        result1 = await bot_info_manager.get_bot_info(bot_id)
        assert result1['result'] == 'success'
        
        # Проверяем, что кэш заполнен
        cache_key = bot_info_manager._get_bot_cache_key(bot_id)
        cached_data = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_data is not None
        
        # Очищаем кэш
        await bot_info_manager.clear_bot_cache(bot_id)
        
        # Проверяем, что кэш очищен
        cached_data_after = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_data_after is None
        
        # Сбрасываем счетчики
        mock_master_repository.get_bot_by_id.reset_mock()
        mock_master_repository.get_commands_by_bot.reset_mock()
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Второй запрос - должен загрузить из БД снова
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что master_repository был вызван снова
        mock_master_repository.get_bot_by_id.assert_called_once()
        assert result2['result'] == 'success'
    
    async def test_get_bot_info_caches_not_found_error(self, bot_info_manager, mock_master_repository):
        """Проверка: ошибка NOT_FOUND кэшируется с коротким TTL"""
        bot_id = 999
        
        # Настраиваем мок для возврата None (бот не найден)
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=None)
        
        # Первый запрос - должен вернуть ошибку и закэшировать её
        result1 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что вернулась ошибка
        assert result1['result'] == 'error'
        assert result1['error']['code'] == 'NOT_FOUND'
        
        # Проверяем, что ошибка закэширована
        cache_key = bot_info_manager._get_bot_cache_key(bot_id)
        cached_error = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_error is not None
        assert cached_error.get('_error') is True
        assert cached_error.get('code') == 'NOT_FOUND'
        
        # Сбрасываем счетчик
        mock_master_repository.get_bot_by_id.reset_mock()
        
        # Второй запрос - должен вернуть ошибку из кэша (не вызывать БД)
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что БД не вызывалась
        mock_master_repository.get_bot_by_id.assert_not_called()
        
        # Проверяем, что вернулась та же ошибка из кэша
        assert result2['result'] == 'error'
        assert result2['error']['code'] == 'NOT_FOUND'
    
    async def test_get_telegram_bot_info_by_token_caches_api_error(self, bot_info_manager, mock_telegram_api):
        """Проверка: ошибка API_ERROR кэшируется с коротким TTL"""
        bot_token = 'invalid_token'
        
        # Настраиваем мок для возврата пустых данных (ошибка API)
        mock_telegram_api.get_bot_info = AsyncMock(return_value={})
        
        # Первый запрос - должен вернуть ошибку и закэшировать её
        result1 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Проверяем, что вернулась ошибка
        assert result1['result'] == 'error'
        assert result1['error']['code'] == 'API_ERROR'
        
        # Проверяем, что ошибка закэширована
        cache_key = bot_info_manager._get_token_cache_key(bot_token)
        cached_error = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_error is not None
        assert cached_error.get('_error') is True
        assert cached_error.get('code') == 'API_ERROR'
        
        # Сбрасываем счетчик
        mock_telegram_api.get_bot_info.reset_mock()
        
        # Второй запрос - должен вернуть ошибку из кэша (не вызывать API)
        result2 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Проверяем, что API не вызывался
        mock_telegram_api.get_bot_info.assert_not_called()
        
        # Проверяем, что вернулась та же ошибка из кэша
        assert result2['result'] == 'error'
        assert result2['error']['code'] == 'API_ERROR'
    
    async def test_get_bot_info_caches_internal_error(self, bot_info_manager, mock_master_repository):
        """Проверка: ошибка INTERNAL_ERROR (исключение) кэшируется с коротким TTL"""
        bot_id = 1
        
        # Настраиваем мок для выброса исключения
        mock_master_repository.get_bot_by_id = AsyncMock(side_effect=Exception("Database error"))
        
        # Первый запрос - должен вернуть ошибку и закэшировать её
        result1 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что вернулась ошибка
        assert result1['result'] == 'error'
        assert result1['error']['code'] == 'INTERNAL_ERROR'
        
        # Проверяем, что ошибка закэширована
        cache_key = bot_info_manager._get_bot_cache_key(bot_id)
        cached_error = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_error is not None
        assert cached_error.get('_error') is True
        assert cached_error.get('code') == 'INTERNAL_ERROR'
        
        # Сбрасываем счетчик
        mock_master_repository.get_bot_by_id.reset_mock()
        
        # Второй запрос - должен вернуть ошибку из кэша (не вызывать БД)
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Проверяем, что БД не вызывалась
        mock_master_repository.get_bot_by_id.assert_not_called()
        
        # Проверяем, что вернулась та же ошибка из кэша
        assert result2['result'] == 'error'
        assert result2['error']['code'] == 'INTERNAL_ERROR'

