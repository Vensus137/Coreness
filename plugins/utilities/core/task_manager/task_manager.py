import asyncio
import concurrent.futures
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from .queue_manager import QueueManager
from .task_executor import TaskExecutor
from .types import TaskItem


class TaskManager:
    """Universal utility for managing background tasks"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Get ALL settings centrally
        settings = self.settings_manager.get_plugin_settings('task_manager')
        
        # Main TaskManager settings
        self.default_queue = settings.get('default_queue', 'action')
        
        # Settings for submodules
        self.wait_interval = settings.get('wait_interval', 1.0)
        
        # Get shutdown_timeout from global settings
        global_settings = self.settings_manager.get_global_settings()
        shutdown_settings = global_settings.get('shutdown', {})
        self.shutdown_timeout = shutdown_settings.get('plugin_timeout', 3.0)
        
        # Initialize components
        self.queue_manager = QueueManager(
            logger=self.logger,
            settings_manager=self.settings_manager,
            wait_interval=self.wait_interval
        )
        self.task_executor = TaskExecutor(logger=self.logger, queue_manager=self.queue_manager)
        
        # Active queue processors
        self._background_processors = {}
        
        # Statistics
        self.stats = {
            'total_submitted': 0,
            'queue_sizes': dict.fromkeys(self.queue_manager.get_available_queues(), 0)
        }
        
        # Automatically start all queue processors
        asyncio.create_task(self._start_all_queue_processors())
    
    async def submit_task(self, 
                         task_id: str, 
                         coro: Callable, 
                         queue_name: Optional[str] = None,
                         fire_and_forget: bool = False,
                         return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Public method - submits task to corresponding queue
        """
        try:
            # Determine target queue
            target_queue = self._determine_target_queue(queue_name)
            
            # Tasks are always accepted into queue
            # Limits are applied only when executing tasks
            
            # Automatically start queue processor
            if target_queue not in self._background_processors:
                await self._start_queue_processor(target_queue)
            
            # Get queue configuration
            config = self.queue_manager.get_queue_config(target_queue)
            
            # Create Future for tracking result
            # Future is created if: not fire_and_forget OR return_future=True
            future = None
            if return_future or not fire_and_forget:
                future = asyncio.Future()
            
            # Create task item
            task_item = TaskItem(
                id=task_id,
                coro=coro,
                config=config,
                created_at=datetime.now(),
                future=future
            )
            
            # Add to queue
            await self.queue_manager.task_queues[target_queue].put(task_item)
            
            # Update statistics
            self.stats['total_submitted'] += 1
            self.stats['queue_sizes'][target_queue] += 1

            # If return_future - return Future for tracking
            if return_future:
                return future
            
            # If fire_and_forget - immediately return success
            if fire_and_forget:
                return {"result": "success"}
            
            # If not fire_and_forget - wait for execution result
            result = await future
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding task {task_id}: {e}")
            # If return_future - create Future with error
            if return_future:
                error_future = asyncio.Future()
                error_future.set_exception(e)
                return error_future
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _determine_target_queue(self, queue_name: Optional[str]) -> str:
        """Determines target queue based on name"""
        
        # If queue name specified
        if queue_name:
            if self.queue_manager.is_queue_valid(queue_name):
                return queue_name
            else:
                self.logger.warning(f"Unknown queue '{queue_name}', using '{self.default_queue}'")
                return self.default_queue
        
        # By default - default queue
        return self.default_queue
    
    async def _start_queue_processor(self, queue_name: str):
        """Starts queue processor in background (private method)"""
        if queue_name in self._background_processors:
            return  # Already started
        
        try:
            # Create background task
            processor_task = asyncio.create_task(
                self._run_background_processor(queue_name),
                name=f"queue_processor_{queue_name}"
            )
            
            self._background_processors[queue_name] = processor_task
            
        except Exception as e:
            self.logger.error(f"Error starting queue processor {queue_name}: {e}")
    
    async def _stop_queue_processor(self, queue_name: str):
        """Stops queue processor (private method)"""
        if queue_name not in self._background_processors:
            return
        
        try:
            processor_task = self._background_processors[queue_name]
            processor_task.cancel()
            
            try:
                await processor_task
            except asyncio.CancelledError:
                pass
            
            del self._background_processors[queue_name]
            self.logger.info(f"Queue processor {queue_name} stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping queue processor {queue_name}: {e}")
    
    async def _run_background_processor(self, queue_name: str):
        """Processes queue in background (private method)"""
        queue = self.queue_manager.task_queues[queue_name]
        config = self.queue_manager.get_queue_config(queue_name)
        
        self.logger.info(f"Queue processor {queue_name} started")
        
        while True:
            try:
                # Get task from queue
                task_item = await queue.get()
                
                # Start task with semaphore control (semaphore itself controls queue limits)
                asyncio.create_task(
                    self.task_executor.execute_task_with_semaphore(task_item, self.queue_manager, queue_name)
                )
                
            except asyncio.CancelledError:
                self.logger.info(f"Queue processor {queue_name} stopped")
                break
            except Exception as e:
                self.logger.error(f"Error in queue processor {queue_name}: {e}")
                # Use queue settings for delay
                await asyncio.sleep(config.retry_delay)
    
    async def _start_all_queue_processors(self):
        """Starts processors for all queues (private method)"""
        for queue_name in self.queue_manager.queue_configs.keys():
            await self._start_queue_processor(queue_name)
        self.logger.info(f"Started processors for {len(self.queue_manager.queue_configs)} queues")
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Returns TaskManager statistics"""
        executor_stats = self.task_executor.get_stats()
        
        return {
            'stats': {
                **self.stats,
                **executor_stats
            },
            'active_processors': [p.get_name() for p in self._background_processors.values()],
            'queue_sizes': {k: v.qsize() for k, v in self.queue_manager.task_queues.items()},
            'semaphore_values': {k: v._value for k, v in self.queue_manager.semaphores.items()},
            'active_tasks': {k: self.queue_manager.get_queue_config(k).max_concurrent - v._value for k, v in self.queue_manager.semaphores.items()}
        }
    
    def shutdown(self):
        """Synchronous graceful shutdown of utility"""
        self.logger.info("Shutdown TaskManager...")
        
        # If no active processors, just exit
        if not self._background_processors:
            self.logger.info("TaskManager stopped (no active processors)")
            return
        
        # Cancel all background tasks
        tasks_to_wait = []
        for queue_name in list(self._background_processors.keys()):
            processor_task = self._background_processors[queue_name]
            try:
                # Cancel task
                processor_task.cancel()
                tasks_to_wait.append(processor_task)
            except Exception as e:
                # Log error but continue shutdown
                self.logger.warning(f"Error canceling queue processor {queue_name}: {e}")
        
        # Wait for all tasks to complete with timeout
        async def _wait_for_shutdown():
            """Wait for all canceled tasks to complete"""
            if not tasks_to_wait:
                return
            
            try:
                # Check that all tasks belong to current loop
                current_loop = asyncio.get_running_loop()
                valid_tasks = []
                for task in tasks_to_wait:
                    # Check that task belongs to current loop
                    try:
                        if hasattr(task, 'get_loop') and task.get_loop() == current_loop:
                            valid_tasks.append(task)
                        elif not hasattr(task, 'get_loop'):
                            # If no get_loop method, try to use task
                            # (may be from same loop if created in correct context)
                            valid_tasks.append(task)
                    except Exception:
                        # If can't check, skip task
                        pass
                
                if not valid_tasks:
                    # If no valid tasks, just exit
                    return
                
                # Wait for all tasks to complete with CancelledError handling
                # Use asyncio.gather to wait for all tasks simultaneously
                # return_exceptions=True allows not interrupting wait on errors
                await asyncio.wait_for(
                    asyncio.gather(*valid_tasks, return_exceptions=True),
                    timeout=self.shutdown_timeout
                )
                self.logger.info("All tasks completed successfully")
            except asyncio.TimeoutError:
                self.logger.warning(f"Timeout waiting for tasks to complete ({self.shutdown_timeout} sec), forcing shutdown")
            except Exception as e:
                # Log all errors - task filtering by loop already done above
                self.logger.warning(f"Error waiting for tasks to complete: {e}")
        
        try:
            # Try to wait for tasks to complete in existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, use run_coroutine_threadsafe to execute in correct loop
                # This works even if shutdown() is called from another thread (via asyncio.to_thread)
                try:
                    future = asyncio.run_coroutine_threadsafe(_wait_for_shutdown(), loop)
                    # Wait for completion with timeout (use same timeout as inside _wait_for_shutdown)
                    # If coroutine completes earlier (successfully or by timeout), future.result() returns immediately
                    future.result(timeout=self.shutdown_timeout)
                except concurrent.futures.TimeoutError:
                    self.logger.warning(f"Timeout waiting for tasks to complete ({self.shutdown_timeout} sec), forcing shutdown")
                except Exception as e:
                    # Log all errors - task filtering by loop already done in _wait_for_shutdown
                    self.logger.warning(f"Error waiting for tasks to complete: {e}")
            else:
                # If loop not running, start it for shutdown with timeout
                try:
                    loop.run_until_complete(_wait_for_shutdown())
                except Exception as e:
                    self.logger.warning(f"Error waiting for tasks to complete: {e}")
        except RuntimeError:
            # If no event loop, create new one
            try:
                asyncio.run(_wait_for_shutdown())
            except Exception as e:
                self.logger.warning(f"Error waiting for tasks to complete: {e}")
        except Exception as e:
            self.logger.warning(f"Error shutting down TaskManager: {e}")
        
        # Clear processors dictionary
        self._background_processors.clear()
        
        self.logger.info("TaskManager stopped")