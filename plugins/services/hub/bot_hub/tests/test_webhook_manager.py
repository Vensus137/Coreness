"""
Unit tests for WebhookManager
"""
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from modules.webhook_manager import WebhookManager


@pytest.fixture
def mock_cache_manager():
    """Create mock CacheManager"""
    mock = MagicMock()
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_logger():
    """Create mock logger"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def mock_settings_manager():
    """Create mock SettingsManager"""
    mock = MagicMock()
    mock.get_plugin_settings = Mock(return_value={
        'cache_ttl': 315360000,
        'allowed_updates': ['message', 'callback_query', 'pre_checkout_query']
    })
    return mock


@pytest.fixture
def mock_http_server():
    """Create mock HTTPServer"""
    mock = MagicMock()
    mock.get_webhook_url = Mock(return_value='https://123.45.67.89:8443/webhooks/telegram')
    mock.get_certificate = Mock(return_value=(b'cert_pem', b'key_pem'))
    return mock


@pytest.fixture
def webhook_manager(mock_cache_manager, mock_logger, mock_settings_manager, mock_http_server):
    """Create WebhookManager instance"""
    return WebhookManager(
        mock_cache_manager,
        mock_logger,
        mock_settings_manager,
        mock_http_server
    )


def test_generate_secret_token(webhook_manager):
    """Test secret_token generation"""
    bot_id = 123
    secret_token = webhook_manager._generate_secret_token(bot_id)
    
    # Check that token is MD5 hash
    assert len(secret_token) == 32  # MD5 hex = 32 characters
    assert secret_token.isalnum() or all(c in '0123456789abcdef' for c in secret_token)
    
    # Check that for same bot_id and startup_timestamp token is same
    token2 = webhook_manager._generate_secret_token(bot_id)
    assert secret_token == token2
    
    # Check that for different bot_id tokens are different
    token3 = webhook_manager._generate_secret_token(456)
    assert secret_token != token3


@pytest.mark.asyncio
async def test_save_secret_token(webhook_manager, mock_cache_manager):
    """Test saving secret_token to cache"""
    secret_token = "test_secret_token"
    bot_id = 123
    
    await webhook_manager._save_secret_token(secret_token, bot_id)
    
    # Check that set was called with correct parameters
    mock_cache_manager.set.assert_called_once()
    call_args = mock_cache_manager.set.call_args[0]
    assert 'webhook_secret:test_secret_token' in call_args[0]
    assert call_args[1] == bot_id


@pytest.mark.asyncio
async def test_get_bot_id_by_secret_token_found(webhook_manager, mock_cache_manager):
    """Test getting bot_id by secret_token (found)"""
    secret_token = "test_secret_token"
    bot_id = 123
    mock_cache_manager.get = AsyncMock(return_value=bot_id)
    
    result = await webhook_manager.get_bot_id_by_secret_token(secret_token)
    
    assert result == bot_id
    mock_cache_manager.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_bot_id_by_secret_token_not_found(webhook_manager, mock_cache_manager):
    """Test getting bot_id by secret_token (not found)"""
    secret_token = "test_secret_token"
    mock_cache_manager.get = AsyncMock(return_value=None)
    
    result = await webhook_manager.get_bot_id_by_secret_token(secret_token)
    
    assert result is None
    mock_cache_manager.get.assert_called_once()


@pytest.mark.asyncio
async def test_set_webhook_success(webhook_manager, mock_http_server, mock_cache_manager):
    """Test successful webhook setup"""
    bot_id = 123
    bot_token = "123456:ABC-DEF"
    
    # Mock successful response from Telegram API
    mock_response = Mock()
    mock_response.json = AsyncMock(return_value={'ok': True})
    mock_response.status = 200
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    
    # Mock post method that returns context manager
    mock_post = Mock(return_value=mock_response)
    
    # Mock session
    mock_session = Mock()
    mock_session.post = mock_post
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    
    with patch('modules.webhook_manager.aiohttp.ClientSession', return_value=mock_session):
        result = await webhook_manager.set_webhook(bot_id, bot_token)
        
        assert result['result'] == 'success'
        assert 'webhook_url' in result['response_data']
        assert 'secret_token' in result['response_data']
        
        # Check that secret_token was saved to cache
        mock_cache_manager.set.assert_called_once()


@pytest.mark.asyncio
async def test_set_webhook_no_http_server(mock_cache_manager, mock_logger, mock_settings_manager):
    """Test webhook setup without http_server (http_server is now required, but for test create with None)"""
    from modules.webhook_manager import WebhookManager
    # Create WebhookManager with None for test (in real code this should not happen)
    webhook_manager = WebhookManager(mock_cache_manager, mock_logger, mock_settings_manager, None)
    bot_id = 123
    bot_token = "123456:ABC-DEF"
    
    result = await webhook_manager.set_webhook(bot_id, bot_token)
    
    assert result['result'] == 'error'
    assert result['error']['code'] == 'CONFIG_ERROR'


@pytest.mark.asyncio
async def test_set_webhook_no_external_url(webhook_manager, mock_http_server):
    """Test webhook setup without external_url"""
    mock_http_server.get_webhook_url = Mock(return_value=None)
    bot_id = 123
    bot_token = "123456:ABC-DEF"
    
    result = await webhook_manager.set_webhook(bot_id, bot_token)
    
    assert result['result'] == 'error'
    assert result['error']['code'] == 'CONFIG_ERROR'


@pytest.mark.asyncio
async def test_set_webhook_telegram_api_error(webhook_manager, mock_http_server, mock_cache_manager):
    """Test webhook setup with Telegram API error"""
    bot_id = 123
    bot_token = "123456:ABC-DEF"
    
    # Mock error from Telegram API
    mock_response = Mock()
    mock_response.json = AsyncMock(return_value={
        'ok': False,
        'error_code': 400,
        'description': 'Bad Request'
    })
    mock_response.status = 400
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    
    mock_post = Mock(return_value=mock_response)
    mock_session = Mock()
    mock_session.post = mock_post
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    
    with patch('modules.webhook_manager.aiohttp.ClientSession', return_value=mock_session):
        result = await webhook_manager.set_webhook(bot_id, bot_token)
        
        assert result['result'] == 'error'
        assert result['error']['code'] == 'API_ERROR'
        assert 'Bad Request' in result['error']['message']


@pytest.mark.asyncio
async def test_set_webhook_conflict_409(webhook_manager, mock_http_server, mock_cache_manager):
    """Test webhook setup with conflict (409)"""
    bot_id = 123
    bot_token = "123456:ABC-DEF"
    
    # First response - conflict 409
    mock_response_409 = Mock()
    mock_response_409.json = AsyncMock(return_value={
        'ok': False,
        'error_code': 409,
        'description': 'Conflict'
    })
    mock_response_409.__aenter__ = AsyncMock(return_value=mock_response_409)
    mock_response_409.__aexit__ = AsyncMock(return_value=False)
    
    # Second response after deletion - success
    mock_response_success = Mock()
    mock_response_success.json = AsyncMock(return_value={'ok': True})
    mock_response_success.__aenter__ = AsyncMock(return_value=mock_response_success)
    mock_response_success.__aexit__ = AsyncMock(return_value=False)
    
    # Mock delete_webhook
    mock_response_delete = Mock()
    mock_response_delete.json = AsyncMock(return_value={'ok': True})
    mock_response_delete.__aenter__ = AsyncMock(return_value=mock_response_delete)
    mock_response_delete.__aexit__ = AsyncMock(return_value=False)
    
    mock_post = Mock(side_effect=[mock_response_409, mock_response_delete, mock_response_success])
    mock_session = Mock()
    mock_session.post = mock_post
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    
    with patch('modules.webhook_manager.aiohttp.ClientSession', return_value=mock_session):
        result = await webhook_manager.set_webhook(bot_id, bot_token)
        
        # Should be success after conflict handling
        assert result['result'] == 'success'


@pytest.mark.asyncio
async def test_delete_webhook_success(webhook_manager):
    """Test successful webhook deletion"""
    bot_token = "123456:ABC-DEF"
    bot_id = 123
    
    # Mock successful response from Telegram API
    mock_response = Mock()
    mock_response.json = AsyncMock(return_value={'ok': True})
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    
    mock_post = Mock(return_value=mock_response)
    mock_session = Mock()
    mock_session.post = mock_post
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    
    with patch('modules.webhook_manager.aiohttp.ClientSession', return_value=mock_session):
        result = await webhook_manager.delete_webhook(bot_token, bot_id)
        
        assert result['result'] == 'success'


@pytest.mark.asyncio
async def test_delete_webhook_already_deleted(webhook_manager):
    """Test deleting webhook that is already deleted"""
    bot_token = "123456:ABC-DEF"
    bot_id = 123
    
    # Mock response that webhook is already deleted
    mock_response = Mock()
    mock_response.json = AsyncMock(return_value={
        'ok': False,
        'description': 'Webhook is already deleted'
    })
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    
    mock_post = Mock(return_value=mock_response)
    mock_session = Mock()
    mock_session.post = mock_post
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    
    with patch('modules.webhook_manager.aiohttp.ClientSession', return_value=mock_session):
        result = await webhook_manager.delete_webhook(bot_token, bot_id)
        
        # Should return success even if already deleted
        assert result['result'] == 'success'

