"""
Integration-тесты для Telegram вебхуков
Тестируют полный флоу от установки вебхука до получения и обработки обновлений

Примечание: эти тесты требуют, чтобы HTTP сервер был запущен.
Если порт занят или сервер отключен, тесты будут пропущены.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import web


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_endpoint_registered(initialized_di_container):
    """Тест что эндпоинт Telegram вебхука зарегистрирован"""
    http_server = initialized_di_container.get_utility('http_server')
    
    # Проверяем что эндпоинт зарегистрирован
    endpoint_found = False
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                endpoint_found = True
                break
    
    assert endpoint_found, "Эндпоинт /webhooks/telegram не зарегистрирован"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_handler_missing_secret_token(initialized_di_container):
    """Тест обработки вебхука без secret_token"""
    http_server = initialized_di_container.get_utility('http_server')
    
    # Запускаем сервер если не запущен
    if not http_server.is_running:
        success = await http_server.start()
        assert success is True
    
    # Получаем обработчик
    handler = None
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                handler = route.handler
                break
    
    assert handler is not None, "Обработчик для /webhooks/telegram не найден"
    
    # Создаем запрос без secret_token
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=b'{}')
    request.headers = {}
    
    response = await handler(request)
    
    assert response.status == 401
    assert "Missing secret token" in response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_handler_invalid_secret_token(initialized_di_container):
    """Тест обработки вебхука с невалидным secret_token"""
    http_server = initialized_di_container.get_utility('http_server')
    
    if not http_server.is_running:
        success = await http_server.start()
        assert success is True
    
    # Получаем обработчик
    handler = None
    for route in http_server.app.router.routes():
        if hasattr(route, 'resource') and route.resource:
            canonical = getattr(route.resource, 'canonical', None)
            if canonical == '/webhooks/telegram':
                handler = route.handler
                break
    
    assert handler is not None, "Обработчик для /webhooks/telegram не найден"
    
    # Создаем запрос с невалидным secret_token
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=b'{}')
    request.headers = {'X-Telegram-Bot-Api-Secret-Token': 'invalid_token_12345'}
    
    response = await handler(request)
    
    assert response.status == 401
    assert "Invalid secret token" in response.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_full_flow(initialized_di_container):
    """Тест полного флоу: установка вебхука → получение обновления → обработка"""
    bot_hub = initialized_di_container.get_service('bot_hub')
    http_server = initialized_di_container.get_utility('http_server')
    action_hub = initialized_di_container.get_utility('action_hub')
    cache_manager = initialized_di_container.get_utility('cache_manager')
    
    # Мокаем execute_action чтобы не делать реальную обработку
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
        # Запускаем сервер если не запущен
        if not http_server.is_running:
            success = await http_server.start()
            assert success is True
        
        # Тестовые данные
        test_bot_id = 999999
        test_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        
        # 1. Устанавливаем вебхук через WebhookManager
        # Получаем webhook_manager из bot_hub (он приватный, но доступен через атрибут)
        webhook_manager = bot_hub.webhook_manager
        
        # Мокаем успешный ответ от Telegram API
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={'ok': True})
        mock_response.status = 200
        
        # Правильный мок для aiohttp.ClientSession
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
        
        # 2. Проверяем что secret_token сохранен в кэш
        bot_id_from_cache = await webhook_manager.get_bot_id_by_secret_token(secret_token)
        assert bot_id_from_cache == test_bot_id
        
        # 3. Получаем обработчик
        handler = None
        for route in http_server.app.router.routes():
            if hasattr(route, 'resource') and route.resource:
                canonical = getattr(route.resource, 'canonical', None)
                if canonical == '/webhooks/telegram':
                    handler = route.handler
                    break
        
        assert handler is not None, "Обработчик для /webhooks/telegram не найден"
        
        # 4. Создаем тестовый payload от Telegram
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
        
        # 5. Создаем запрос с валидным secret_token
        request = Mock(spec=web.Request)
        request.read = AsyncMock(return_value=payload)
        request.headers = {'X-Telegram-Bot-Api-Secret-Token': secret_token}
        
        # 6. Вызываем обработчик
        response = await handler(request)
        
        # 7. Проверяем результат
        assert response.status == 200
        assert response.text == "OK"
        
        # 8. Проверяем что событие было отправлено в event_processor
        assert len(action_called) == 1
        assert action_called[0]['action'] == 'process_event'
        assert action_called[0]['data']['system']['bot_id'] == test_bot_id
        assert action_called[0]['data']['system']['source'] == 'webhook'
        assert action_called[0]['kwargs']['fire_and_forget'] is True
        
        # 9. Удаляем вебхук
        mock_response_delete = Mock()
        mock_response_delete.json = AsyncMock(return_value={'ok': True})
        
        # Правильный мок для aiohttp.ClientSession
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
        # Восстанавливаем оригинальный метод
        action_hub.execute_action = original_execute_action


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_ssl_certificate_generation(initialized_di_container):
    """Тест автоматической генерации SSL-сертификата"""
    http_server = initialized_di_container.get_utility('http_server')
    settings_manager = initialized_di_container.get_utility('settings_manager')
    
    # Устанавливаем external_url для генерации сертификата
    settings = settings_manager.get_plugin_settings('http_server')
    if settings.get('external_url'):
        # Проверяем что сертификат был сгенерирован
        assert http_server.ssl_context is not None
        assert http_server._certificate_pem is not None
        assert http_server._private_key_pem is not None
        
        # Проверяем что можно получить сертификат
        cert_result = http_server.get_certificate()
        assert cert_result is not None
        cert_pem, key_pem = cert_result
        assert isinstance(cert_pem, bytes)
        assert isinstance(key_pem, bytes)
        assert b'BEGIN CERTIFICATE' in cert_pem
        assert b'BEGIN PRIVATE KEY' in key_pem

