"""
Core модуль для обработки событий от Telegram пулинга
Содержит основную логику обработки и пересылки событий
"""

from typing import Any, Dict


class EventHandler:
    """
    Основной обработчик событий от Telegram пулинга
    - Парсинг raw событий в стандартный формат
    - Обработка медиагрупп (объединение событий)
    - Передача обработанных событий дальше
    """
    
    def __init__(self, logger, action_hub, datetime_formatter, settings_manager, database_manager, user_manager, data_converter, cache_manager):
        self.logger = logger
        self.action_hub = action_hub
        self.datetime_formatter = datetime_formatter
        self.settings_manager = settings_manager
        
        # Получаем настройки фильтрации по времени
        settings = self.settings_manager.get_plugin_settings('event_processor')
        self.enable_time_comparison = settings.get('enable_time_comparison', False)
        self.startup_time_offset = settings.get('startup_time_offset', 0)
        
        # Инициализируем утилиты
        from ..utils.event_parser import EventParser
        from ..utils.media_group_processor import MediaGroupProcessor
        
        self.event_parser = EventParser(
            logger=self.logger,
            datetime_formatter=self.datetime_formatter,
            data_converter=data_converter,
            database_manager=database_manager,
            user_manager=user_manager,
            cache_manager=cache_manager
        )
        self.media_group_processor = MediaGroupProcessor(
            logger=self.logger,
            settings_manager=self.settings_manager
        )
    
    async def handle_raw_event(self, raw_event: Dict[str, Any]) -> None:
        """
        Обработка raw события от пулинга
        Вызывается из telegram_polling_service через event_callback
        """
        try:
            # Парсим событие в стандартный формат
            parsed_event = await self.event_parser.parse_event(raw_event)
            
            if not parsed_event:
                # Событие не было распознано или произошла ошибка парсинга
                return
            
            # Фильтрация по времени относительно запуска пуллинга
            if await self._should_ignore_event_by_time(parsed_event, raw_event):
                return
            
            # Обрабатываем медиагруппы (если есть)
            await self.media_group_processor.process_event(
                parsed_event, 
                self._forward_processed_event
            )
                    
        except Exception as e:
            self.logger.error(f"Ошибка обработки raw события: {e}")
    
    async def _forward_processed_event(self, processed_event: Dict[str, Any]) -> None:
        """
        Передача обработанного события в scenario_processor через ActionHub
        """
        try:
            # Отправляем событие в scenario_processor для обработки по сценариям
            await self.action_hub.execute_action(
                'process_scenario_event',
                processed_event
            )
                
        except Exception as e:
            self.logger.error(f"Ошибка передачи обработанного события в scenario_processor: {e}")
    
    async def _should_ignore_event_by_time(self, parsed_event: dict, raw_event: dict) -> bool:
        """
        Определяет нужно ли игнорировать событие по времени
        """
        # Если сравнение времени отключено, не игнорируем события
        if not self.enable_time_comparison:
            return False
        
        try:
            # Получаем время запуска пуллинга из системных данных raw_event
            polling_start_time = raw_event.get('system', {}).get('polling_start_time')
            if not polling_start_time:
                # Если нет времени запуска, не фильтруем
                return False
            
            # Получаем время события из parsed_event (уже в локальном времени)
            event_date = parsed_event.get('event_date')
            if not event_date:
                # Если нет времени события, не фильтруем
                return False
            
            # Вычисляем разность времени между запуском пуллинга и событием
            time_diff = await self.datetime_formatter.time_diff(event_date, polling_start_time)
            time_diff_seconds = time_diff.total_seconds()
            
            # Игнорируем события если разность больше startup_time_offset
            return time_diff_seconds > self.startup_time_offset
                
        except Exception as e:
            self.logger.warning(f"Ошибка проверки времени события: {e}")
            return False
    
    async def cleanup(self) -> None:
        """
        Очистка ресурсов
        """
        try:
            await self.media_group_processor.cleanup()
        except Exception as e:
            self.logger.error(f"Ошибка очистки: {e}")
