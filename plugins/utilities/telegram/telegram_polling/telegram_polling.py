"""
Telegram Polling Utility - утилита для пулинга множественных Telegram ботов
"""

import asyncio
from typing import Any, Callable, Dict, List

from .core.bot_poller import BotPoller
from .core.polling_manager import PollingManager


class TelegramPollingUtility:
    """
    Утилита для пулинга множественных Telegram ботов
    Прямой HTTP API для работы с Telegram Bot API
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.datetime_formatter = kwargs['datetime_formatter']
        
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('telegram_polling')
        
        # Создаем менеджер пулинга
        self.polling_manager = PollingManager(
            self.settings, 
            self.logger, 
            BotPoller, 
            self.datetime_formatter
        )
    
    def shutdown(self):
        """Синхронный graceful shutdown утилиты"""
        self.polling_manager.shutdown()

    def _create_event_callback(self, bot_id: int, event_callback: Callable):
        """Создает внутренний callback для обработки событий с привязанным bot_id"""
        async def internal_event_callback(raw_event):
            try:
                # Добавляем системные поля (для защиты)
                if 'system' not in raw_event:
                    raw_event['system'] = {}
                raw_event['system']['bot_id'] = bot_id
                
                # Добавляем поля в плоский словарь (для использования в действиях)
                raw_event['bot_id'] = bot_id
                
                # Вызываем переданный callback
                if asyncio.iscoroutinefunction(event_callback):
                    await event_callback(raw_event)
                else:
                    event_callback(raw_event)
                
            except Exception as e:
                self.logger.error(f"Ошибка обработки события: {e}")
        
        return internal_event_callback

    # === Публичные методы для использования в сервисах ===
    
    async def start_bot_polling(self, bot_id: int, token: str) -> bool:
        """Запуск пулинга для конкретного бота (автоматически останавливает существующий)"""
        try:
            # Создаем callback для отправки событий в event_processor через ActionHub
            async def bot_event_callback(raw_event):
                try:
                    # Отправляем событие в event_processor через ActionHub (fire_and_forget для параллельности)
                    await self.action_hub.execute_action('process_event', raw_event, fire_and_forget=True)
                except Exception as e:
                    self.logger.error(f"Ошибка отправки события в event_processor: {e}")
            
            # Создаем внутренний callback для обработки событий с привязанным bot_id
            internal_callback = self._create_event_callback(bot_id, bot_event_callback)
            
            # Используем PollingManager для запуска (он автоматически остановит существующий)
            return await self.polling_manager.start_bot_polling(bot_id, token, internal_callback)
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска пулинга: {e}")
            return False
    
    async def stop_bot_polling(self, bot_id: int) -> bool:
        """Остановка пулинга для конкретного бота"""
        try:
            return await self.polling_manager.stop_bot_polling(bot_id)
        except Exception as e:
            self.logger.error(f"Ошибка остановки пулинга: {e}")
            return False
    
    def is_bot_polling(self, bot_id: int) -> bool:
        """Проверка активности пулинга для конкретного бота"""
        try:
            if bot_id not in self.polling_manager.active_pollers:
                return False
            
            poller = self.polling_manager.active_pollers[bot_id]
            return poller.is_running
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки активности пулинга: {e}")
            return False
    
    async def stop_all_polling(self) -> bool:
        """Остановка пулинга всех ботов"""
        try:
            return await self.polling_manager.stop_all_polling()
        except Exception as e:
            self.logger.error(f"Ошибка остановки пулинга всех ботов: {e}")
            return False
    
    async def start_all_polling(self, bots_list: List[Dict[str, Any]]) -> int:
        """Запуск пулинга для списка ботов"""
        try:
            started_count = 0
            
            for bot_info in bots_list:
                bot_id = bot_info.get('bot_id')
                bot_token = bot_info.get('bot_token')
                is_active = bot_info.get('is_active', False)
                
                if bot_id and bot_token and is_active:
                    success = await self.start_bot_polling(bot_id, bot_token)
                    if success:
                        started_count += 1
                        self.logger.info(f"[Bot-{bot_id}] Запуск бота успешен")
                    else:
                        self.logger.warning(f"[Bot-{bot_id}] Не удалось запустить бота")
            
            self.logger.info(f"Запуск всех ботов завершен. Запущено {started_count} ботов")
            return started_count
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска всех ботов: {e}")
            return 0
    
    
