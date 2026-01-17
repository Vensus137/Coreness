"""
Event Processor - сервис для обработки событий от пулинга
Обертка над core модулями для интеграции с ActionHub
"""

from typing import Any, Dict

from .core.event_handler import EventHandler


class EventProcessor:
    """
    Сервис для обработки событий от пулинга
    Обертка над core модулями для интеграции с ActionHub
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        
        # Создаем обработчик событий
        self.event_handler = EventHandler(
            logger=self.logger,
            action_hub=self.action_hub,
            datetime_formatter=kwargs['datetime_formatter'],
            settings_manager=self.settings_manager,
            database_manager=kwargs['database_manager'],
            user_manager=kwargs['user_manager'],
            data_converter=kwargs['data_converter'],
            cache_manager=kwargs['cache_manager']
        )
        
        # Регистрируем себя в ActionHub
        self.action_hub.register('event_processor', self)
    
    def shutdown(self):
        """Синхронный graceful shutdown сервиса"""
        self.logger.info("Останавливаем сервис...")
        # Очищаем ресурсы через event_handler
        import asyncio
        try:
            # Пытаемся очистить ресурсы в существующем event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop запущен, создаем задачу для очистки
                loop.create_task(self.event_handler.cleanup())
            else:
                # Если loop не запущен, запускаем его для очистки
                loop.run_until_complete(self.event_handler.cleanup())
        except RuntimeError:
            # Если нет event loop, создаем новый
            asyncio.run(self.event_handler.cleanup())
        except Exception as e:
            self.logger.warning(f"Ошибка очистки ресурсов: {e}")
        
        self.logger.info("Сервис остановлен")
    
    # === Actions для ActionHub ===
    
    async def process_event(self, data: dict) -> Dict[str, Any]:
        """
        Обработка события от пулинга
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Обрабатываем событие через event_handler
            await self.event_handler.handle_raw_event(data)
            
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки события: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
