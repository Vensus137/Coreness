"""
Unit-тесты для TelegramWebhookHandler
"""
import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from aiohttp import web

from handlers.telegram_webhook import TelegramWebhookHandler


@pytest.fixture
def mock_webhook_manager():
    """Создает мок WebhookManager"""
    mock = MagicMock()
    mock.get_bot_id_by_secret_token = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_action_hub():
    """Создает мок ActionHub"""
    mock = MagicMock()
    mock.execute_action = AsyncMock(return_value={'result': 'success'})
    return mock


@pytest.fixture
def mock_logger():
    """Создает мок логгера"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def handler(mock_webhook_manager, mock_action_hub, mock_logger):
    """Создает экземпляр обработчика"""
    # Порядок параметров: webhook_manager, action_hub, logger
    return TelegramWebhookHandler(
        mock_webhook_manager,
        mock_action_hub,
        mock_logger
    )


@pytest.mark.asyncio
async def test_handle_missing_secret_token(handler):
    """Тест обработки запроса без secret_token"""
    request = Mock(spec=web.Request)
    request.headers = {}
    request.read = AsyncMock(return_value=b'{}')
    
    response = await handler.handle(request)
    
    assert response.status == 401
    assert "Missing secret token" in response.text

@pytest.mark.asyncio
async def test_handle_invalid_secret_token(handler, mock_webhook_manager):
    """Тест обработки запроса с невалидным secret_token"""
    mock_webhook_manager.get_bot_id_by_secret_token = AsyncMock(return_value=None)
    
    request = Mock(spec=web.Request)
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'invalid_token'}
    request.read = AsyncMock(return_value=b'{}')
    
    response = await handler.handle(request)
    
    assert response.status == 401
    assert "Invalid secret token" in response.text
    mock_webhook_manager.get_bot_id_by_secret_token.assert_called_once_with('invalid_token')


@pytest.mark.asyncio
async def test_handle_invalid_json(handler, mock_webhook_manager):
    """Тест обработки запроса с невалидным JSON"""
    bot_id = 123
    mock_webhook_manager.get_bot_id_by_secret_token = AsyncMock(return_value=bot_id)
    
    request = Mock(spec=web.Request)
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'valid_token'}
    request.read = AsyncMock(return_value=b'invalid json')
    
    response = await handler.handle(request)
    
    assert response.status == 400
    assert "Invalid JSON" in response.text
    handler.logger.error.assert_called()


@pytest.mark.asyncio
async def test_handle_valid_webhook(handler, mock_webhook_manager, mock_action_hub):
    """Тест обработки валидного вебхука"""
    bot_id = 123
    mock_webhook_manager.get_bot_id_by_secret_token = AsyncMock(return_value=bot_id)
    
    payload_data = {
        'update_id': 123456,
        'message': {
            'message_id': 1,
            'from': {'id': 789, 'first_name': 'Test'},
            'chat': {'id': 789, 'type': 'private'},
            'text': 'Hello'
        }
    }
    payload = json.dumps(payload_data).encode('utf-8')
    
    request = Mock(spec=web.Request)
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'valid_token'}
    request.read = AsyncMock(return_value=payload)
    
    response = await handler.handle(request)
    
    assert response.status == 200
    assert response.text == "OK"
    
    # Проверяем что execute_action был вызван
    mock_action_hub.execute_action.assert_called_once()
    call_args = mock_action_hub.execute_action.call_args
    assert call_args[0][0] == 'process_event'
    assert call_args[0][1]['system']['bot_id'] == bot_id
    assert call_args[0][1]['system']['source'] == 'webhook'
    assert call_args[1]['fire_and_forget'] is True


@pytest.mark.asyncio
async def test_handle_existing_system_data(handler, mock_webhook_manager, mock_action_hub):
    """Тест обработки вебхука с уже существующими system данными"""
    bot_id = 123
    mock_webhook_manager.get_bot_id_by_secret_token = AsyncMock(return_value=bot_id)
    
    payload_data = {
        'update_id': 123456,
        'system': {
            'some_field': 'value'
        },
        'message': {
            'message_id': 1,
            'text': 'Hello'
        }
    }
    payload = json.dumps(payload_data).encode('utf-8')
    
    request = Mock(spec=web.Request)
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'valid_token'}
    request.read = AsyncMock(return_value=payload)
    
    response = await handler.handle(request)
    
    assert response.status == 200
    
    # Проверяем что system данные были обновлены, а не перезаписаны
    call_args = mock_action_hub.execute_action.call_args
    assert call_args[0][1]['system']['bot_id'] == bot_id
    assert call_args[0][1]['system']['source'] == 'webhook'
    assert call_args[0][1]['system']['some_field'] == 'value'


@pytest.mark.asyncio
async def test_handle_action_hub_error(handler, mock_webhook_manager, mock_action_hub):
    """Тест обработки ошибки в ActionHub"""
    bot_id = 123
    mock_webhook_manager.get_bot_id_by_secret_token = AsyncMock(return_value=bot_id)
    mock_action_hub.execute_action = AsyncMock(side_effect=Exception("ActionHub error"))
    
    payload_data = {'update_id': 123456}
    payload = json.dumps(payload_data).encode('utf-8')
    
    request = Mock(spec=web.Request)
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'valid_token'}
    request.read = AsyncMock(return_value=payload)
    
    response = await handler.handle(request)
    
    # Все равно возвращаем 200, т.к. событие получено
    assert response.status == 200
    handler.logger.error.assert_called()


@pytest.mark.asyncio
async def test_handle_general_exception(handler, mock_webhook_manager):
    """Тест обработки общего исключения"""
    mock_webhook_manager.get_bot_id_by_secret_token = AsyncMock(side_effect=Exception("Unexpected error"))
    
    request = Mock(spec=web.Request)
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'valid_token'}
    request.read = AsyncMock(return_value=b'{}')
    
    response = await handler.handle(request)
    
    assert response.status == 500
    assert "Internal server error" in response.text
    handler.logger.error.assert_called()

