"""
GitHub Webhook Handler - обработчик вебхуков от GitHub
Валидация подписи и обработка событий push для синхронизации тенантов
"""

import hashlib
import hmac
import json

from aiohttp import web


class GitHubWebhookHandler:
    """Обработчик вебхуков от GitHub"""
    
    def __init__(self, action_hub, webhook_secret: str, logger):
        self.action_hub = action_hub
        self.webhook_secret = webhook_secret
        self.logger = logger

    async def handle(self, request: web.Request) -> web.Response:
        """Обработчик GitHub вебхуков"""
        try:
            # Получаем тело запроса
            payload_body = await request.read()
            
            # Получаем заголовки
            signature = request.headers.get('X-Hub-Signature-256', '')
            event_type = request.headers.get('X-GitHub-Event', '')
            
            # Валидация подписи
            if not self._verify_signature(payload_body, signature):
                self.logger.warning("Невалидная подпись GitHub вебхука")
                return web.Response(
                    status=401,
                    text="Invalid signature"
                )
            
            # Парсим JSON payload
            try:
                payload = json.loads(payload_body.decode('utf-8'))
            except json.JSONDecodeError as e:
                self.logger.error(f"Ошибка парсинга JSON payload: {e}")
                return web.Response(
                    status=400,
                    text="Invalid JSON"
                )
            
            # Обрабатываем только события push
            if event_type != 'push':
                self.logger.info(f"Игнорируем событие типа {event_type}")
                return web.Response(
                    status=200,
                    text="Event ignored"
                )
            
            # Извлекаем список измененных файлов из payload
            all_files = []
            commits = payload.get('commits', [])
            for commit in commits:
                # Собираем все измененные файлы из всех коммитов
                all_files.extend(commit.get('added', []))
                all_files.extend(commit.get('modified', []))
                all_files.extend(commit.get('removed', []))
            
            if not all_files:
                self.logger.info("Нет измененных файлов в push событии")
                return web.Response(
                    status=200,
                    text="No file changes"
                )
            
            # Вызываем универсальный метод синхронизации через ActionHub
            # Он использует существующую логику из smart_sync для парсинга
            result = await self.action_hub.execute_action(
                'sync_tenants_from_files',
                {'files': all_files},  # Передаем список путей файлов
                fire_and_forget=True  # Асинхронно, не ждем завершения
            )
            
            if result.get('result') not in ['success', 'partial_success']:
                error_obj = result.get('error', {})
                self.logger.error(
                    f"Ошибка синхронизации тенантов по вебхуку: "
                    f"{error_obj.get('message', 'Неизвестная ошибка')}"
                )
            else:
                response_data = result.get('response_data', {})
                synced = response_data.get('synced_tenants', 0)
                total = response_data.get('total_tenants', 0)
                self.logger.info(f"Синхронизировано {synced} из {total} тенантов по вебхуку")
            
            return web.Response(
                status=200,
                text="Webhook processed"
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки GitHub вебхука: {e}")
            return web.Response(
                status=500,
                text="Internal server error"
            )
            
    def _verify_signature(self, payload_body: bytes, signature: str) -> bool:
        """Валидация подписи GitHub вебхука"""
        if not self.webhook_secret:
            return False
        
        if not signature:
            return False
        
        # GitHub отправляет подпись в формате "sha256=..."
        if not signature.startswith('sha256='):
            return False
        
        # Извлекаем хеш из подписи
        received_hash = signature[7:]
        
        # Вычисляем ожидаемый хеш
        expected_hash = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        
        # Сравниваем безопасным способом
        return hmac.compare_digest(received_hash, expected_hash)

