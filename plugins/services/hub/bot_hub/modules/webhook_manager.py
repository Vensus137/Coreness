"""
WebhookManager - подмодуль для управления вебхуками Telegram ботов
Установка/удаление вебхуков через Telegram Bot API
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional

import aiohttp


class WebhookManager:
    """
    Менеджер вебхуков для Telegram ботов
    Управляет установкой и удалением вебхуков через Telegram Bot API
    """
    
    def __init__(self, cache_manager, logger, settings_manager, http_server):
        self.cache_manager = cache_manager
        self.logger = logger
        self.http_server = http_server
        
        # Получаем настройки из bot_hub
        bot_hub_settings = settings_manager.get_plugin_settings("bot_hub")
        self.cache_ttl = bot_hub_settings.get('cache_ttl', 315360000)  # Вечный кэш
        self.webhook_endpoint = bot_hub_settings.get('webhook_endpoint', '/webhooks/telegram')
        
        # Получаем allowed_updates из telegram_polling (унификация настроек)
        telegram_polling_settings = settings_manager.get_plugin_settings("telegram_polling")
        self.allowed_updates = telegram_polling_settings.get('allowed_updates', ['message', 'callback_query', 'pre_checkout_query'])
        
        # Время запуска системы для генерации уникальных secret_token
        self.startup_timestamp = str(int(time.time()))
    
    def _get_webhook_secret_cache_key(self, secret_token: str) -> str:
        """Генерация ключа кэша для secret_token"""
        return f"webhook_secret:{secret_token}"
    
    def _generate_secret_token(self, bot_id: int) -> str:
        """
        Генерация secret_token для вебхука
        Формат: MD5(bot_id:startup_timestamp)
        """
        seed = f"{bot_id}:{self.startup_timestamp}"
        return hashlib.md5(seed.encode('utf-8')).hexdigest()
    
    async def _save_secret_token(self, secret_token: str, bot_id: int):
        """Сохранение маппинга secret_token -> bot_id в кэш"""
        cache_key = self._get_webhook_secret_cache_key(secret_token)
        await self.cache_manager.set(cache_key, bot_id, ttl=self.cache_ttl)
    
    async def get_bot_id_by_secret_token(self, secret_token: str) -> Optional[int]:
        """
        Получение bot_id по secret_token из кэша
        """
        cache_key = self._get_webhook_secret_cache_key(secret_token)
        bot_id = await self.cache_manager.get(cache_key)
        return bot_id
    
    async def set_webhook(self, bot_id: int, bot_token: str) -> Dict[str, Any]:
        """
        Установка вебхука для бота через Telegram Bot API
        """
        try:
            # Проверяем наличие http_server (для безопасности, хотя он обязателен)
            if not self.http_server:
                return {
                    "result": "error",
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "http_server не найден. Убедитесь, что http_server включен в зависимостях"
                    }
                }
            
            # Получаем URL вебхука от http_server
            webhook_url = self.http_server.get_webhook_url(self.webhook_endpoint)
            if not webhook_url:
                return {
                    "result": "error",
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "external_url не настроен в http_server. Укажите внешний URL сервера в настройках http_server"
                    }
                }
            
            # Генерируем secret_token
            secret_token = self._generate_secret_token(bot_id)
            
            # Сохраняем маппинг в кэш
            await self._save_secret_token(secret_token, bot_id)
            
            # Вызываем Telegram Bot API для установки вебхука
            api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
            
            # Всегда используем самоподписанный сертификат (генерируется в http_server при инициализации)
            cert_result = self.http_server.get_certificate()
            if not cert_result:
                return {
                    "result": "error",
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "Ошибка генерации SSL-сертификата. Проверьте настройку external_url в http_server"
                    }
                }
            cert_pem, _ = cert_result
            
            # Telegram API требует multipart/form-data для загрузки сертификата
            form_data = aiohttp.FormData()
            form_data.add_field('url', webhook_url)
            form_data.add_field('secret_token', secret_token)
            # allowed_updates передаем как JSON массив (Telegram API принимает JSON строку)
            form_data.add_field('allowed_updates', json.dumps(self.allowed_updates))
            # certificate передаем как файл
            form_data.add_field('certificate', cert_pem, filename='cert.pem', content_type='application/x-pem-file')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=form_data) as response:
                    data = await response.json()
                
                if data.get('ok'):
                    self.logger.info(f"[Bot-{bot_id}] Вебхук установлен: {webhook_url}")
                    return {
                        "result": "success",
                        "response_data": {
                            "webhook_url": webhook_url,
                            "secret_token": secret_token
                        }
                    }
                else:
                    error_description = data.get('description', 'Неизвестная ошибка')
                    error_code = data.get('error_code', 0)
                    
                    # Обработка конфликта вебхука (409)
                    if error_code == 409:
                        self.logger.warning(f"[Bot-{bot_id}] Конфликт вебхука, пытаемся удалить старый...")
                        # Пытаемся удалить старый вебхук и установить новый
                        delete_result = await self.delete_webhook(bot_token, bot_id)
                        if delete_result.get('result') == 'success':
                            # Повторная попытка установки
                            async with session.post(api_url, data=form_data) as retry_response:
                                retry_data = await retry_response.json()
                            
                            if retry_data.get('ok'):
                                self.logger.info(f"[Bot-{bot_id}] Вебхук установлен после удаления старого")
                                return {
                                    "result": "success",
                                    "response_data": {
                                        "webhook_url": webhook_url,
                                        "secret_token": secret_token
                                    }
                                }
                    
                    self.logger.error(f"[Bot-{bot_id}] Ошибка установки вебхука: {error_description}")
                    return {
                        "result": "error",
                        "error": {
                            "code": "API_ERROR",
                            "message": f"Ошибка Telegram API: {error_description}",
                            "telegram_error_code": error_code
                        }
                    }
                        
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка установки вебхука: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_webhook_info(self, bot_token: str, bot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получение информации о вебхуке через Telegram Bot API getWebhookInfo
        Возвращает True если вебхук установлен и URL совпадает с нашим
        """
        try:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            
            api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    data = await response.json()
                    
                    if data.get('ok'):
                        webhook_info = data.get('result', {})
                        webhook_url = webhook_info.get('url', '')
                        
                        # Проверяем, установлен ли вебхук (URL не пустой)
                        is_webhook_active = bool(webhook_url)
                        
                        # Если вебхук установлен, проверяем что URL совпадает с нашим
                        if is_webhook_active:
                            expected_url = self.http_server.get_webhook_url(self.webhook_endpoint)
                            if expected_url and webhook_url != expected_url:
                                # Вебхук установлен, но на другой URL - считаем неактивным
                                self.logger.warning(f"{log_prefix} Вебхук установлен на другой URL: {webhook_url} (ожидается: {expected_url})")
                                is_webhook_active = False
                        
                        return {
                            "result": "success",
                            "response_data": {
                                "is_webhook_active": is_webhook_active,
                                "webhook_url": webhook_url
                            }
                        }
                    else:
                        error_description = data.get('description', 'Неизвестная ошибка')
                        self.logger.warning(f"{log_prefix} Ошибка получения информации о вебхуке: {error_description}")
                        # При ошибке считаем вебхук неактивным
                        return {
                            "result": "success",
                            "response_data": {
                                "is_webhook_active": False,
                                "webhook_url": ""
                            }
                        }
                        
        except Exception as e:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            self.logger.error(f"{log_prefix} Ошибка получения информации о вебхуке: {e}")
            # При исключении считаем вебхук неактивным
            return {
                "result": "success",
                "response_data": {
                    "is_webhook_active": False,
                    "webhook_url": ""
                }
            }
    
    async def delete_webhook(self, bot_token: str, bot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Удаление вебхука для бота через Telegram Bot API
        """
        try:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            
            api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
            
            # Telegram рекомендует использовать drop_pending_updates=false
            # чтобы сохранить накопленные обновления для пулинга
            payload = {
                "drop_pending_updates": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('ok'):
                        self.logger.info(f"{log_prefix} Вебхук удален")
                        return {"result": "success"}
                    else:
                        error_description = data.get('description', 'Неизвестная ошибка')
                        self.logger.warning(f"{log_prefix} Предупреждение при удалении вебхука: {error_description}")
                        # Не считаем это ошибкой, т.к. вебхук может быть уже удален
                        return {"result": "success"}
                        
        except Exception as e:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            self.logger.error(f"{log_prefix} Ошибка удаления вебхука: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }

