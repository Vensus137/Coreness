"""
Tests for BotInfoManager functionality with caching verification
"""
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
class TestBotInfoManagerCache:
    """Tests for caching in BotInfoManager"""
    
    async def test_get_bot_info_uses_cache_on_second_request(self, bot_info_manager, mock_master_repository):
        """Check: on second request data is taken from cache (not from DB)"""
        # Prepare data (format as in DB)
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
        
        # Configure mocks to return data
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # First request - should call get_bot_by_id and get_commands_by_bot
        result1 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that master_repository was called
        mock_master_repository.get_bot_by_id.assert_called_once()
        mock_master_repository.get_commands_by_bot.assert_called_once()
        assert result1['result'] == 'success'
        assert result1['response_data']['bot_id'] == bot_id
        
        # Reset call counters
        mock_master_repository.get_bot_by_id.reset_mock()
        mock_master_repository.get_commands_by_bot.reset_mock()
        
        # Second request - should use cache
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that master_repository was NOT called again
        mock_master_repository.get_bot_by_id.assert_not_called()
        mock_master_repository.get_commands_by_bot.assert_not_called()
        
        # Check that result is same (from cache)
        assert result2['result'] == 'success'
        assert result2['response_data']['bot_id'] == bot_id
    
    async def test_get_bot_info_force_refresh_reloads_from_db(self, bot_info_manager, mock_master_repository):
        """Check: force_refresh=True forcibly updates data from DB"""
        # Prepare data (format as in DB)
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
        
        # Configure mocks for first request
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data_1)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # First request
        result1 = await bot_info_manager.get_bot_info(bot_id)
        assert result1['response_data']['first_name'] == 'Old Name'
        
        # Configure mocks for second request (different data)
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data_2)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Second request with force_refresh=True
        result2 = await bot_info_manager.get_bot_info(bot_id, force_refresh=True)
        
        # Check that master_repository was called again
        assert mock_master_repository.get_bot_by_id.call_count == 1
        
        # Check that data was updated
        assert result2['response_data']['first_name'] == 'New Name'
    
    async def test_get_telegram_bot_info_by_token_uses_cache(self, bot_info_manager, mock_telegram_api):
        """Check: get_telegram_bot_info_by_token uses cache on repeated requests"""
        bot_token = 'test_token_123'
        
        # Configure mock for first request
        mock_telegram_api.get_bot_info = AsyncMock(return_value={
            'result': 'success',
            'response_data': {
                'telegram_bot_id': 123456,
                'username': 'test_bot'
            }
        })
        
        # First request - should call telegram_api
        result1 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Check that telegram_api was called
        mock_telegram_api.get_bot_info.assert_called_once()
        assert result1['result'] == 'success'
        
        # Reset call counter
        mock_telegram_api.get_bot_info.reset_mock()
        
        # Second request - should use cache
        result2 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Check that telegram_api was NOT called again
        mock_telegram_api.get_bot_info.assert_not_called()
        
        # Check that result is same (from cache)
        assert result2['result'] == 'success'
        assert result2['response_data']['telegram_bot_id'] == 123456
    
    async def test_load_all_bots_cache_fills_cache(self, bot_info_manager, mock_master_repository):
        """Check: load_all_bots_cache fills cache on startup"""
        # Prepare data (format as in DB)
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
        
        # Configure mocks
        mock_master_repository.get_all_bots = AsyncMock(return_value=bots_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Load cache
        result = await bot_info_manager.load_all_bots_cache()
        
        # Check that all bots are loaded
        assert len(result) == 2
        
        # Check that cache is filled through cache_manager
        cache_key_1 = bot_info_manager._get_bot_cache_key(1)
        cache_key_2 = bot_info_manager._get_bot_cache_key(2)
        cached_bot1_data = await bot_info_manager.cache_manager.get(cache_key_1)
        cached_bot2_data = await bot_info_manager.cache_manager.get(cache_key_2)
        
        assert cached_bot1_data is not None
        assert cached_bot2_data is not None
        
        # Check data structure in cache (cache stores only data, without wrapper)
        assert cached_bot1_data['bot_id'] == 1
        assert cached_bot1_data['tenant_id'] == 1
        assert cached_bot1_data['bot_token'] == 'token1'
        
        assert cached_bot2_data['bot_id'] == 2
        assert cached_bot2_data['tenant_id'] == 2
        assert cached_bot2_data['bot_token'] == 'token2'
    
    async def test_clear_bot_cache_clears_cache(self, bot_info_manager, mock_master_repository):
        """Check: clear_bot_cache clears cache"""
        # Prepare data (format as in DB)
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
        
        # Configure mocks
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # First request - loads into cache
        result1 = await bot_info_manager.get_bot_info(bot_id)
        assert result1['result'] == 'success'
        
        # Check that cache is filled
        cache_key = bot_info_manager._get_bot_cache_key(bot_id)
        cached_data = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_data is not None
        
        # Clear cache
        await bot_info_manager.clear_bot_cache(bot_id)
        
        # Check that cache is cleared
        cached_data_after = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_data_after is None
        
        # Reset counters
        mock_master_repository.get_bot_by_id.reset_mock()
        mock_master_repository.get_commands_by_bot.reset_mock()
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=bot_data)
        mock_master_repository.get_commands_by_bot = AsyncMock(return_value=[])
        
        # Second request - should load from DB again
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that master_repository was called again
        mock_master_repository.get_bot_by_id.assert_called_once()
        assert result2['result'] == 'success'
    
    async def test_get_bot_info_caches_not_found_error(self, bot_info_manager, mock_master_repository):
        """Check: NOT_FOUND error is cached with short TTL"""
        bot_id = 999
        
        # Configure mock to return None (bot not found)
        mock_master_repository.get_bot_by_id = AsyncMock(return_value=None)
        
        # First request - should return error and cache it
        result1 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that error was returned
        assert result1['result'] == 'error'
        assert result1['error']['code'] == 'NOT_FOUND'
        
        # Check that error is cached
        cache_key = bot_info_manager._get_bot_cache_key(bot_id)
        cached_error = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_error is not None
        assert cached_error.get('_error') is True
        assert cached_error.get('code') == 'NOT_FOUND'
        
        # Reset counter
        mock_master_repository.get_bot_by_id.reset_mock()
        
        # Second request - should return error from cache (not call DB)
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that DB was not called
        mock_master_repository.get_bot_by_id.assert_not_called()
        
        # Check that same error was returned from cache
        assert result2['result'] == 'error'
        assert result2['error']['code'] == 'NOT_FOUND'
    
    async def test_get_telegram_bot_info_by_token_caches_api_error(self, bot_info_manager, mock_telegram_api):
        """Check: API_ERROR error is cached with short TTL"""
        bot_token = 'invalid_token'
        
        # Configure mock to return empty data (API error)
        mock_telegram_api.get_bot_info = AsyncMock(return_value={})
        
        # First request - should return error and cache it
        result1 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Check that error was returned
        assert result1['result'] == 'error'
        assert result1['error']['code'] == 'API_ERROR'
        
        # Check that error is cached
        cache_key = bot_info_manager._get_token_cache_key(bot_token)
        cached_error = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_error is not None
        assert cached_error.get('_error') is True
        assert cached_error.get('code') == 'API_ERROR'
        
        # Reset counter
        mock_telegram_api.get_bot_info.reset_mock()
        
        # Second request - should return error from cache (not call API)
        result2 = await bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        
        # Check that API was not called
        mock_telegram_api.get_bot_info.assert_not_called()
        
        # Check that same error was returned from cache
        assert result2['result'] == 'error'
        assert result2['error']['code'] == 'API_ERROR'
    
    async def test_get_bot_info_caches_internal_error(self, bot_info_manager, mock_master_repository):
        """Check: INTERNAL_ERROR (exception) is cached with short TTL"""
        bot_id = 1
        
        # Configure mock to raise exception
        mock_master_repository.get_bot_by_id = AsyncMock(side_effect=Exception("Database error"))
        
        # First request - should return error and cache it
        result1 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that error was returned
        assert result1['result'] == 'error'
        assert result1['error']['code'] == 'INTERNAL_ERROR'
        
        # Check that error is cached
        cache_key = bot_info_manager._get_bot_cache_key(bot_id)
        cached_error = await bot_info_manager.cache_manager.get(cache_key)
        assert cached_error is not None
        assert cached_error.get('_error') is True
        assert cached_error.get('code') == 'INTERNAL_ERROR'
        
        # Reset counter
        mock_master_repository.get_bot_by_id.reset_mock()
        
        # Second request - should return error from cache (not call DB)
        result2 = await bot_info_manager.get_bot_info(bot_id)
        
        # Check that DB was not called
        mock_master_repository.get_bot_by_id.assert_not_called()
        
        # Check that same error was returned from cache
        assert result2['result'] == 'error'
        assert result2['error']['code'] == 'INTERNAL_ERROR'

