"""
Unit tests for GitHub webhook handler (tenant_hub)
"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web

from plugins.services.hub.tenant_hub.handlers.github_webhook import GitHubWebhookHandler


@pytest.fixture
def mock_webhook_actions():
    """Create mock webhook_actions (sync logic, no tenant_hub reference)"""
    actions = Mock()
    actions.sync_tenants_from_files = AsyncMock(return_value={
        'result': 'success',
        'response_data': {
            'synced_tenants': 1,
            'total_tenants': 1
        }
    })
    return actions


@pytest.fixture
def mock_logger():
    """Create mock logger"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def webhook_secret():
    """Secret for tests"""
    return "test_secret_12345"


@pytest.fixture
def handler(mock_webhook_actions, webhook_secret, mock_logger):
    """Create handler instance"""
    return GitHubWebhookHandler(
        mock_webhook_actions,
        webhook_secret,
        mock_logger
    )


def test_verify_signature_valid(handler, webhook_secret):
    """Test validation of correct signature"""
    payload = b'{"test": "data"}'
    
    # Calculate correct signature
    expected_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature = f"sha256={expected_hash}"
    
    result = handler._verify_signature(payload, signature)
    
    assert result is True


def test_verify_signature_invalid(handler, webhook_secret):
    """Test validation of incorrect signature"""
    payload = b'{"test": "data"}'
    signature = "sha256=wrong_hash"
    
    result = handler._verify_signature(payload, signature)
    
    assert result is False


def test_verify_signature_no_secret(handler):
    """Test validation when secret is not set"""
    handler.webhook_secret = ""
    payload = b'{"test": "data"}'
    signature = "sha256=some_hash"
    
    result = handler._verify_signature(payload, signature)
    
    assert result is False


def test_verify_signature_wrong_format(handler):
    """Test validation of signature in wrong format"""
    payload = b'{"test": "data"}'
    signature = "wrong_format_hash"
    
    result = handler._verify_signature(payload, signature)
    
    assert result is False


@pytest.mark.asyncio
async def test_handle_invalid_signature(handler):
    """Test handling request with invalid signature"""
    payload = b'{"test": "data"}'
    
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {'X-Hub-Signature-256': 'sha256=wrong_hash', 'X-GitHub-Event': 'push'}
    
    response = await handler.handle(request)
    
    assert response.status == 401
    handler.logger.warning.assert_called()


@pytest.mark.asyncio
async def test_handle_invalid_json(handler, webhook_secret):
    """Test handling request with invalid JSON"""
    payload = b'invalid json'
    
    # Calculate correct signature
    expected_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature = f"sha256={expected_hash}"
    
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {'X-Hub-Signature-256': signature, 'X-GitHub-Event': 'push'}
    
    response = await handler.handle(request)
    
    assert response.status == 400
    handler.logger.error.assert_called()


@pytest.mark.asyncio
async def test_handle_wrong_event_type(handler, webhook_secret):
    """Test handling request with unsupported event type"""
    payload = json.dumps({"test": "data"}).encode('utf-8')
    
    # Calculate correct signature
    expected_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature = f"sha256={expected_hash}"
    
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {'X-Hub-Signature-256': signature, 'X-GitHub-Event': 'pull_request'}
    
    response = await handler.handle(request)
    
    assert response.status == 200
    handler.logger.info.assert_called()


@pytest.mark.asyncio
async def test_handle_push_event_with_tenant_changes(handler, webhook_secret, mock_webhook_actions):
    """Test handling push event with tenant changes"""
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
    
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {'X-Hub-Signature-256': signature, 'X-GitHub-Event': 'push'}
    
    response = await handler.handle(request)
    
    assert response.status == 200
    mock_webhook_actions.sync_tenants_from_files.assert_called_once()
    call_args = mock_webhook_actions.sync_tenants_from_files.call_args
    data = call_args[0][0]
    assert 'files' in data
    assert 'tenant/tenant_101/bots/telegram.yaml' in data['files']
    assert 'tenant/tenant_102/scenarios/scenario1.yaml' in data['files']


@pytest.mark.asyncio
async def test_handle_push_event_no_tenant_changes(handler, webhook_secret):
    """Test handling push event without tenant changes"""
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
    
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {'X-Hub-Signature-256': signature, 'X-GitHub-Event': 'push'}
    
    response = await handler.handle(request)
    
    assert response.status == 200
    handler.logger.info.assert_called()

