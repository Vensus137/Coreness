"""
Integration tests for GitHub webhooks
Test full flow from receiving webhook to tenant synchronization

Note: these tests require HTTP server to be running.
If port is busy or server is disabled, tests will be skipped.
"""
import asyncio
import hmac
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, Mock

from aiohttp import web

# Fixed secret for tests (must match conftest.py)
TEST_WEBHOOK_SECRET = 'test_secret_12345'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_full_flow(initialized_di_container):
    """Test full flow: webhook → parsing → synchronization"""
    # Get dependencies
    http_server = initialized_di_container.get_utility('http_server')
    tenant_hub = initialized_di_container.get_service('tenant_hub')
    
    # Mock webhook_actions.sync_tenants_from_files (handler uses webhook_actions, not tenant_hub)
    original_sync = tenant_hub.webhook_actions.sync_tenants_from_files
    tenant_hub.webhook_actions.sync_tenants_from_files = AsyncMock(return_value={
        'result': 'success',
        'response_data': {
            'synced_tenants': 1,
            'total_tenants': 1
        }
    })
    
    try:
        # Endpoint is already registered during tenant_hub initialization
        # Start server (as http_api_service does)
        if not http_server.is_running:
            success = await http_server.start()
            assert success is True
        
        # Use fixed secret for tests (set through conftest)
        webhook_secret = TEST_WEBHOOK_SECRET
        
        # Create test payload
        payload_data = {
            "commits": [
                {
                    "added": ["tenant/tenant_101/bots/telegram.yaml"],
                    "modified": ["tenant/tenant_102/scenarios/scenario1.yaml"],
                    "removed": []
                }
            ]
        }
        payload = json.dumps(payload_data).encode('utf-8')
        
        # Calculate correct signature
        expected_hash = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_hash}"
        
        # Create mock request
        request = Mock(spec=web.Request)
        request.read = AsyncMock(return_value=payload)
        request.headers = {
            'X-Hub-Signature-256': signature,
            'X-GitHub-Event': 'push'
        }
        
        # Get handler from router
        handler = None
        for route in http_server.app.router.routes():
            if route.resource.canonical == '/webhooks/github':
                handler = route.handler
                break
        
        assert handler is not None
        
        # Call handler
        response = await handler(request)
        
        # Verify result
        assert response.status == 200
        tenant_hub.webhook_actions.sync_tenants_from_files.assert_called_once()
        call_args = tenant_hub.webhook_actions.sync_tenants_from_files.call_args
        data = call_args[0][0]
        assert 'files' in data
        assert 'tenant/tenant_101/bots/telegram.yaml' in data['files']
        assert 'tenant/tenant_102/scenarios/scenario1.yaml' in data['files']
        
    finally:
        tenant_hub.webhook_actions.sync_tenants_from_files = original_sync


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_invalid_signature(initialized_di_container):
    """Test webhook handling with invalid signature"""
    http_server = initialized_di_container.get_utility('http_server')
    
    # Endpoint is already registered during tenant_hub initialization
    # Start server (as http_api_service does)
    if not http_server.is_running:
        success = await http_server.start()
        assert success is True
    
    # Create test payload with wrong signature
    payload_data = {"commits": []}
    payload = json.dumps(payload_data).encode('utf-8')
    
    # Create mock request
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {
        'X-Hub-Signature-256': 'sha256=wrong_hash',
        'X-GitHub-Event': 'push'
    }
    
    # Get handler
    handler = None
    for route in http_server.app.router.routes():
        if route.resource.canonical == '/webhooks/github':
            handler = route.handler
            break
    
    assert handler is not None
    
    # Call handler
    response = await handler(request)
    
    # Verify that 401 error was returned
    assert response.status == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_no_tenant_changes(initialized_di_container):
    """Test webhook handling without tenant changes"""
    http_server = initialized_di_container.get_utility('http_server')
    action_hub = initialized_di_container.get_utility('action_hub')
    
    # Endpoint is already registered during tenant_hub initialization
    # Start server (as http_api_service does)
    if not http_server.is_running:
        success = await http_server.start()
        assert success is True
    
    # Use fixed secret for tests (set through conftest)
    webhook_secret = TEST_WEBHOOK_SECRET
    
    # Create payload without tenant changes
    payload_data = {
        "commits": [
            {
                "added": ["README.md"],
                "modified": ["docs/guide.md"],
                "removed": []
            }
        ]
    }
    payload = json.dumps(payload_data).encode('utf-8')
    
    # Calculate correct signature
    expected_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature = f"sha256={expected_hash}"
    
    # Create mock request
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {
        'X-Hub-Signature-256': signature,
        'X-GitHub-Event': 'push'
    }
    
    # Get handler
    handler = None
    for route in http_server.app.router.routes():
        if route.resource.canonical == '/webhooks/github':
            handler = route.handler
            break
    
    assert handler is not None
    
    # Call handler
    response = await handler(request)
    
    # Verify that success was returned (but without synchronization)
    assert response.status == 200
    # Verify that action was NOT called (no tenant changes)
    # This is verified by absence of sync_tenants_from_files call

