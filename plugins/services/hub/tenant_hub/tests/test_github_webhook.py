"""
Unit tests for GitHub webhook handler (tenant_hub)
"""
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import web

from handlers.github_webhook import GitHubWebhookHandler


@pytest.fixture
def mock_action_hub():
    """Create mock action_hub"""
    action_hub = Mock()
    action_hub.execute_action = AsyncMock(return_value={
        'result': 'success',
        'response_data': {
            'synced_tenants': 1,
            'total_tenants': 1
        }
    })
    return action_hub


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
def handler(mock_action_hub, webhook_secret, mock_logger):
    """Create handler instance"""
    return GitHubWebhookHandler(
        mock_action_hub,
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
async def test_handle_push_event_with_tenant_changes(handler, webhook_secret, mock_action_hub):
    """Test handling push event with tenant changes"""
    payload_data = {
        "commits": [
            {
                "added": ["tenant/tenant_101/tg_bot.yaml"],
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
    # Check that action was called
    mock_action_hub.execute_action.assert_called_once()
    call_args = mock_action_hub.execute_action.call_args
    assert call_args[0][0] == 'sync_tenants_from_files'
    assert 'files' in call_args[0][1]


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

