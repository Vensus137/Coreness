"""
TelegramAPI - утилита для работы с Telegram Bot API
"""

import asyncio
from typing import Any, Dict, List, Optional

import aiohttp


class TelegramAPI:
    """Утилита для работы с Telegram Bot API"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Настройки
        settings = self.settings_manager.get_plugin_settings("telegram_api")
        self.request_timeout = settings.get('request_timeout', 30)
        self.connection_pool_limit = settings.get('connection_pool_limit', 100)
        self.connection_pool_limit_per_host = settings.get('connection_pool_limit_per_host', 50)
        self.dns_cache_ttl = settings.get('dns_cache_ttl', 300)
        self.keepalive_timeout = settings.get('keepalive_timeout', 30)
        self.connect_timeout = settings.get('connect_timeout', 10)
        self.sock_read_timeout = settings.get('sock_read_timeout', 30)
        
        # Получаем shutdown_timeout из глобальных настроек
        global_settings = self.settings_manager.get_global_settings()
        shutdown_settings = global_settings.get('shutdown', {})
        self.shutdown_timeout = shutdown_settings.get('plugin_timeout', 3.0)
        
        # HTTP клиент
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Компоненты
        from .actions.bot_info_action import BotInfoAction
        from .actions.callback_action import CallbackAction
        from .actions.command_action import CommandAction
        from .actions.invoice_action import InvoiceAction
        from .actions.message_action import MessageAction
        from .core.api_client import APIClient
        from .core.rate_limiter import RateLimiter
        from .utils.attachment_handler import AttachmentHandler
        from .utils.button_mapper import ButtonMapper
        
        # Инициализируем сервис сразу
        self._initialize_service()
        
        # Создаем компоненты после инициализации
        self.rate_limiter = RateLimiter(settings, **kwargs)
        self.api_client = APIClient(self.session, self.rate_limiter, **kwargs)
        
        # Создаем утилиты
        self.button_mapper = ButtonMapper(**kwargs)
        self.attachment_handler = AttachmentHandler(api_client=self.api_client, **kwargs)
        
        # Создаем actions
        self.command_action = CommandAction(self.api_client, **kwargs)
        self.message_action = MessageAction(
            api_client=self.api_client,
            button_mapper=self.button_mapper,
            attachment_handler=self.attachment_handler,
            **kwargs
        )
        self.bot_info_action = BotInfoAction(self.api_client, **kwargs)
        self.invoice_action = InvoiceAction(self.api_client, **kwargs)
        self.callback_action = CallbackAction(self.api_client, **kwargs)
    
    def _initialize_service(self):
        """Приватная инициализация сервиса"""
        try:
            # Создаем HTTP сессию с оптимизированным пулом соединений
            connector = aiohttp.TCPConnector(
                limit=self.connection_pool_limit,              # Общий лимит соединений
                limit_per_host=self.connection_pool_limit_per_host,  # Лимит на api.telegram.org
                ttl_dns_cache=self.dns_cache_ttl,              # Кэш DNS
                use_dns_cache=True,                            # Включить DNS кэш
                keepalive_timeout=self.keepalive_timeout,       # Keep-alive таймаут
                enable_cleanup_closed=True                     # Автоочистка закрытых соединений
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(
                    total=self.request_timeout,
                    connect=self.connect_timeout,
                    sock_read=self.sock_read_timeout
                ),
                headers={
                    'User-Agent': 'TelegramAPI/1.0',
                    'Connection': 'keep-alive'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации: {e}")
            # Закрываем сессию если она была создана
            if hasattr(self, 'session') and self.session:
                # Закрываем сессию синхронно
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.session.close())
                    else:
                        loop.run_until_complete(self.session.close())
                except Exception:
                    pass  # Игнорируем ошибки при закрытии в случае ошибки инициализации
            raise
    
    def cleanup(self):
        """Синхронная очистка ресурсов"""
        try:
            if self.session:
                # Закрываем сессию синхронно
                import asyncio
                try:
                    # Пытаемся закрыть сессию в существующем event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Если loop запущен, создаем задачу для закрытия
                        loop.create_task(self.session.close())
                    else:
                        # Если loop не запущен, запускаем его для закрытия
                        loop.run_until_complete(self.session.close())
                except RuntimeError:
                    # Если нет event loop, создаем новый
                    asyncio.run(self.session.close())
                except Exception as e:
                    self.logger.warning(f"Ошибка закрытия сессии: {e}")
                
                self.session = None

            self.rate_limiter.cleanup()

            self.logger.info("TelegramAPI утилита очищена")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка очистки: {e}")
            return False
    
    def shutdown(self):
        """Синхронный graceful shutdown утилиты"""
        if not self.session or self.session.closed:
            return


        async def _close():
            try:
                await asyncio.wait_for(self.session.close(), timeout=self.shutdown_timeout)
            except asyncio.TimeoutError:
                # В случае таймаута закрываем коннектор принудительно
                if hasattr(self.session, '_connector'):
                    self.session._connector.close()
            except Exception:
                # На всякий случай закрываем коннектор при любых неожиданных ошибках
                if hasattr(self.session, '_connector'):
                    self.session._connector.close()

        try:
            # Если event loop уже запущен (pytest-asyncio, продовый рантайм) —
            # просто ставим задачу на закрытие в существующий цикл
            loop = asyncio.get_running_loop()
            loop.create_task(_close())
        except RuntimeError:
            # Нет активного цикла — можно безопасно заблокироваться
            asyncio.run(_close())

        self.session = None

    # === Методы для работы с командами ===
    
    async def sync_bot_commands(self, bot_token: str, bot_id: int, command_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Синхронизация команд бота: применение команд в Telegram"""
        try:
            # Делегируем выполнение в command_action
            result = await self.command_action.sync_bot_commands(bot_token, bot_id, command_list)
            
            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка синхронизации команд: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Методы для работы с информацией о боте ===
    
    def _format_token_for_logs(self, bot_token: str) -> str:
        """
        Форматирование токена для логов: первые 15 символов
        Формат токена: {bot_id}:{secret}, где bot_id можно извлечь из начала
        """
        if not bot_token:
            return "[Bot-Token: unknown]"
        
        # Берем первые 15 символов (обычно это bot_id + часть секрета)
        return f"[Bot-Token: {bot_token[:15]}...]"
    
    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """Получение информации о боте через Telegram API"""
        try:
            # Делегируем выполнение в bot_info_action
            result = await self.bot_info_action.get_bot_info(bot_token)
            
            return result
            
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Ошибка получения информации о боте: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Методы для работы с сообщениями ===
    
    async def send_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Отправка сообщения через API"""
        try:
            # Делегируем выполнение в message_action
            result = await self.message_action.send_message(bot_token, bot_id, data)

            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка отправки сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

    async def delete_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Удаление сообщения через API"""
        try:
            # Делегируем выполнение в message_action
            result = await self.message_action.delete_message(bot_token, bot_id, data)

            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка удаления сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Методы для работы с callback query ===
    
    async def answer_callback_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Ответ на callback query через API"""
        try:
            # Делегируем выполнение в callback_action
            result = await self.callback_action.answer_callback_query(bot_token, bot_id, data)

            return result

        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка ответа на callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Методы для работы с инвойсами ===
    
    async def send_invoice(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Отправка инвойса через API"""
        try:
            # Делегируем выполнение в invoice_action
            result = await self.invoice_action.send_invoice(bot_token, bot_id, data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка отправки инвойса: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def create_invoice_link(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Создание ссылки на инвойс через API"""
        try:
            # Делегируем выполнение в invoice_action
            result = await self.invoice_action.create_invoice_link(bot_token, bot_id, data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка создания ссылки на инвойс: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def answer_pre_checkout_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Ответ на запрос подтверждения оплаты через API"""
        try:
            # Делегируем выполнение в invoice_action
            result = await self.invoice_action.answer_pre_checkout_query(bot_token, bot_id, data)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка ответа на pre_checkout_query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    
