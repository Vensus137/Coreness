"""
Integration tests for Telegram webhooks.
Test full flow from webhook setup to receiving and processing updates.

Requires: use_webhooks=True for telegram_bot_manager and http_server loaded
(integration conftest enables webhooks for telegram_bot_manager).
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import web


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_endpoint_registered(initialized_di_container):
    """Test that Telegram webhook endpoint is registered (when use_webhooks is enabled)"""
    http_server = initialized_di_container.get_utility('http_server')

    endpoint_found = False
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                endpoint_found = True
                break

    assert endpoint_found, (
        "Endpoint /webhooks/telegram is not registered. "
        "Enable use_webhooks in telegram_bot_manager settings and ensure http_server is loaded."
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_handler_missing_secret_token(initialized_di_container):
    """Test webhook handling without secret_token"""
    http_server = initialized_di_container.get_utility('http_server')

    if not http_server.is_running:
        success = await http_server.start()
        assert success is True

    handler = None
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                handler = route.handler
                break

    assert handler is not None, (
        "Handler for /webhooks/telegram not found. "
        "Enable use_webhooks in telegram_bot_manager settings."
    )

    # Create request without secret_token
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=b'{}')
    request.headers = {}
    
    response = await handler(request)
    
    assert response.status == 401
    assert "Missing secret token" in response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_handler_invalid_secret_token(initialized_di_container):
    """Test webhook handling with invalid secret_token"""
    http_server = initialized_di_container.get_utility('http_server')

    if not http_server.is_running:
        success = await http_server.start()
        assert success is True

    handler = None
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                handler = route.handler
                break

    assert handler is not None, (
        "Handler for /webhooks/telegram not found. "
        "Enable use_webhooks in telegram_bot_manager settings."
    )

    # Create request with invalid secret_token
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=b'{}')
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'invalid_token_12345'}
    
    response = await handler(request)
    
    assert response.status == 401
    assert "Invalid secret token" in response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_full_flow(initialized_di_container):
    """Test full flow: webhook setup → receiving update → processing"""
    bot_manager = initialized_di_container.get_service('telegram_bot_manager')
    http_server = initialized_di_container.get_utility('http_server')
    action_hub = initialized_di_container.get_utility('action_hub')
    cache_manager = initialized_di_container.get_utility('cache_manager')

    assert bot_manager is not None, "telegram_bot_manager service must be loaded"
    assert bot_manager.webhook_manager is not None, (
        "webhook_manager not available (enable use_webhooks and ensure http_server is loaded)"
    )

    handler = None
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                handler = route.handler
                break
    assert handler is not None, (
        "Endpoint /webhooks/telegram not registered. "
        "Enable use_webhooks in telegram_bot_manager settings."
    )

    webhook_manager = bot_manager.webhook_manager

    # Mock execute_action to avoid real processing
    original_execute_action = action_hub.execute_action
    action_called = []

    async def mock_execute_action(action_name, data, **kwargs):
        action_called.append({
            'action': action_name,
            'data': data,
            'kwargs': kwargs
        })
        return {'result': 'success'}

    action_hub.execute_action = AsyncMock(side_effect=mock_execute_action)

    try:
        # Start server if not running
        if not http_server.is_running:
            success = await http_server.start()
            assert success is True

        # Test data
        test_bot_id = 999999
        test_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        
        # Mock successful response from Telegram API
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={'ok': True})
        mock_response.status = 200
        
        # Correct mock for aiohttp.ClientSession
        mock_post_response = AsyncMock()
        mock_post_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_response.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance = AsyncMock()
        mock_session_instance.post = Mock(return_value=mock_post_response)
        
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await webhook_manager.set_webhook(test_bot_id, test_bot_token)
            
            assert result['result'] == 'success'
            secret_token = result['response_data']['secret_token']
        
        # 2. Verify that secret_token is saved in cache
        bot_id_from_cache = await webhook_manager.get_bot_id_by_secret_token(secret_token)
        assert bot_id_from_cache == test_bot_id
        
        # 3. Get handler (already found at start of test)
        handler = None
        for route in http_server.app.router.routes():
            if hasattr(route, 'resource') and route.resource:
                canonical = getattr(route.resource, 'canonical', None)
                if canonical == '/webhooks/telegram':
                    handler = route.handler
                    break
        assert handler is not None
        
        # 4. Create test payload from Telegram
        payload_data = {
            'update_id': 123456,
            'message': {
                'message_id': 1,
                'from': {'id': 789, 'first_name': 'Test User'},
                'chat': {'id': 789, 'type': 'private'},
                'text': 'Hello, bot!'
            }
        }
        payload = json.dumps(payload_data).encode('utf-8')
        
        # 5. Create request with valid secret_token
        request = Mock(spec=web.Request)
        request.read = AsyncMock(return_value=payload)
        request.headers = {'X-Telegram-Bot-Api-Secret-Token': secret_token}
        
        # 6. Call handler
        response = await handler(request)
        
        # 7. Verify result
        assert response.status == 200
        assert response.text == "OK"
        
        # 8. Verify that event was sent to event_processor
        assert len(action_called) == 1
        assert action_called[0]['action'] == 'process_event'
        assert action_called[0]['data']['system']['bot_id'] == test_bot_id
        assert action_called[0]['data']['system']['source'] == 'webhook'
        assert action_called[0]['kwargs']['fire_and_forget'] is True
        
        # 9. Delete webhook
        mock_response_delete = Mock()
        mock_response_delete.json = AsyncMock(return_value={'ok': True})
        
        # Correct mock for aiohttp.ClientSession
        mock_post_response_delete = AsyncMock()
        mock_post_response_delete.__aenter__ = AsyncMock(return_value=mock_response_delete)
        mock_post_response_delete.__aexit__ = AsyncMock(return_value=None)
        
        mock_session_instance_delete = AsyncMock()
        mock_session_instance_delete.post = Mock(return_value=mock_post_response_delete)
        
        mock_session_delete = AsyncMock()
        mock_session_delete.__aenter__ = AsyncMock(return_value=mock_session_instance_delete)
        mock_session_delete.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session_delete):
            delete_result = await webhook_manager.delete_webhook(test_bot_token, test_bot_id)
            assert delete_result['result'] == 'success'
        
    finally:
        # Restore original method
        action_hub.execute_action = original_execute_action


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_ssl_certificate_generation(initialized_di_container):
    """Test automatic SSL certificate generation"""
    http_server = initialized_di_container.get_utility('http_server')
    settings_manager = initialized_di_container.get_utility('settings_manager')
    
    # Set external_url for certificate generation
    settings = settings_manager.get_plugin_settings('http_server')
    if settings.get('external_url'):
        # Verify that certificate was generated
        assert http_server.ssl_context is not None
        assert http_server._certificate_pem is not None
        assert http_server._private_key_pem is not None
        
        # Verify that certificate can be retrieved
        cert_result = http_server.get_certificate()
        assert cert_result is not None
        cert_pem, key_pem = cert_result
        assert isinstance(cert_pem, bytes)
        assert isinstance(key_pem, bytes)
        assert b'BEGIN CERTIFICATE' in cert_pem
        assert b'BEGIN PRIVATE KEY' in key_pem

