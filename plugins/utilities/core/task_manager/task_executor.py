import asyncio
from typing import Any, Dict

from .types import TaskItem


class TaskExecutor:
    """Выполнение задач с семафорами и контролем"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.queue_manager = kwargs['queue_manager']
        
        # Статистика
        self.stats = {
            'total_completed': 0,
            'total_failed': 0,
            'total_timeout': 0,
            'total_retries': 0
        }
    
    async def execute_task_with_semaphore(self, task_item: TaskItem, queue_manager, queue_name: str):
        """Выполняет задачу с контролем семафора"""
        semaphore = queue_manager.semaphores[queue_name]
        
        # Если семафор занят - задача будет ждать
        if semaphore._value <= 0:
            self.logger.warning(f"Задача {task_item.id} ожидает освобождения семафора очереди {queue_name}")
        
        async with semaphore:  # Ограничиваем одновременные задачи
            try:
                
                # Выполняем задачу с таймаутом
                try:
                    result = await asyncio.wait_for(
                        task_item.coro(), 
                        timeout=task_item.config.timeout
                    )
                    
                    # Устанавливаем результат в Future
                    if task_item.future and not task_item.future.done():
                        task_item.future.set_result(result)
                    
                    self.stats['total_completed'] += 1
                    
                except Exception as e:
                    # Устанавливаем ошибку в Future
                    if task_item.future and not task_item.future.done():
                        task_item.future.set_exception(e)
                    raise
                
            except asyncio.TimeoutError:
                self.stats['total_timeout'] += 1
                self.logger.warning(f"Задача {task_item.id} превысила таймаут {task_item.config.timeout}с")
                
                # Устанавливаем таймаут в Future
                if task_item.future and not task_item.future.done():
                    task_item.future.set_exception(asyncio.TimeoutError(f"Задача {task_item.id} превысила таймаут"))
                
            except Exception as e:
                self.stats['total_failed'] += 1
                self.logger.error(f"Ошибка выполнения задачи {task_item.id}: {e}")
                
                # Повторная попытка
                if task_item.retry_count < task_item.config.retry_count:
                    task_item.retry_count += 1
                    self.stats['total_retries'] += 1
                    self.logger.info(f"Повторная попытка {task_item.retry_count}/{task_item.config.retry_count} для задачи {task_item.id}")
                    
                    await asyncio.sleep(task_item.config.retry_delay)
                    
                    # Добавляем задачу обратно в очередь
                    await queue_manager.task_queues[queue_name].put(task_item)
            
            finally:
                pass
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику выполнения задач"""
        return self.stats.copy()
