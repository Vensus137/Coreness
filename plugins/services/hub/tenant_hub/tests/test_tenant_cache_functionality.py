"""
Tests for TenantCache functionality with caching verification
"""
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
class TestTenantCacheFunctionality:
    """Tests for caching in TenantCache"""
    
    async def test_get_bot_by_tenant_id_uses_cache_on_second_request(self, tenant_cache, mock_master_repository):
        """Check: on second request data is taken from cache (not from DB)"""
        # Prepare data
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
        
        # Configure mock to return data
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # First request - should call get_bot_by_tenant_id
        result1 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        
        # Check that master_repository was called
        mock_master_repository.get_bot_by_tenant_id.assert_called_once_with(tenant_id)
        assert result1 is not None
        # Always structured data with 'bot_id'
        assert result1['bot_id'] == bot_id
        assert result1['tenant_id'] == tenant_id
        
        # Check that mapping is saved in cache
        tenant_bot_id_key = tenant_cache._get_tenant_bot_id_key(tenant_id)
        cached_bot_id = await tenant_cache.cache_manager.get(tenant_bot_id_key)
        assert cached_bot_id == bot_id
        
        # Save structured data in cache (as BotInfoManager does)
        # so second request uses them instead of DB access
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
        
        # Reset call counter
        mock_master_repository.get_bot_by_tenant_id.reset_mock()
        
        # Second request - should use cache mapping and structured data
        result2 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        
        # Check that master_repository was NOT called again
        mock_master_repository.get_bot_by_tenant_id.assert_not_called()
        
        # Check that result is same (from cache)
        # Always structured data with 'bot_id'
        assert result2 is not None
        assert result2['bot_id'] == bot_id
        assert result2['tenant_id'] == tenant_id
    
    async def test_get_bot_id_by_tenant_id_uses_cache(self, tenant_cache, mock_master_repository):
        """Check: get_bot_id_by_tenant_id uses cache"""
        # Prepare data
        tenant_id = 1
        bot_id = 123
        bot_data = {
            'id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token'
        }
        
        # Configure mock
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # First request
        result1 = await tenant_cache.get_bot_id_by_tenant_id(tenant_id)
        assert result1 == bot_id
        
        # Save structured data in cache (as BotInfoManager does)
        # so second request uses them instead of DB access
        bot_cache_key = tenant_cache._get_bot_cache_key(bot_id)
        structured_bot_info = {
            'bot_id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token',
            'bot_command': []
        }
        await tenant_cache.cache_manager.set(bot_cache_key, structured_bot_info, ttl=315360000)
        
        # Reset counter
        mock_master_repository.get_bot_by_tenant_id.reset_mock()
        
        # Second request - should use cache
        result2 = await tenant_cache.get_bot_id_by_tenant_id(tenant_id)
        
        # Check that master_repository was NOT called again
        mock_master_repository.get_bot_by_tenant_id.assert_not_called()
        assert result2 == bot_id
    
    async def test_invalidate_bot_cache_clears_cache(self, tenant_cache, mock_master_repository):
        """Check: invalidate_bot_cache clears tenant -> bot_id mapping"""
        # Prepare data
        tenant_id = 1
        bot_id = 1
        bot_data = {
            'id': bot_id,
            'tenant_id': tenant_id,
            'bot_token': 'test_token'
        }
        
        # Configure mock
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # First request - loads mapping into cache
        result1 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        assert result1 is not None
        
        # Check that mapping is saved in cache
        tenant_bot_id_key = tenant_cache._get_tenant_bot_id_key(tenant_id)
        cached_bot_id = await tenant_cache.cache_manager.get(tenant_bot_id_key)
        assert cached_bot_id == bot_id
        
        # Invalidate cache
        await tenant_cache.invalidate_bot_cache(tenant_id)
        
        # Check that mapping is cleared
        cached_bot_id_after = await tenant_cache.cache_manager.get(tenant_bot_id_key)
        assert cached_bot_id_after is None
        
        # Reset counter
        mock_master_repository.get_bot_by_tenant_id.reset_mock()
        mock_master_repository.get_bot_by_tenant_id = AsyncMock(return_value=bot_data)
        
        # Second request - should load from DB again
        result2 = await tenant_cache.get_bot_by_tenant_id(tenant_id)
        
        # Check that master_repository was called again
        mock_master_repository.get_bot_by_tenant_id.assert_called_once()
        assert result2 is not None
    
    async def test_set_last_updated_saves_metadata(self, tenant_cache, mock_datetime_formatter):
        """Check: set_last_updated saves update metadata"""
        tenant_id = 1
        mock_datetime = MagicMock()
        mock_datetime_formatter.now_local_tz = AsyncMock(return_value=mock_datetime)
        mock_datetime_formatter.to_string = AsyncMock(return_value='2024-01-01T12:00:00+00:00')
        
        # Set metadata
        await tenant_cache.set_last_updated(tenant_id)
        
        # Get metadata
        cache_meta = await tenant_cache.get_tenant_cache(tenant_id)
        
        # Check that metadata is saved
        assert 'last_updated_at' in cache_meta
        assert cache_meta['last_updated_at'] == '2024-01-01T12:00:00+00:00'
        assert 'last_error' not in cache_meta
        assert 'last_failed_at' not in cache_meta
    
    async def test_set_last_failed_saves_error_metadata(self, tenant_cache, mock_datetime_formatter):
        """Check: set_last_failed saves error metadata"""
        tenant_id = 1
        error = {
            'code': 'TEST_ERROR',
            'message': 'Test error message',
            'details': ['detail1', 'detail2']
        }
        
        mock_datetime = MagicMock()
        mock_datetime_formatter.now_local_tz = AsyncMock(return_value=mock_datetime)
        mock_datetime_formatter.to_string = AsyncMock(return_value='2024-01-01T12:00:00+00:00')
        
        # Set error metadata
        await tenant_cache.set_last_failed(tenant_id, error)
        
        # Get metadata
        cache_meta = await tenant_cache.get_tenant_cache(tenant_id)
        
        # Check that error metadata is saved
        assert 'last_failed_at' in cache_meta
        assert cache_meta['last_failed_at'] == '2024-01-01T12:00:00+00:00'
        assert 'last_error' in cache_meta
        assert cache_meta['last_error']['code'] == 'TEST_ERROR'
        assert cache_meta['last_error']['message'] == 'Test error message'
        assert cache_meta['last_error']['details'] == ['detail1', 'detail2']
    
    async def test_get_tenant_cache_returns_metadata(self, tenant_cache, mock_datetime_formatter):
        """Check: get_tenant_cache returns tenant metadata"""
        tenant_id = 1
        
        # Set metadata
        mock_datetime = MagicMock()
        mock_datetime_formatter.now_local_tz = AsyncMock(return_value=mock_datetime)
        mock_datetime_formatter.to_string = AsyncMock(return_value='2024-01-01T12:00:00+00:00')
        
        await tenant_cache.set_last_updated(tenant_id)
        
        # Get metadata
        cache_meta = await tenant_cache.get_tenant_cache(tenant_id)
        
        # Check metadata structure
        assert isinstance(cache_meta, dict)
        assert 'last_updated_at' in cache_meta
        
        # Check for non-existent tenant
        empty_meta = await tenant_cache.get_tenant_cache(999)
        assert isinstance(empty_meta, dict)
        assert len(empty_meta) == 0
    
    async def test_get_tenant_config_uses_cache_on_second_request(self, tenant_cache, mock_master_repository):
        """Check: get_tenant_config uses cache on second request"""
        tenant_id = 1
        tenant_data = {
            'id': tenant_id,
            'openrouter_token': 'sk-test-token-123',
            'processed_at': '2024-01-01T00:00:00+00:00'
        }
        
        # Configure mock to return data
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=tenant_data)
        
        # First request - should call get_tenant_by_id
        result1 = await tenant_cache.get_tenant_config(tenant_id)
        
        # Check that master_repository was called
        mock_master_repository.get_tenant_by_id.assert_called_once_with(tenant_id)
        assert result1 is not None
        assert result1.get('openrouter_token') == 'sk-test-token-123'
        # Check that service fields are excluded
        assert 'id' not in result1
        assert 'processed_at' not in result1
        
        # Reset call counter
        mock_master_repository.get_tenant_by_id.reset_mock()
        
        # Second request - should use cache
        result2 = await tenant_cache.get_tenant_config(tenant_id)
        
        # Check that master_repository was NOT called again
        mock_master_repository.get_tenant_by_id.assert_not_called()
        
        # Check that result is same (from cache)
        assert result2 is not None
        assert result2.get('openrouter_token') == 'sk-test-token-123'
    
    async def test_get_tenant_config_returns_none_for_missing_tenant(self, tenant_cache, mock_master_repository):
        """Check: get_tenant_config returns None for non-existent tenant"""
        tenant_id = 999
        
        # Configure mock to return None
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=None)
        
        # Request
        result = await tenant_cache.get_tenant_config(tenant_id)
        
        # Check that None was returned
        assert result is None
    
    async def test_get_tenant_config_excludes_service_fields(self, tenant_cache, mock_master_repository):
        """Check: get_tenant_config excludes service fields (id, processed_at)"""
        tenant_id = 1
        tenant_data = {
            'id': tenant_id,
            'openrouter_token': 'sk-test-token-123',
            'processed_at': '2024-01-01T00:00:00+00:00'
        }
        
        # Configure mock
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=tenant_data)
        
        # Request
        result = await tenant_cache.get_tenant_config(tenant_id)
        
        # Check that service fields are excluded
        assert result is not None
        assert 'id' not in result
        assert 'processed_at' not in result
        # Check that configuration fields are included
        assert 'openrouter_token' in result
        assert result['openrouter_token'] == 'sk-test-token-123'
    
    async def test_get_tenant_config_excludes_none_values(self, tenant_cache, mock_master_repository):
        """Check: get_tenant_config excludes fields with None value"""
        tenant_id = 1
        tenant_data = {
            'id': tenant_id,
            'openrouter_token': None,  # None value
            'processed_at': '2024-01-01T00:00:00+00:00'
        }
        
        # Configure mock
        mock_master_repository.get_tenant_by_id = AsyncMock(return_value=tenant_data)
        
        # Request
        result = await tenant_cache.get_tenant_config(tenant_id)
        
        # Check that None values are excluded
        assert result is not None
        assert 'openrouter_token' not in result
        # Check that dictionary can be empty but not None
        assert isinstance(result, dict)

