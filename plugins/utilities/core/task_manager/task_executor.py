import asyncio
from typing import Any, Dict

from .types import TaskItem


class TaskExecutor:
    """Task execution with semaphores and control"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.queue_manager = kwargs['queue_manager']
        
        # Statistics
        self.stats = {
            'total_completed': 0,
            'total_failed': 0,
            'total_timeout': 0,
            'total_retries': 0
        }
    
    async def execute_task_with_semaphore(self, task_item: TaskItem, queue_manager, queue_name: str):
        """Executes task with semaphore control"""
        semaphore = queue_manager.semaphores[queue_name]
        
        # If semaphore is busy - task will wait
        if semaphore._value <= 0:
            self.logger.warning(f"Task {task_item.id} waiting for semaphore release in queue {queue_name}")
        
        async with semaphore:  # Limit concurrent tasks
            try:
                
                # Execute task with timeout
                try:
                    result = await asyncio.wait_for(
                        task_item.coro(), 
                        timeout=task_item.config.timeout
                    )
                    
                    # Set result in Future
                    if task_item.future and not task_item.future.done():
                        task_item.future.set_result(result)
                    
                    self.stats['total_completed'] += 1
                    
                except Exception as e:
                    # Set error in Future
                    if task_item.future and not task_item.future.done():
                        task_item.future.set_exception(e)
                    raise
                
            except asyncio.TimeoutError:
                self.stats['total_timeout'] += 1
                self.logger.warning(f"Task {task_item.id} exceeded timeout {task_item.config.timeout}s")
                
                # Set timeout in Future
                if task_item.future and not task_item.future.done():
                    task_item.future.set_exception(asyncio.TimeoutError(f"Task {task_item.id} exceeded timeout"))
                
            except Exception as e:
                self.stats['total_failed'] += 1
                self.logger.error(f"Error executing task {task_item.id}: {e}")
                
                # Retry
                if task_item.retry_count < task_item.config.retry_count:
                    task_item.retry_count += 1
                    self.stats['total_retries'] += 1
                    self.logger.info(f"Retry {task_item.retry_count}/{task_item.config.retry_count} for task {task_item.id}")
                    
                    await asyncio.sleep(task_item.config.retry_delay)
                    
                    # Add task back to queue
                    await queue_manager.task_queues[queue_name].put(task_item)
            
            finally:
                pass
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Returns task execution statistics"""
        return self.stats.copy()
