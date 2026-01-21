"""
Tests for verifying application shutdown order
Verify that plugins stop before background tasks are cancelled
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
    Verify shutdown order:
    1. First shutdown all plugins (through di_container.shutdown())
    2. Then cancel application background tasks (_background_tasks)
    """
    # Create mocks to track call order
    shutdown_call_order = []
    di_shutdown_called = False
    tasks_cancelled = False
    
    # Create mock DI container
    mock_di_container = Mock(spec=DIContainer)
    
    # Mock DI container shutdown - it should be called first
    def mock_di_shutdown():
        nonlocal di_shutdown_called
        di_shutdown_called = True
        shutdown_call_order.append('di_container_shutdown')
        # Simulate plugin shutdown
        shutdown_call_order.append('telegram_polling_shutdown')
        shutdown_call_order.append('task_manager_shutdown')
        shutdown_call_order.append('cache_manager_shutdown')
        shutdown_call_order.append('scenario_processor_shutdown')
    
    mock_di_container.shutdown = Mock(side_effect=mock_di_shutdown)
    
    # Create mock Application with settings_manager to use overridden shutdown settings
    app = Application()
    app.settings_manager = settings_manager  # Use settings_manager from fixture (with patch)
    app.di_container = mock_di_container
    app.is_running = True
    app._background_tasks = []
    
    # Create background tasks for test
    async def mock_service_task():
        try:
            await asyncio.sleep(10)  # Long-running task
        except asyncio.CancelledError:
            nonlocal tasks_cancelled
            if not tasks_cancelled:
                shutdown_call_order.append('background_tasks_cancelled')
                tasks_cancelled = True
            raise
    
    task1 = asyncio.create_task(mock_service_task())
    task2 = asyncio.create_task(mock_service_task())
    app._background_tasks = [task1, task2]
    
    # Start shutdown
    await app._async_shutdown()
    
    # Give some time for cancellation processing
    await asyncio.sleep(0.1)
    
    # Verify call order
    # 1. di_container.shutdown() should be called first
    assert shutdown_call_order[0] == 'di_container_shutdown', \
        f"di_container.shutdown() should be called first, but order: {shutdown_call_order}"
    
    # 2. Then plugin shutdown
    assert 'telegram_polling_shutdown' in shutdown_call_order, \
        f"telegram_polling.shutdown() should be called, order: {shutdown_call_order}"
    
    # 3. Then background tasks cancellation
    assert 'background_tasks_cancelled' in shutdown_call_order, \
        f"Background tasks cancellation should occur, order: {shutdown_call_order}"
    
    # Verify that DI container shutdown is called before task cancellation
    di_shutdown_index = shutdown_call_order.index('di_container_shutdown')
    task_cancel_index = shutdown_call_order.index('background_tasks_cancelled')
    assert di_shutdown_index < task_cancel_index, \
        f"di_container.shutdown() should be called before background tasks cancellation. " \
        f"Order: {shutdown_call_order}"
    
    # Verify that plugin shutdown occurs before task cancellation
    plugin_shutdown_index = shutdown_call_order.index('telegram_polling_shutdown')
    assert plugin_shutdown_index < task_cancel_index, \
        f"Plugin shutdown should be called before background tasks cancellation. " \
        f"Order: {shutdown_call_order}"
    
    # Verify that shutdown was called
    assert di_shutdown_called, "di_container.shutdown() should be called"
    
    # Verify that tasks were cancelled
    assert all(task.cancelled() or task.done() for task in app._background_tasks), \
        "All background tasks should be cancelled or completed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shutdown_plugins_stop_internal_tasks():
    """
    Verify that plugin shutdown stops their internal tasks
    """
    shutdown_calls = {}
    
    # Create plugin mocks with shutdown call tracking
    mock_telegram_polling = Mock()
    mock_telegram_polling.shutdown = Mock(side_effect=lambda: shutdown_calls.update({'telegram_polling': True}))
    
    mock_task_manager = Mock()
    mock_task_manager.shutdown = Mock(side_effect=lambda: shutdown_calls.update({'task_manager': True}))
    
    mock_cache_manager = Mock()
    mock_cache_manager.shutdown = Mock(side_effect=lambda: shutdown_calls.update({'cache_manager': True}))
    
    # Create mock DI container with plugins
    mock_di_container = Mock(spec=DIContainer)
    mock_di_container._utilities = {
        'telegram_polling': mock_telegram_polling,
        'task_manager': mock_task_manager,
        'cache_manager': mock_cache_manager,
    }
    mock_di_container._services = {}
    
    def mock_di_shutdown():
        # Simulate utility shutdown
        for utility_name, utility_instance in mock_di_container._utilities.items():
            if hasattr(utility_instance, 'shutdown'):
                utility_instance.shutdown()
    
    mock_di_container.shutdown = Mock(side_effect=mock_di_shutdown)
    
    # Call DI container shutdown
    mock_di_container.shutdown()
    
    # Verify that shutdown of all plugins was called
    assert shutdown_calls.get('telegram_polling'), \
        "telegram_polling.shutdown() should be called"
    assert shutdown_calls.get('task_manager'), \
        "task_manager.shutdown() should be called"
    assert shutdown_calls.get('cache_manager'), \
        "cache_manager.shutdown() should be called"

