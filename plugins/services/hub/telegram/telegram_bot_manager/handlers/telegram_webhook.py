"""
Telegram Webhook Handler - handler for Telegram webhooks
Secret token validation and update processing for bots
"""

import json

from aiohttp import web


class TelegramWebhookHandler:
    """Handler for Telegram webhooks"""
    
    def __init__(self, webhook_manager, action_hub, logger):
        self.webhook_manager = webhook_manager
        self.action_hub = action_hub
        self.logger = logger

    async def handle(self, request: web.Request) -> web.Response:
        """Telegram webhook handler"""
        try:
            # Get secret_token from header
            secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
            
            if not secret_token:
                return web.Response(
                    status=401,
                    text="Missing secret token"
                )
            
            # Determine bot_id by secret_token
            bot_id = await self.webhook_manager.get_bot_id_by_secret_token(secret_token)
            
            if not bot_id:
                return web.Response(
                    status=401,
                    text="Invalid secret token"
                )
            
            # Get request body
            try:
                payload_body = await request.read()
                payload = json.loads(payload_body.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.logger.error(f"[Bot-{bot_id}] Error parsing JSON payload: {e}")
                return web.Response(
                    status=400,
                    text="Invalid JSON"
                )
            
            # Add system data with bot_id
            if 'system' not in payload:
                payload['system'] = {}
            
            payload['system'].update({
                'bot_id': bot_id,
                'source': 'webhook'
            })
            
            # Send event to event_processor through ActionHub
            # Use fire_and_forget for fast Telegram response
            try:
                await self.action_hub.execute_action(
                    'process_event',
                    payload,
                    fire_and_forget=True
                )
            except Exception as e:
                self.logger.error(f"[Bot-{bot_id}] Error sending event to event_processor: {e}")
                # Still return 200, as event received
                # Processing error - internal issue
            
            # Telegram requires fast response (200 OK)
            return web.Response(
                status=200,
                text="OK"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing Telegram webhook: {e}")
            return web.Response(
                status=500,
                text="Internal server error"
            )

