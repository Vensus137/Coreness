import asyncio
import signal
import sys
from typing import List

from plugins.utilities.foundation.logger.logger import Logger
# Прямые импорты
from plugins.utilities.foundation.plugins_manager.plugins_manager import \
    PluginsManager

from .di_container import DIContainer


class Application:
    """Основной класс приложения - управляет жизненным циклом"""
    
    def __init__(self):
        self.logger_instance = Logger()
        self.logger = self.logger_instance.get_logger("application")
        self.is_running = False
        self.plugins_manager = None
        self.di_container = None
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Настройка обработчиков сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, _):
        """Обработчик сигналов для graceful shutdown"""
        self.logger.info(f"Получен сигнал {signum}, начинаем graceful shutdown...")
        # Устанавливаем событие shutdown в event loop
        if asyncio.get_event_loop().is_running():
            asyncio.create_task(self._async_shutdown())
        else:
            self._shutdown_event.set()
    
    async def startup(self):
        """Асинхронный запуск приложения"""
        self.logger.info("Запуск приложения...")
        self.is_running = True
        
        try:
            # 1. Создаем plugins_manager через DI-контейнер
            self.logger.info("Инициализация plugins_manager...")
            self.plugins_manager = PluginsManager(logger=self.logger_instance.get_logger("plugins_manager"))
            
            # 2. Создаем DI-контейнер с передачей plugins_manager
            self.logger.info("Создание DI-контейнера...")
            self.di_container = DIContainer(logger=self.logger_instance.get_logger("DI container"), plugins_manager=self.plugins_manager)
            
            # 3. Инициализируем все плагины автоматически
            self.logger.info("Инициализация всех плагинов...")
            self.di_container.initialize_all_plugins()
            
            # 4. Запускаем все сервисы в фоновых задачах
            self.logger.info("Запуск всех сервисов...")
            await self._start_all_services()
            
            self.logger.info("Приложение запущено успешно")
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске приложения: {e}")
            await self.shutdown()
            sys.exit(1)
    
    async def _start_all_services(self):
        """Запуск всех сервисов в фоновых задачах"""
        services = self.di_container.get_all_services()
        
        if not services:
            self.logger.info("Сервисы для запуска не найдены")
            return
        
        self.logger.info(f"Найдено сервисов для запуска: {len(services)}")
        
        for service_name, service_instance in services.items():
            try:
                # Проверяем, есть ли у сервиса метод run
                if hasattr(service_instance, 'run'):
                    self.logger.info(f"Запуск сервиса: {service_name}")
                    
                    # Создаем фоновую задачу
                    task = asyncio.create_task(service_instance.run(), name=service_name)
                    self._background_tasks.append(task)
                    
                    self.logger.debug(f"Сервис {service_name} запущен в фоновой задаче")
                else:
                    self.logger.warning(f"Сервис {service_name} не имеет метода run()")
                    
            except Exception as e:
                self.logger.error(f"Ошибка запуска сервиса {service_name}: {e}")
        
        self.logger.info(f"Запущено фоновых задач: {len(self._background_tasks)}")
    
    async def _async_shutdown(self):
        """Асинхронный graceful shutdown"""
        if not self.is_running:
            return
            
        self.logger.info("Начинаем async shutdown приложения...")
        self.is_running = False
        self._shutdown_event.set()
        
        try:
            # Отменяем все фоновые задачи
            if self._background_tasks:
                self.logger.info(f"Отмена {len(self._background_tasks)} фоновых задач...")
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                        self.logger.debug(f"Задача {task.get_name()} отменена")
                
                # Ждем завершения всех задач
                await asyncio.gather(*self._background_tasks, return_exceptions=True)
            
            # Shutdown DI-контейнера
            if self.di_container:
                self.di_container.shutdown()
            
            self.logger.info("Приложение корректно завершено")
            
        except Exception as e:
            self.logger.error(f"Ошибка при async shutdown: {e}")
    
    def shutdown(self):
        """Синхронный shutdown для обратной совместимости"""
        if not self.is_running:
            return
            
        self.logger.info("Начинаем shutdown приложения...")
        self.is_running = False
        
        try:
            # Отменяем все фоновые задачи
            if self._background_tasks:
                self.logger.info(f"Отмена {len(self._background_tasks)} фоновых задач...")
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                        self.logger.debug(f"Задача {task.get_name()} отменена")
            
            # Shutdown DI-контейнера
            if self.di_container:
                self.di_container.shutdown()
            
            self.logger.info("Приложение корректно завершено")
            
        except Exception as e:
            self.logger.error(f"Ошибка при shutdown: {e}")
    
    async def run(self):
        """Асинхронный основной цикл приложения"""
        await self.startup()
        
        try:
            # Ждем события shutdown или завершения всех сервисов
            await self._shutdown_event.wait()
            
        except KeyboardInterrupt:
            self.logger.info("Получен KeyboardInterrupt")
        finally:
            await self._async_shutdown()
    
    def run_sync(self):
        """Синхронная обертка для запуска асинхронного приложения"""
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            self.logger.info("Получен KeyboardInterrupt в run_sync")
        except Exception as e:
            self.logger.error(f"Ошибка в run_sync: {e}")
            sys.exit(1) 