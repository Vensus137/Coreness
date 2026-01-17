"""
Telegram Webhook Handler - обработчик вебхуков от Telegram
Валидация secret_token и обработка обновлений для ботов
"""

import json

from aiohttp import web


class TelegramWebhookHandler:
    """Обработчик вебхуков от Telegram"""
    
    def __init__(self, webhook_manager, action_hub, logger):
        self.webhook_manager = webhook_manager
        self.action_hub = action_hub
        self.logger = logger

    async def handle(self, request: web.Request) -> web.Response:
        """Обработчик Telegram вебхуков"""
        try:
            # Получаем secret_token из заголовка
            secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
            
            if not secret_token:
                return web.Response(
                    status=401,
                    text="Missing secret token"
                )
            
            # Определяем bot_id по secret_token
            bot_id = await self.webhook_manager.get_bot_id_by_secret_token(secret_token)
            
            if not bot_id:
                return web.Response(
                    status=401,
                    text="Invalid secret token"
                )
            
            # Получаем тело запроса
            try:
                payload_body = await request.read()
                payload = json.loads(payload_body.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.logger.error(f"[Bot-{bot_id}] Ошибка парсинга JSON payload: {e}")
                return web.Response(
                    status=400,
                    text="Invalid JSON"
                )
            
            # Добавляем системные данные с bot_id
            if 'system' not in payload:
                payload['system'] = {}
            
            payload['system'].update({
                'bot_id': bot_id,
                'source': 'webhook'
            })
            
            # Отправляем событие в event_processor через ActionHub
            # Используем fire_and_forget для быстрого ответа Telegram
            try:
                await self.action_hub.execute_action(
                    'process_event',
                    payload,
                    fire_and_forget=True
                )
            except Exception as e:
                self.logger.error(f"[Bot-{bot_id}] Ошибка отправки события в event_processor: {e}")
                # Все равно возвращаем 200, т.к. событие получено
                # Ошибка обработки - внутренняя проблема
            
            # Telegram требует быстрый ответ (200 OK)
            return web.Response(
                status=200,
                text="OK"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки Telegram вебхука: {e}")
            return web.Response(
                status=500,
                text="Internal server error"
            )

