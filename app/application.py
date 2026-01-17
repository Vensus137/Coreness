import asyncio
import signal
import sys
from typing import List

from plugins.utilities.foundation.logger.logger import Logger
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager

from .di_container import DIContainer

# Настройки shutdown теперь берутся из config/settings.yaml через settings_manager


class Application:
    """Основной класс приложения - управляет жизненным циклом"""
    
    def __init__(self):
        self.logger_instance = Logger()
        self.logger = self.logger_instance.get_logger("application")
        self.is_running = False
        self.plugins_manager = None
        self.settings_manager = None
        self.di_container = None
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        
        # Регистрируем сигналы СРАЗУ после создания logger
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, _):
        """Обработчик сигналов для graceful shutdown"""
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"Получен сигнал {signum}, начинаем graceful shutdown...")
        
        # Проверяем, не получали ли мы уже сигнал
        if hasattr(self, '_shutdown_requested') and self._shutdown_requested:
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.critical("Получен повторный сигнал завершения, принудительно завершаем приложение!")
                else:
                    print("[SIGNAL] Получен повторный сигнал завершения!")
            except Exception:
                print("[SIGNAL] Повторный сигнал, принудительное завершение!")
            import os
            os._exit(1)
        
        # Устанавливаем флаг запроса shutdown
        self._shutdown_requested = True
        
        # Просто устанавливаем событие shutdown
        if self.is_running:
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info("Устанавливаем shutdown event")
                else:
                    print("[SIGNAL] Устанавливаем shutdown event")
            except Exception:
                print("[SIGNAL] Установка shutdown event")
            self._shutdown_event.set()
        else:
            try:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.info("Приложение еще не запущено, игнорируем сигнал")
                else:
                    print("[SIGNAL] Приложение еще не запущено, игнорируем сигнал")
            except Exception:
                print("[SIGNAL] Приложение не запущено")
    
    async def startup(self):
        """Асинхронный запуск приложения"""
        self.logger.info("Запуск приложения...")
        self.is_running = True
        
        try:
            # 1. Создаем plugins_manager через DI-контейнер
            self.logger.info("Инициализация plugins_manager...")
            self.plugins_manager = PluginsManager(logger=self.logger_instance.get_logger("plugins_manager"))
            
            # 2. Создаем settings_manager
            self.logger.info("Инициализация settings_manager...")
            self.settings_manager = SettingsManager(
                logger=self.logger_instance.get_logger("settings_manager"),
                plugins_manager=self.plugins_manager
            )
            
            # 3. Создаем DI-контейнер с передачей plugins_manager и settings_manager
            self.logger.info("Создание DI-контейнера...")
            self.di_container = DIContainer(
                logger=self.logger_instance, 
                plugins_manager=self.plugins_manager,
                settings_manager=self.settings_manager
            )
            
            # 4. Инициализируем все плагины автоматически
            self.logger.info("Инициализация всех плагинов...")
            self.di_container.initialize_all_plugins()
            
            # 5. Запускаем все сервисы в фоновых задачах
            self.logger.info("Запуск всех сервисов...")
            await self._start_all_services()
            
            self.logger.info("Приложение запущено успешно")
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске приложения: {e}")
            await self.shutdown()
            sys.exit(1)
    
    async def _start_all_services(self):
        """Запуск сервисов по плану из SettingsManager"""
        # Получаем план запуска из DI-контейнера (уже построен)
        startup_plan = self.di_container.get_startup_plan()
        
        if not startup_plan:
            self.logger.error("DI-контейнер не смог получить план запуска")
            return
        
        enabled_services = startup_plan.get('enabled_services', [])
        
        if not enabled_services:
            self.logger.info("Включенные сервисы для запуска не найдены")
            return
        
        self.logger.info(f"Запускаем сервисы по плану: {len(enabled_services)} сервисов")
        
        for service_name in enabled_services:
            try:
                # Получаем экземпляр сервиса из DI-контейнера
                service_instance = self.di_container.get_service(service_name)
                
                if not service_instance:
                    self.logger.error(f"Не удалось получить экземпляр сервиса {service_name}")
                    continue
                
                # Проверяем, есть ли у сервиса метод run
                if hasattr(service_instance, 'run'):
                    self.logger.info(f"Запуск сервиса: {service_name}")
                    
                    # Создаем фоновую задачу
                    task = asyncio.create_task(service_instance.run(), name=service_name)
                    self._background_tasks.append(task)
                    
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
            # Получаем настройки shutdown из глобальных настроек
            global_settings = self.settings_manager.get_global_settings()
            shutdown_settings = global_settings.get('shutdown', {})
            di_container_timeout = shutdown_settings.get('di_container_timeout', 5.0)
            background_tasks_timeout = shutdown_settings.get('background_tasks_timeout', 2.0)
            
            # Вычисляем общий timeout для логирования
            total_shutdown_timeout = di_container_timeout + background_tasks_timeout
            self.logger.info(f"Начинаем shutdown с общим timeout {total_shutdown_timeout} секунд (di_container: {di_container_timeout}s, background_tasks: {background_tasks_timeout}s)...")
            
            # ШАГ 1: Shutdown всех плагинов (утилит и сервисов)
            # Плагины останавливают свои внутренние фоновые задачи (пулинг, scheduled scenarios, task processors и т.д.)
            if self.di_container:
                self.logger.info("Начинаем shutdown DI-контейнера (остановка всех плагинов)...")
                try:
                    # Создаем задачу для shutdown с таймаутом
                    shutdown_task = asyncio.create_task(
                        asyncio.to_thread(self.di_container.shutdown)
                    )
                    await asyncio.wait_for(shutdown_task, timeout=di_container_timeout)
                    self.logger.info("DI-контейнер корректно завершен, все плагины остановлены")
                except asyncio.TimeoutError:
                    self.logger.warning("Таймаут shutdown DI-контейнера, принудительно завершаем")
                    shutdown_task.cancel()
                    self.logger.info("DI-контейнер принудительно завершен")
                except Exception as e:
                    self.logger.error(f"Ошибка shutdown DI-контейнера: {e}")
                    shutdown_task.cancel()
                    self.logger.info("DI-контейнер принудительно завершен после ошибки")
            
            # ШАГ 2: Отменяем все фоновые задачи приложения (service.run() задачи)
            if self._background_tasks:
                self.logger.info(f"Отмена {len(self._background_tasks)} фоновых задач...")
                for task in self._background_tasks:
                    if not task.done():
                        task.cancel()
                
                # Ждем завершения всех задач с таймаутом
                try:
                    # Используем asyncio.wait вместо gather для корректной работы с timeout
                    done, pending = await asyncio.wait(
                        self._background_tasks,
                        timeout=background_tasks_timeout,
                        return_when=asyncio.ALL_COMPLETED
                    )
                    
                    if pending:
                        self.logger.warning(f"Таймаут ожидания завершения {len(pending)} фоновых задач, принудительно завершаем")
                        # Принудительно завершаем незавершенные задачи
                        for task in pending:
                            task.cancel()
                        self.logger.info("Все фоновые задачи принудительно завершены")
                    else:
                        self.logger.info("Все фоновые задачи завершены корректно")
                        
                except Exception as e:
                    self.logger.error(f"Ошибка при ожидании завершения задач: {e}")
                    # Принудительно завершаем все задачи
                    for task in self._background_tasks:
                        if not task.done():
                            task.cancel()
                    self.logger.info("Все фоновые задачи принудительно завершены после ошибки")
            
            self.logger.info("Приложение корректно завершено")
            
        except Exception as e:
            self.logger.error(f"Ошибка при async shutdown: {e}")
            # В крайнем случае принудительно завершаем процесс
            self.logger.critical("Критическая ошибка shutdown, принудительно завершаем процесс...")
            import os
            os._exit(1)
    
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
            self.logger.info("Приложение запущено, ожидаем события shutdown...")
            await self._shutdown_event.wait()
            self.logger.info("Получено событие shutdown!")
            
        except KeyboardInterrupt:
            self.logger.info("Получен KeyboardInterrupt")
        finally:
            await self._async_shutdown()
    
    def run_sync(self):
        """Синхронная обертка для запуска асинхронного приложения"""
        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            self.logger.info("Получен KeyboardInterrupt, завершаем приложение")
        except SystemExit:
            raise
        except Exception as e:
            self.logger.error(f"Ошибка в run_sync: {e}")
            sys.exit(1) 