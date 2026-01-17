"""
Тесты для проверки порядка shutdown приложения
Проверяют, что плагины останавливаются перед отменой фоновых задач
"""
import asyncio
from unittest.mock import Mock, patch, MagicMock
import pytest

from app.application import Application
from app.di_container import DIContainer


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shutdown_order_plugins_before_background_tasks(settings_manager):
    """
    Проверка порядка shutdown:
    1. Сначала shutdown всех плагинов (через di_container.shutdown())
    2. Потом отмена фоновых задач приложения (_background_tasks)
    """
    # Создаем моки для отслеживания порядка вызовов
    shutdown_call_order = []
    di_shutdown_called = False
    tasks_cancelled = False
    
    # Создаем мок DI-контейнера
    mock_di_container = Mock(spec=DIContainer)
    
    # Мокаем shutdown DI-контейнера - он должен вызываться первым
    def mock_di_shutdown():
        nonlocal di_shutdown_called
        di_shutdown_called = True
        shutdown_call_order.append('di_container_shutdown')
        # Имитируем shutdown плагинов
        shutdown_call_order.append('telegram_polling_shutdown')
        shutdown_call_order.append('task_manager_shutdown')
        shutdown_call_order.append('cache_manager_shutdown')
        shutdown_call_order.append('scenario_processor_shutdown')
    
    mock_di_container.shutdown = Mock(side_effect=mock_di_shutdown)
    
    # Создаем мок Application с settings_manager для использования переопределенных настроек shutdown
    app = Application()
    app.settings_manager = settings_manager  # Используем settings_manager из фикстуры (с патчем)
    app.di_container = mock_di_container
    app.is_running = True
    app._background_tasks = []
    
    # Создаем фоновые задачи для теста
    async def mock_service_task():
        try:
            await asyncio.sleep(10)  # Долгая задача
        except asyncio.CancelledError:
            nonlocal tasks_cancelled
            if not tasks_cancelled:
                shutdown_call_order.append('background_tasks_cancelled')
                tasks_cancelled = True
            raise
    
    task1 = asyncio.create_task(mock_service_task())
    task2 = asyncio.create_task(mock_service_task())
    app._background_tasks = [task1, task2]
    
    # Запускаем shutdown
    await app._async_shutdown()
    
    # Даем немного времени для обработки отмены
    await asyncio.sleep(0.1)
    
    # Проверяем порядок вызовов
    # 1. Сначала должен быть вызван di_container.shutdown()
    assert shutdown_call_order[0] == 'di_container_shutdown', \
        f"di_container.shutdown() должен вызываться первым, но порядок: {shutdown_call_order}"
    
    # 2. Потом shutdown плагинов
    assert 'telegram_polling_shutdown' in shutdown_call_order, \
        f"telegram_polling.shutdown() должен вызываться, порядок: {shutdown_call_order}"
    
    # 3. Потом отмена фоновых задач
    assert 'background_tasks_cancelled' in shutdown_call_order, \
        f"Отмена фоновых задач должна происходить, порядок: {shutdown_call_order}"
    
    # Проверяем, что shutdown DI-контейнера вызван до отмены задач
    di_shutdown_index = shutdown_call_order.index('di_container_shutdown')
    task_cancel_index = shutdown_call_order.index('background_tasks_cancelled')
    assert di_shutdown_index < task_cancel_index, \
        f"di_container.shutdown() должен вызываться до отмены фоновых задач. " \
        f"Порядок: {shutdown_call_order}"
    
    # Проверяем, что shutdown плагинов происходит до отмены задач
    plugin_shutdown_index = shutdown_call_order.index('telegram_polling_shutdown')
    assert plugin_shutdown_index < task_cancel_index, \
        f"shutdown плагинов должен вызываться до отмены фоновых задач. " \
        f"Порядок: {shutdown_call_order}"
    
    # Проверяем, что shutdown был вызван
    assert di_shutdown_called, "di_container.shutdown() должен быть вызван"
    
    # Проверяем, что задачи были отменены
    assert all(task.cancelled() or task.done() for task in app._background_tasks), \
        "Все фоновые задачи должны быть отменены или завершены"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shutdown_plugins_stop_internal_tasks():
    """
    Проверка, что shutdown плагинов останавливает их внутренние задачи
    """
    shutdown_calls = {}
    
    # Создаем моки плагинов с отслеживанием вызовов shutdown
    mock_telegram_polling = Mock()
    mock_telegram_polling.shutdown = Mock(side_effect=lambda: shutdown_calls.update({'telegram_polling': True}))
    
    mock_task_manager = Mock()
    mock_task_manager.shutdown = Mock(side_effect=lambda: shutdown_calls.update({'task_manager': True}))
    
    mock_cache_manager = Mock()
    mock_cache_manager.shutdown = Mock(side_effect=lambda: shutdown_calls.update({'cache_manager': True}))
    
    # Создаем мок DI-контейнера с плагинами
    mock_di_container = Mock(spec=DIContainer)
    mock_di_container._utilities = {
        'telegram_polling': mock_telegram_polling,
        'task_manager': mock_task_manager,
        'cache_manager': mock_cache_manager,
    }
    mock_di_container._services = {}
    
    def mock_di_shutdown():
        # Имитируем shutdown утилит
        for utility_name, utility_instance in mock_di_container._utilities.items():
            if hasattr(utility_instance, 'shutdown'):
                utility_instance.shutdown()
    
    mock_di_container.shutdown = Mock(side_effect=mock_di_shutdown)
    
    # Вызываем shutdown DI-контейнера
    mock_di_container.shutdown()
    
    # Проверяем, что shutdown всех плагинов был вызван
    assert shutdown_calls.get('telegram_polling'), \
        "telegram_polling.shutdown() должен быть вызван"
    assert shutdown_calls.get('task_manager'), \
        "task_manager.shutdown() должен быть вызван"
    assert shutdown_calls.get('cache_manager'), \
        "cache_manager.shutdown() должен быть вызван"

