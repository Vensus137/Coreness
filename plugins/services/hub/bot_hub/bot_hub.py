"""
Bot Hub Service - центральный сервис для управления всеми ботами
"""

from typing import Any, Dict

from .actions.bot_actions import BotActions
from .actions.message_actions import MessageActions
from .modules.bot_info_manager import BotInfoManager
from .modules.webhook_manager import WebhookManager


class BotHubService:
    """
    Центральный сервис для управления всеми ботами
    Интегрирует различные утилиты для полного управления ботами
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.telegram_polling = kwargs['telegram_polling']
        self.telegram_api = kwargs['telegram_api']
        self.database_manager = kwargs['database_manager']
        self.http_server = kwargs.get('http_server')
        self.cache_manager = kwargs['cache_manager']
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('bot_hub')
        
        # Регистрируем себя в ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('bot_hub', self)
        
        # Инициализируем подмодули
        self.webhook_manager = WebhookManager(self.cache_manager, self.logger, self.settings_manager, self.http_server)
        self.bot_info_manager = BotInfoManager(self.database_manager, self.action_hub, self.telegram_api, self.telegram_polling, self.logger, self.cache_manager, self.settings_manager, self.webhook_manager)
        
        # Инициализируем действия
        self.bot_actions = BotActions(self.bot_info_manager, self.telegram_polling, self.telegram_api, self.webhook_manager, self.settings_manager, self.logger)
        self.message_actions = MessageActions(self.bot_info_manager, self.telegram_api, self.logger, self.settings)
        
        # Регистрируем эндпоинт для вебхуков (если включены и доступны)
        # Флаг use_webhooks автоматически переключается в BotActions при инициализации
        use_webhooks_setting = self.settings.get('use_webhooks', False)
        
        if use_webhooks_setting and self.http_server:
            self._register_telegram_webhook_endpoint()
            # SSL сертификат автоматически генерируется при инициализации http_server, если external_url задан
        
        # Состояние сервиса
        self.is_running = False
    
    async def run(self):
        """Основной цикл работы сервиса"""
        try:
            self.is_running = True
            self.logger.info("Запущен")
            
            # Загружаем кэш всех ботов при запуске
            await self.bot_info_manager.load_all_bots_cache()
            
            # Пулинг запускается через Tenant Hub при синхронизации
            
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле: {e}")
        finally:
            self.is_running = False
    
    # === Actions для ActionHub ===
    
    async def start_bot(self, data: dict) -> Dict[str, Any]:
        """Запуск бота"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_actions.start_bot(data)
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def stop_bot(self, data: dict) -> Dict[str, Any]:
        """Остановка бота"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_actions.stop_bot(data)
        except Exception as e:
            self.logger.error(f"Ошибка остановки бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def stop_all_bots(self, data: dict) -> Dict[str, Any]:
        """Остановка всех ботов"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_actions.stop_all_bots(data)
        except Exception as e:
            self.logger.error(f"Ошибка остановки всех ботов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_bot_config(self, data: dict) -> Dict[str, Any]:
        """Синхронизация конфигурации бота: создание/обновление бота + запуск пулинга"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_actions.sync_bot_config(data)
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации конфигурации бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_bot_commands(self, data: dict) -> Dict[str, Any]:
        """Синхронизация команд бота"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_actions.sync_bot_commands(data)
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Ошибка синхронизации команд бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def set_bot_token(self, data: dict) -> Dict[str, Any]:
        """Установка токена бота через мастер-бота"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_actions.set_bot_token(data)
        except Exception as e:
            self.logger.error(f"Ошибка установки токена бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_bot(self, data: dict) -> Dict[str, Any]:
        """
        Синхронизация бота: конфигурация + команды (обертка над sync_bot_config + sync_bot_commands)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # 1. Синхронизация конфигурации бота
            sync_config_result = await self.sync_bot_config(data)
            if sync_config_result.get('result') != 'success':
                return sync_config_result
            
            bot_id = sync_config_result.get('response_data', {}).get('bot_id')
            
            # 2. Если есть команды, синхронизируем их
            if data.get('bot_commands'):
                sync_commands_result = await self.sync_bot_commands({
                    'bot_id': bot_id,
                    'command_list': data.get('bot_commands', [])
                })
                
                if sync_commands_result.get('result') != 'success':
                    error_msg = sync_commands_result.get('error', 'Неизвестная ошибка')
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Неизвестная ошибка')
                    self.logger.warning(f"[Bot-{bot_id}] Ошибка синхронизации команд: {error_msg}")
                    # Не возвращаем ошибку, т.к. конфигурация уже обновлена
            
            return sync_config_result
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def send_message(self, data: dict) -> Dict[str, Any]:
        """Отправка сообщения боту"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.message_actions.send_message(data)
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def delete_message(self, data: dict) -> Dict[str, Any]:
        """Удаление сообщения бота"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.message_actions.delete_message(data)
        except Exception as e:
            self.logger.error(f"Ошибка удаления сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def build_keyboard(self, data: dict) -> Dict[str, Any]:
        """Построение клавиатуры из массива ID с использованием шаблонов"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.message_actions.build_keyboard(data)
        except Exception as e:
            self.logger.error(f"Ошибка построения клавиатуры: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def answer_callback_query(self, data: dict) -> Dict[str, Any]:
        """Ответ на callback query (всплывающее уведомление или простое уведомление)"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.message_actions.answer_callback_query(data)
        except Exception as e:
            self.logger.error(f"Ошибка ответа на callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_telegram_bot_info(self, data: dict) -> Dict[str, Any]:
        """Получение информации о боте через Telegram API (с кэшированием)"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            bot_token = data.get('bot_token', 'unknown')
            return await self.bot_info_manager.get_telegram_bot_info_by_token(bot_token)
        except Exception as e:
            bot_token = data.get('bot_token', '')
            # Форматируем токен для логов: первые 15 символов
            if bot_token:
                token_info = f"[Bot-Token: {bot_token[:15]}...]"
            else:
                token_info = "[Bot-Token: unknown]"
            self.logger.error(f"{token_info} Ошибка получения информации о боте: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_bot_status(self, data: dict) -> Dict[str, Any]:
        """Получение статуса пулинга бота"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.bot_info_manager.get_bot_status(data)
        except Exception as e:
            self.logger.error(f"Ошибка получения статуса бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_bot_info(self, data: dict) -> Dict[str, Any]:
        """Получение информации о боте из базы данных (с кэшированием)"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            bot_id = data.get('bot_id')
            force_refresh = data.get('force_refresh', False)
            
            # Получаем информацию о боте из БД (с кэшированием)
            # BotInfoManager.get_bot_info() уже возвращает универсальную структуру
            return await self.bot_info_manager.get_bot_info(bot_id, force_refresh)
            
        except Exception as e:
            bot_id = data.get('bot_id', 'unknown')
            self.logger.error(f"[Bot-{bot_id}] Ошибка получения информации о боте: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    # === Методы управления вебхуками ===
    
    def _register_telegram_webhook_endpoint(self):
        """Регистрация эндпоинта для Telegram вебхука (вызывается при инициализации)"""
        try:
            from .handlers.telegram_webhook import TelegramWebhookHandler
            
            if not self.http_server:
                self.logger.error("http_server не найден, не удалось зарегистрировать эндпоинт Telegram вебхука")
                return
            
            # Получаем путь эндпоинта из настроек
            webhook_endpoint = self.settings.get('webhook_endpoint', '/webhooks/telegram')
            
            # Создаем обработчик
            handler_instance = TelegramWebhookHandler(
                self.webhook_manager,
                self.action_hub,
                self.logger
            )
            
            # Регистрируем эндпоинт (синхронно, при инициализации)
            success = self.http_server.register_endpoint(
                'POST',
                webhook_endpoint,
                handler_instance.handle
            )
            
            if success:
                self.logger.info(f"Эндпоинт Telegram вебхука зарегистрирован на {webhook_endpoint}")
            else:
                self.logger.error(f"Не удалось зарегистрировать эндпоинт Telegram вебхука на {webhook_endpoint}")
                
        except Exception as e:
            self.logger.error(f"Ошибка регистрации эндпоинта Telegram вебхука: {e}")
    
