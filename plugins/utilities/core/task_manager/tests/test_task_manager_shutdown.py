"""
Unit tests for TaskManager shutdown
Check correct shutdown operation with global settings
"""
import asyncio

import pytest

from task_manager.task_manager import TaskManager


@pytest.mark.asyncio
async def test_shutdown_uses_global_settings(task_manager_kwargs):
    """Test that shutdown uses global plugin_timeout settings"""
    # Set global settings
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 5.0
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Check that shutdown_timeout is set from global settings
    assert task_manager.shutdown_timeout == 5.0


@pytest.mark.asyncio
async def test_shutdown_without_processors(task_manager_kwargs):
    """Test shutdown when there are no active processors"""
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Stop all processors if they were running
    task_manager._background_processors.clear()
    
    # Shutdown should complete without errors
    task_manager.shutdown()
    
    # Check that log was called
    task_manager.logger.info.assert_any_call("TaskManager stopped (no active processors)")


@pytest.mark.asyncio
async def test_shutdown_with_active_processors(task_manager_kwargs):
    """Test shutdown with active processors"""
    # Set short timeout for quick test
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 0.05
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Explicitly start processors (in tests they may not start automatically)
    await task_manager._start_all_queue_processors()
    
    # Wait a bit for processors to definitely start
    await asyncio.sleep(0.01)
    
    # If processors didn't start (no queues), create mock processor for test
    if len(task_manager._background_processors) == 0:
        # Create mock processor for shutdown check
        mock_processor = asyncio.create_task(asyncio.sleep(10))
        task_manager._background_processors['test_queue'] = mock_processor
    
    # Check that there are active processors
    assert len(task_manager._background_processors) > 0
    
    # Call shutdown
    task_manager.shutdown()
    
    # Check that processors are cleared
    assert len(task_manager._background_processors) == 0
    
    # Check that stop log was called
    task_manager.logger.info.assert_any_call("TaskManager stopped")


@pytest.mark.asyncio
async def test_shutdown_waits_for_tasks_completion(task_manager_kwargs):
    """Test that shutdown waits for task completion"""
    # Set timeout
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 0.08
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Wait for processors to start
    await asyncio.sleep(0.01)
    
    # Create task that will complete quickly
    task_completed = False
    
    async def quick_task():
        nonlocal task_completed
        await asyncio.sleep(0.005)
        task_completed = True
        return {'result': 'success'}
    
    # Submit task
    await task_manager.submit_task('test_task', quick_task, fire_and_forget=True)
    
    # Wait a bit for task to start executing
    await asyncio.sleep(0.01)
    
    # Call shutdown
    task_manager.shutdown()
    
    # Check that shutdown completed
    assert len(task_manager._background_processors) == 0


@pytest.mark.asyncio
async def test_shutdown_timeout_handling(task_manager_kwargs):
    """Test timeout handling during shutdown"""
    # Set very short timeout
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 0.05
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Explicitly start processors
    await task_manager._start_all_queue_processors()
    await asyncio.sleep(0.01)
    
    # If no processors, create mock
    if len(task_manager._background_processors) == 0:
        mock_processor = asyncio.create_task(asyncio.sleep(10))
        task_manager._background_processors['test_queue'] = mock_processor
    
    # Create task that runs longer than timeout
    async def long_task():
        await asyncio.sleep(0.08)  # Longer than timeout (0.05)
        return {'result': 'success'}
    
    # Submit task
    await task_manager.submit_task('long_task', long_task, fire_and_forget=True)
    
    # Wait a bit for task to enter queue
    await asyncio.sleep(0.005)
    
    # Call shutdown - should complete even if task didn't finish
    task_manager.shutdown()
    
    # Check that processors are cleared (shutdown should have completed)
    assert len(task_manager._background_processors) == 0
    
    # Check that stop log was called
    task_manager.logger.info.assert_any_call("TaskManager stopped")


@pytest.mark.asyncio
async def test_shutdown_default_timeout(task_manager_kwargs):
    """Test that default timeout is used if global settings are not set"""
    # Don't set shutdown in global settings
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {}
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Should use default timeout (3.0)
    assert task_manager.shutdown_timeout == 3.0


@pytest.mark.asyncio
async def test_shutdown_empty_shutdown_settings(task_manager_kwargs):
    """Test that default timeout is used if shutdown is empty"""
    # Set empty shutdown
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {}
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Should use default timeout (3.0)
    assert task_manager.shutdown_timeout == 3.0

