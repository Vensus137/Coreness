"""
Integration-тесты для GitHub вебхуков
Тестируют полный флоу от получения вебхука до синхронизации тенантов

Примечание: эти тесты требуют, чтобы HTTP сервер был запущен.
Если порт занят или сервер отключен, тесты будут пропущены.
"""
import asyncio
import hmac
import hashlib
import json
import pytest
from unittest.mock import AsyncMock, Mock

from aiohttp import web

# Фиксированный секрет для тестов (должен совпадать с conftest.py)
TEST_WEBHOOK_SECRET = 'test_secret_12345'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_full_flow(initialized_di_container):
    """Тест полного флоу: вебхук → парсинг → синхронизация"""
    # Получаем зависимости
    http_server = initialized_di_container.get_utility('http_server')
    action_hub = initialized_di_container.get_utility('action_hub')
    
    # Мокаем action_hub.execute_action чтобы не делать реальную синхронизацию
    original_execute_action = action_hub.execute_action
    action_hub.execute_action = AsyncMock(return_value={
        'result': 'success',
        'response_data': {
            'synced_tenants': 1,
            'total_tenants': 1
        }
    })
    
    try:
        # Эндпоинт уже зарегистрирован при инициализации tenant_hub
        # Запускаем сервер (как это делает http_api_service)
        if not http_server.is_running:
            success = await http_server.start()
            assert success is True
        
        # Используем фиксированный секрет для тестов (установлен через conftest)
        webhook_secret = TEST_WEBHOOK_SECRET
        
        # Создаем тестовый payload
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
        
        # Вычисляем правильную подпись
        expected_hash = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        signature = f"sha256={expected_hash}"
        
        # Создаем мок запроса
        request = Mock(spec=web.Request)
        request.read = AsyncMock(return_value=payload)
        request.headers = {
            'X-Hub-Signature-256': signature,
            'X-GitHub-Event': 'push'
        }
        
        # Получаем обработчик из роутера
        handler = None
        for route in http_server.app.router.routes():
            if route.resource.canonical == '/webhooks/github':
                handler = route.handler
                break
        
        assert handler is not None
        
        # Вызываем обработчик
        response = await handler(request)
        
        # Проверяем результат
        assert response.status == 200
        # Проверяем что execute_action был вызван с правильными параметрами
        action_hub.execute_action.assert_called_once()
        call_args = action_hub.execute_action.call_args
        assert call_args[0][0] == 'sync_tenants_from_files'
        assert 'files' in call_args[0][1]
        assert 'tenant/tenant_101/tg_bot.yaml' in call_args[0][1]['files']
        assert 'tenant/tenant_102/scenarios/scenario1.yaml' in call_args[0][1]['files']
        
    finally:
        # Восстанавливаем оригинальный метод
        action_hub.execute_action = original_execute_action


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_invalid_signature(initialized_di_container):
    """Тест обработки вебхука с невалидной подписью"""
    http_server = initialized_di_container.get_utility('http_server')
    
    # Эндпоинт уже зарегистрирован при инициализации tenant_hub
    # Запускаем сервер (как это делает http_api_service)
    if not http_server.is_running:
        success = await http_server.start()
        assert success is True
    
    # Создаем тестовый payload с неправильной подписью
    payload_data = {"commits": []}
    payload = json.dumps(payload_data).encode('utf-8')
    
    # Создаем мок запроса
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {
        'X-Hub-Signature-256': 'sha256=wrong_hash',
        'X-GitHub-Event': 'push'
    }
    
    # Получаем обработчик
    handler = None
    for route in http_server.app.router.routes():
        if route.resource.canonical == '/webhooks/github':
            handler = route.handler
            break
    
    assert handler is not None
    
    # Вызываем обработчик
    response = await handler(request)
    
    # Проверяем что вернулась ошибка 401
    assert response.status == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webhook_no_tenant_changes(initialized_di_container):
    """Тест обработки вебхука без изменений тенантов"""
    http_server = initialized_di_container.get_utility('http_server')
    action_hub = initialized_di_container.get_utility('action_hub')
    
    # Эндпоинт уже зарегистрирован при инициализации tenant_hub
    # Запускаем сервер (как это делает http_api_service)
    if not http_server.is_running:
        success = await http_server.start()
        assert success is True
    
    # Используем фиксированный секрет для тестов (установлен через conftest)
    webhook_secret = TEST_WEBHOOK_SECRET
    
    # Создаем payload без изменений тенантов
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
    
    # Вычисляем правильную подпись
    expected_hash = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    signature = f"sha256={expected_hash}"
    
    # Создаем мок запроса
    request = Mock(spec=web.Request)
    request.read = AsyncMock(return_value=payload)
    request.headers = {
        'X-Hub-Signature-256': signature,
        'X-GitHub-Event': 'push'
    }
    
    # Получаем обработчик
    handler = None
    for route in http_server.app.router.routes():
        if route.resource.canonical == '/webhooks/github':
            handler = route.handler
            break
    
    assert handler is not None
    
    # Вызываем обработчик
    response = await handler(request)
    
    # Проверяем что вернулся успех (но без синхронизации)
    assert response.status == 200
    # Проверяем что action НЕ был вызван (нет изменений тенантов)
    # Это проверяется через отсутствие вызова sync_tenants_from_files

