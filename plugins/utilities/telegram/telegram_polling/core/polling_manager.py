"""
PollingManager - управление пулингом множественных ботов
"""

import asyncio
from typing import Any, Callable, Dict, Type


class PollingManager:
    """
    Простое управление пулингом множественных ботов без мониторинга
    """
    
    def __init__(self, settings: dict, logger, bot_poller_class: Type, datetime_formatter):
        self.settings = settings
        self.logger = logger
        self.bot_poller_class = bot_poller_class
        self.datetime_formatter = datetime_formatter
        
        # Активные пуллеры
        self.active_pollers: Dict[int, Any] = {}  # bot_id -> poller
        
        # Отслеживание ботов, для которых уже был выполнен сброс настроек
        # Это глобальная настройка бота на сервере Telegram, не нужно делать при каждом перезапуске пулинга
        self._bots_settings_reset: set[int] = set()
    
    async def start_bot_polling(self, bot_id: int, token: str, event_callback: Callable) -> bool:
        """Запуск пулинга для конкретного бота"""
        try:
            # Останавливаем существующий пулинг если есть
            if bot_id in self.active_pollers:
                await self.stop_bot_polling(bot_id)
            
            # Сбрасываем настройки бота только при первом запуске (глобальная настройка на сервере Telegram)
            # Это нужно делать один раз при старте приложения, а не при каждом перезапуске пулинга
            if bot_id not in self._bots_settings_reset:
                # Создаем временный пуллер только для сброса настроек
                temp_poller = self.bot_poller_class(bot_id, token, self.settings, self.logger, self.datetime_formatter)
                try:
                    await temp_poller.reset_bot_settings()
                    self._bots_settings_reset.add(bot_id)
                    self.logger.info(f"[Bot-{bot_id}] Настройки бота установлены (один раз при запуске)")
                except Exception as e:
                    # Если не удалось установить настройки - логируем, но продолжаем работу
                    # Возможно, настройки уже установлены или есть временная проблема
                    self.logger.warning(f"[Bot-{bot_id}] Не удалось установить настройки бота (продолжаем работу): {e}")
            
            # Создаем новый пуллер и сразу добавляем в active_pollers
            poller = self.bot_poller_class(bot_id, token, self.settings, self.logger, self.datetime_formatter)
            self.active_pollers[bot_id] = poller
            
            # Запускаем пулинг в фоновой задаче (не блокируем)
            # Пулинг будет в бесконечном цикле, если токен валиден - работает, если нет - остановится сам
            self.logger.info(f"[Bot-{bot_id}] Пулинг запущен в фоне")
            asyncio.create_task(poller.start_polling(event_callback))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска пулинга: {e}")
            return False

    async def stop_bot_polling(self, bot_id: int) -> bool:
        """Остановка пулинга для конкретного бота"""
        try:
            if bot_id not in self.active_pollers:
                return True
            
            poller = self.active_pollers[bot_id]
            
            # Останавливаем пулинг с таймаутом
            stop_timeout = self.settings.get('stop_polling_manager_timeout', 3.0)
            try:
                await asyncio.wait_for(poller.stop_polling(), timeout=stop_timeout)
            except asyncio.TimeoutError:
                self.logger.warning(f"[Bot-{bot_id}] Пулинг не остановился за {stop_timeout} секунд, принудительное удаление")
            
            # Удаляем из active_pollers ТОЛЬКО после остановки
            del self.active_pollers[bot_id]
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки пулинга: {e}")
            return False
    
    async def stop_all_polling(self) -> bool:
        """Остановка пулинга всех ботов"""
        try:
            self.logger.info("Остановка пулинга всех ботов")
            
            # Останавливаем все пуллеры
            tasks = []
            for bot_id in list(self.active_pollers.keys()):
                tasks.append(self.stop_bot_polling(bot_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.logger.info("Пулинг всех ботов остановлен")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка остановки пулинга всех ботов: {e}")
            return False
    
    def shutdown(self):
        """Синхронный graceful shutdown менеджера пулинга"""
        # Останавливаем все пуллеры синхронно
        for bot_id in list(self.active_pollers.keys()):
            try:
                if bot_id in self.active_pollers:
                    poller = self.active_pollers[bot_id]
                    # Используем синхронный метод остановки пуллера
                    poller.stop_polling_sync()
                    del self.active_pollers[bot_id]
            except Exception as e:
                self.logger.error(f"Ошибка остановки пулинга: {e}")
    
    