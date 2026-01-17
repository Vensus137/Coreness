import asyncio
import concurrent.futures
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from .queue_manager import QueueManager
from .task_executor import TaskExecutor
from .types import TaskItem


class TaskManager:
    """Универсальная утилита для управления фоновыми задачами"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Получаем ВСЕ настройки централизованно
        settings = self.settings_manager.get_plugin_settings('task_manager')
        
        # Основные настройки TaskManager
        self.default_queue = settings.get('default_queue', 'action')
        
        # Настройки для подмодулей
        self.wait_interval = settings.get('wait_interval', 1.0)
        
        # Получаем shutdown_timeout из глобальных настроек
        global_settings = self.settings_manager.get_global_settings()
        shutdown_settings = global_settings.get('shutdown', {})
        self.shutdown_timeout = shutdown_settings.get('plugin_timeout', 3.0)
        
        # Инициализируем компоненты
        self.queue_manager = QueueManager(
            logger=self.logger,
            settings_manager=self.settings_manager,
            wait_interval=self.wait_interval
        )
        self.task_executor = TaskExecutor(logger=self.logger, queue_manager=self.queue_manager)
        
        # Активные обработчики очередей
        self._background_processors = {}
        
        # Статистика
        self.stats = {
            'total_submitted': 0,
            'queue_sizes': dict.fromkeys(self.queue_manager.get_available_queues(), 0)
        }
        
        # Автоматически запускаем обработчики всех очередей
        asyncio.create_task(self._start_all_queue_processors())
    
    async def submit_task(self, 
                         task_id: str, 
                         coro: Callable, 
                         queue_name: Optional[str] = None,
                         fire_and_forget: bool = False,
                         return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Публичный метод - отправляет задачу в соответствующую очередь
        """
        try:
            # Определяем целевую очередь
            target_queue = self._determine_target_queue(queue_name)
            
            # Задачи всегда принимаются в очередь
            # Ограничения применяются только при выполнении задач
            
            # Автоматически запускаем обработчик очереди
            if target_queue not in self._background_processors:
                await self._start_queue_processor(target_queue)
            
            # Получаем конфигурацию очереди
            config = self.queue_manager.get_queue_config(target_queue)
            
            # Создаем Future для отслеживания результата
            # Future создается если: не fire_and_forget ИЛИ return_future=True
            future = None
            if return_future or not fire_and_forget:
                future = asyncio.Future()
            
            # Создаем элемент задачи
            task_item = TaskItem(
                id=task_id,
                coro=coro,
                config=config,
                created_at=datetime.now(),
                future=future
            )
            
            # Добавляем в очередь
            await self.queue_manager.task_queues[target_queue].put(task_item)
            
            # Обновляем статистику
            self.stats['total_submitted'] += 1
            self.stats['queue_sizes'][target_queue] += 1

            # Если return_future - возвращаем Future для отслеживания
            if return_future:
                return future
            
            # Если fire_and_forget - сразу возвращаем успех
            if fire_and_forget:
                return {"result": "success"}
            
            # Если не fire_and_forget - ждем результат выполнения
            result = await future
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления задачи {task_id}: {e}")
            # Если return_future - создаем Future с ошибкой
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
        """Определяет целевую очередь на основе имени"""
        
        # Если указано имя очереди
        if queue_name:
            if self.queue_manager.is_queue_valid(queue_name):
                return queue_name
            else:
                self.logger.warning(f"Неизвестная очередь '{queue_name}', используем '{self.default_queue}'")
                return self.default_queue
        
        # По умолчанию - дефолтная очередь
        return self.default_queue
    
    async def _start_queue_processor(self, queue_name: str):
        """Запускает обработчик очереди в фоне (приватный метод)"""
        if queue_name in self._background_processors:
            return  # Уже запущен
        
        try:
            # Создаем фоновую задачу
            processor_task = asyncio.create_task(
                self._run_background_processor(queue_name),
                name=f"queue_processor_{queue_name}"
            )
            
            self._background_processors[queue_name] = processor_task
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска обработчика очереди {queue_name}: {e}")
    
    async def _stop_queue_processor(self, queue_name: str):
        """Останавливает обработчик очереди (приватный метод)"""
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
            self.logger.info(f"Остановлен обработчик очереди {queue_name}")
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки обработчика очереди {queue_name}: {e}")
    
    async def _run_background_processor(self, queue_name: str):
        """Обрабатывает очередь в фоне (приватный метод)"""
        queue = self.queue_manager.task_queues[queue_name]
        config = self.queue_manager.get_queue_config(queue_name)
        
        self.logger.info(f"Обработчик очереди {queue_name} запущен")
        
        while True:
            try:
                # Получаем задачу из очереди
                task_item = await queue.get()
                
                # Запускаем задачу с контролем семафора (семафор сам контролирует лимиты очереди)
                asyncio.create_task(
                    self.task_executor.execute_task_with_semaphore(task_item, self.queue_manager, queue_name)
                )
                
            except asyncio.CancelledError:
                self.logger.info(f"Обработчик очереди {queue_name} остановлен")
                break
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике очереди {queue_name}: {e}")
                # Используем настройки очереди для задержки
                await asyncio.sleep(config.retry_delay)
    
    async def _start_all_queue_processors(self):
        """Запускает обработчики всех очередей (приватный метод)"""
        for queue_name in self.queue_manager.queue_configs.keys():
            await self._start_queue_processor(queue_name)
        self.logger.info(f"Запущены обработчики для {len(self.queue_manager.queue_configs)} очередей")
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику TaskManager"""
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
        """Синхронный graceful shutdown утилиты"""
        self.logger.info("Shutdown TaskManager...")
        
        # Если нет активных процессоров, просто выходим
        if not self._background_processors:
            self.logger.info("TaskManager остановлен (нет активных процессоров)")
            return
        
        # Отменяем все фоновые задачи
        tasks_to_wait = []
        for queue_name in list(self._background_processors.keys()):
            processor_task = self._background_processors[queue_name]
            try:
                # Отменяем задачу
                processor_task.cancel()
                tasks_to_wait.append(processor_task)
            except Exception as e:
                # Логируем ошибку, но продолжаем shutdown
                self.logger.warning(f"Ошибка отмены обработчика очереди {queue_name}: {e}")
        
        # Ждем завершения всех задач с таймаутом
        async def _wait_for_shutdown():
            """Ожидание завершения всех отмененных задач"""
            if not tasks_to_wait:
                return
            
            try:
                # Проверяем, что все задачи принадлежат текущему loop
                current_loop = asyncio.get_running_loop()
                valid_tasks = []
                for task in tasks_to_wait:
                    # Проверяем, что задача принадлежит текущему loop
                    try:
                        if hasattr(task, 'get_loop') and task.get_loop() == current_loop:
                            valid_tasks.append(task)
                        elif not hasattr(task, 'get_loop'):
                            # Если нет метода get_loop, пробуем использовать задачу
                            # (может быть из того же loop, если создана в правильном контексте)
                            valid_tasks.append(task)
                    except Exception:
                        # Если не можем проверить, пропускаем задачу
                        pass
                
                if not valid_tasks:
                    # Если нет валидных задач, просто выходим
                    return
                
                # Ждем завершения всех задач с обработкой CancelledError
                # Используем asyncio.gather для ожидания всех задач одновременно
                # return_exceptions=True позволяет не прерывать ожидание при ошибках
                await asyncio.wait_for(
                    asyncio.gather(*valid_tasks, return_exceptions=True),
                    timeout=self.shutdown_timeout
                )
                self.logger.info("Все задачи успешно завершены")
            except asyncio.TimeoutError:
                self.logger.warning(f"Таймаут ожидания завершения задач ({self.shutdown_timeout} сек), принудительно завершаем")
            except Exception as e:
                # Логируем все ошибки - фильтрация задач по loop уже выполнена выше
                self.logger.warning(f"Ошибка при ожидании завершения задач: {e}")
        
        try:
            # Пытаемся дождаться завершения задач в существующем event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop запущен, используем run_coroutine_threadsafe для выполнения в правильном loop
                # Это работает даже если shutdown() вызывается из другого потока (через asyncio.to_thread)
                try:
                    future = asyncio.run_coroutine_threadsafe(_wait_for_shutdown(), loop)
                    # Ждем завершения с таймаутом (используем тот же таймаут, что и внутри _wait_for_shutdown)
                    # Если корутина завершится раньше (успешно или по таймауту), future.result() вернется сразу
                    future.result(timeout=self.shutdown_timeout)
                except concurrent.futures.TimeoutError:
                    self.logger.warning(f"Таймаут ожидания завершения задач ({self.shutdown_timeout} сек), принудительно завершаем")
                except Exception as e:
                    # Логируем все ошибки - фильтрация задач по loop уже выполнена в _wait_for_shutdown
                    self.logger.warning(f"Ошибка при ожидании завершения задач: {e}")
            else:
                # Если loop не запущен, запускаем его для shutdown с таймаутом
                try:
                    loop.run_until_complete(_wait_for_shutdown())
                except Exception as e:
                    self.logger.warning(f"Ошибка при ожидании завершения задач: {e}")
        except RuntimeError:
            # Если нет event loop, создаем новый
            try:
                asyncio.run(_wait_for_shutdown())
            except Exception as e:
                self.logger.warning(f"Ошибка при ожидании завершения задач: {e}")
        except Exception as e:
            self.logger.warning(f"Ошибка shutdown TaskManager: {e}")
        
        # Очищаем словарь процессоров
        self._background_processors.clear()
        
        self.logger.info("TaskManager остановлен")