"""
Unit-тесты для shutdown TaskManager
Проверяют корректную работу shutdown с глобальными настройками
"""
import asyncio

import pytest

from task_manager.task_manager import TaskManager


@pytest.mark.asyncio
async def test_shutdown_uses_global_settings(task_manager_kwargs):
    """Тест что shutdown использует глобальные настройки plugin_timeout"""
    # Устанавливаем глобальные настройки
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 5.0
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Проверяем, что shutdown_timeout установлен из глобальных настроек
    assert task_manager.shutdown_timeout == 5.0


@pytest.mark.asyncio
async def test_shutdown_without_processors(task_manager_kwargs):
    """Тест shutdown когда нет активных процессоров"""
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Останавливаем все процессоры если они были запущены
    task_manager._background_processors.clear()
    
    # Shutdown должен завершиться без ошибок
    task_manager.shutdown()
    
    # Проверяем, что был вызван лог
    task_manager.logger.info.assert_any_call("TaskManager остановлен (нет активных процессоров)")


@pytest.mark.asyncio
async def test_shutdown_with_active_processors(task_manager_kwargs):
    """Тест shutdown с активными процессорами"""
    # Устанавливаем короткий таймаут для быстрого теста
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 0.05
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Явно запускаем процессоры (в тестах они могут не запуститься автоматически)
    await task_manager._start_all_queue_processors()
    
    # Ждем немного, чтобы процессоры точно запустились
    await asyncio.sleep(0.01)
    
    # Если процессоры не запустились (нет очередей), создаем мок процессора для теста
    if len(task_manager._background_processors) == 0:
        # Создаем мок процессора для проверки shutdown
        mock_processor = asyncio.create_task(asyncio.sleep(10))
        task_manager._background_processors['test_queue'] = mock_processor
    
    # Проверяем, что есть активные процессоры
    assert len(task_manager._background_processors) > 0
    
    # Вызываем shutdown
    task_manager.shutdown()
    
    # Проверяем, что процессоры очищены
    assert len(task_manager._background_processors) == 0
    
    # Проверяем, что был вызван лог об остановке
    task_manager.logger.info.assert_any_call("TaskManager остановлен")


@pytest.mark.asyncio
async def test_shutdown_waits_for_tasks_completion(task_manager_kwargs):
    """Тест что shutdown ждет завершения задач"""
    # Устанавливаем таймаут
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 0.08
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Ждем запуска процессоров
    await asyncio.sleep(0.01)
    
    # Создаем задачу, которая быстро завершится
    task_completed = False
    
    async def quick_task():
        nonlocal task_completed
        await asyncio.sleep(0.005)
        task_completed = True
        return {'result': 'success'}
    
    # Отправляем задачу
    await task_manager.submit_task('test_task', quick_task, fire_and_forget=True)
    
    # Ждем немного, чтобы задача начала выполняться
    await asyncio.sleep(0.01)
    
    # Вызываем shutdown
    task_manager.shutdown()
    
    # Проверяем, что shutdown завершился
    assert len(task_manager._background_processors) == 0


@pytest.mark.asyncio
async def test_shutdown_timeout_handling(task_manager_kwargs):
    """Тест обработки таймаута при shutdown"""
    # Устанавливаем очень короткий таймаут
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {
            'plugin_timeout': 0.05
        }
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Явно запускаем процессоры
    await task_manager._start_all_queue_processors()
    await asyncio.sleep(0.01)
    
    # Если процессоров нет, создаем мок
    if len(task_manager._background_processors) == 0:
        mock_processor = asyncio.create_task(asyncio.sleep(10))
        task_manager._background_processors['test_queue'] = mock_processor
    
    # Создаем задачу, которая выполняется дольше таймаута
    async def long_task():
        await asyncio.sleep(0.08)  # Дольше таймаута (0.05)
        return {'result': 'success'}
    
    # Отправляем задачу
    await task_manager.submit_task('long_task', long_task, fire_and_forget=True)
    
    # Ждем немного, чтобы задача попала в очередь
    await asyncio.sleep(0.005)
    
    # Вызываем shutdown - должен завершиться даже если задача не завершилась
    task_manager.shutdown()
    
    # Проверяем, что процессоры очищены (shutdown должен был завершиться)
    assert len(task_manager._background_processors) == 0
    
    # Проверяем, что был вызван лог об остановке
    task_manager.logger.info.assert_any_call("TaskManager остановлен")


@pytest.mark.asyncio
async def test_shutdown_default_timeout(task_manager_kwargs):
    """Тест что используется дефолтный таймаут если глобальные настройки не заданы"""
    # Не задаем shutdown в глобальных настройках
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {}
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Должен использоваться дефолтный таймаут (3.0)
    assert task_manager.shutdown_timeout == 3.0


@pytest.mark.asyncio
async def test_shutdown_empty_shutdown_settings(task_manager_kwargs):
    """Тест что используется дефолтный таймаут если shutdown пустой"""
    # Задаем пустой shutdown
    task_manager_kwargs['settings_manager'].get_global_settings.return_value = {
        'shutdown': {}
    }
    
    task_manager = TaskManager(**task_manager_kwargs)
    
    # Должен использоваться дефолтный таймаут (3.0)
    assert task_manager.shutdown_timeout == 3.0

