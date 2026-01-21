"""
WebhookManager - submodule for managing Telegram bot webhooks
Set/delete webhooks through Telegram Bot API
"""

import hashlib
import json
import time
from typing import Any, Dict, Optional

import aiohttp


class WebhookManager:
    """
    Webhook manager for Telegram bots
    Manages webhook setup and deletion through Telegram Bot API
    """
    
    def __init__(self, cache_manager, logger, settings_manager, http_server):
        self.cache_manager = cache_manager
        self.logger = logger
        self.http_server = http_server
        
        # Get settings from bot_hub
        bot_hub_settings = settings_manager.get_plugin_settings("bot_hub")
        self.cache_ttl = bot_hub_settings.get('cache_ttl', 315360000)  # Eternal cache
        self.webhook_endpoint = bot_hub_settings.get('webhook_endpoint', '/webhooks/telegram')
        
        # Get allowed_updates from telegram_polling (settings unification)
        telegram_polling_settings = settings_manager.get_plugin_settings("telegram_polling")
        self.allowed_updates = telegram_polling_settings.get('allowed_updates', ['message', 'callback_query', 'pre_checkout_query'])
        
        # System startup time for generating unique secret_tokens
        self.startup_timestamp = str(int(time.time()))
    
    def _get_webhook_secret_cache_key(self, secret_token: str) -> str:
        """Generate cache key for secret_token"""
        return f"webhook_secret:{secret_token}"
    
    def _generate_secret_token(self, bot_id: int) -> str:
        """
        Generate secret_token for webhook
        Format: MD5(bot_id:startup_timestamp)
        """
        seed = f"{bot_id}:{self.startup_timestamp}"
        return hashlib.md5(seed.encode('utf-8')).hexdigest()
    
    async def _save_secret_token(self, secret_token: str, bot_id: int):
        """Save mapping secret_token -> bot_id to cache"""
        cache_key = self._get_webhook_secret_cache_key(secret_token)
        await self.cache_manager.set(cache_key, bot_id, ttl=self.cache_ttl)
    
    async def get_bot_id_by_secret_token(self, secret_token: str) -> Optional[int]:
        """
        Get bot_id by secret_token from cache
        """
        cache_key = self._get_webhook_secret_cache_key(secret_token)
        bot_id = await self.cache_manager.get(cache_key)
        return bot_id
    
    async def set_webhook(self, bot_id: int, bot_token: str) -> Dict[str, Any]:
        """
        Set webhook for bot through Telegram Bot API
        """
        try:
            # Check http_server presence (for safety, though it's required)
            if not self.http_server:
                return {
                    "result": "error",
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "http_server not found. Make sure http_server is included in dependencies"
                    }
                }
            
            # Get webhook URL from http_server
            webhook_url = self.http_server.get_webhook_url(self.webhook_endpoint)
            if not webhook_url:
                return {
                    "result": "error",
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "external_url not configured in http_server. Specify external server URL in http_server settings"
                    }
                }
            
            # Generate secret_token
            secret_token = self._generate_secret_token(bot_id)
            
            # Save mapping to cache
            await self._save_secret_token(secret_token, bot_id)
            
            # Call Telegram Bot API to set webhook
            api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
            
            # Always use self-signed certificate (generated in http_server on initialization)
            cert_result = self.http_server.get_certificate()
            if not cert_result:
                return {
                    "result": "error",
                    "error": {
                        "code": "CONFIG_ERROR",
                        "message": "SSL certificate generation error. Check external_url setting in http_server"
                    }
                }
            cert_pem, _ = cert_result
            
            # Telegram API requires multipart/form-data for certificate upload
            form_data = aiohttp.FormData()
            form_data.add_field('url', webhook_url)
            form_data.add_field('secret_token', secret_token)
            # allowed_updates passed as JSON array (Telegram API accepts JSON string)
            form_data.add_field('allowed_updates', json.dumps(self.allowed_updates))
            # certificate passed as file
            form_data.add_field('certificate', cert_pem, filename='cert.pem', content_type='application/x-pem-file')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, data=form_data) as response:
                    data = await response.json()
                
                if data.get('ok'):
                    self.logger.info(f"[Bot-{bot_id}] Webhook set: {webhook_url}")
                    return {
                        "result": "success",
                        "response_data": {
                            "webhook_url": webhook_url,
                            "secret_token": secret_token
                        }
                    }
                else:
                    error_description = data.get('description', 'Unknown error')
                    error_code = data.get('error_code', 0)
                    
                    # Handle webhook conflict (409)
                    if error_code == 409:
                        self.logger.warning(f"[Bot-{bot_id}] Webhook conflict, trying to delete old one...")
                        # Try to delete old webhook and set new one
                        delete_result = await self.delete_webhook(bot_token, bot_id)
                        if delete_result.get('result') == 'success':
                            # Retry setup
                            async with session.post(api_url, data=form_data) as retry_response:
                                retry_data = await retry_response.json()
                            
                            if retry_data.get('ok'):
                                self.logger.info(f"[Bot-{bot_id}] Webhook set after deleting old one")
                                return {
                                    "result": "success",
                                    "response_data": {
                                        "webhook_url": webhook_url,
                                        "secret_token": secret_token
                                    }
                                }
                    
                    self.logger.error(f"[Bot-{bot_id}] Error setting webhook: {error_description}")
                    return {
                        "result": "error",
                        "error": {
                            "code": "API_ERROR",
                            "message": f"Telegram API error: {error_description}",
                            "telegram_error_code": error_code
                        }
                    }
                        
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error setting webhook: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_webhook_info(self, bot_token: str, bot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get webhook information through Telegram Bot API getWebhookInfo
        Returns True if webhook is set and URL matches ours
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
                        
                        # Check if webhook is set (URL not empty)
                        is_webhook_active = bool(webhook_url)
                        
                        # If webhook set, check that URL matches ours
                        if is_webhook_active:
                            expected_url = self.http_server.get_webhook_url(self.webhook_endpoint)
                            if expected_url and webhook_url != expected_url:
                                # Webhook set but on different URL - consider inactive
                                self.logger.warning(f"{log_prefix} Webhook set on different URL: {webhook_url} (expected: {expected_url})")
                                is_webhook_active = False
                        
                        return {
                            "result": "success",
                            "response_data": {
                                "is_webhook_active": is_webhook_active,
                                "webhook_url": webhook_url
                            }
                        }
                    else:
                        error_description = data.get('description', 'Unknown error')
                        self.logger.warning(f"{log_prefix} Error getting webhook information: {error_description}")
                        # On error consider webhook inactive
                        return {
                            "result": "success",
                            "response_data": {
                                "is_webhook_active": False,
                                "webhook_url": ""
                            }
                        }
                        
        except Exception as e:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            self.logger.error(f"{log_prefix} Error getting webhook information: {e}")
            # On exception consider webhook inactive
            return {
                "result": "success",
                "response_data": {
                    "is_webhook_active": False,
                    "webhook_url": ""
                }
            }
    
    async def delete_webhook(self, bot_token: str, bot_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Delete webhook for bot through Telegram Bot API
        """
        try:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            
            api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
            
            # Telegram recommends using drop_pending_updates=false
            # to preserve accumulated updates for polling
            payload = {
                "drop_pending_updates": False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as response:
                    data = await response.json()
                    
                    if data.get('ok'):
                        self.logger.info(f"{log_prefix} Webhook deleted")
                        return {"result": "success"}
                    else:
                        error_description = data.get('description', 'Unknown error')
                        self.logger.warning(f"{log_prefix} Warning when deleting webhook: {error_description}")
                        # Don't consider this an error, as webhook may already be deleted
                        return {"result": "success"}
                        
        except Exception as e:
            log_prefix = f"[Bot-{bot_id}]" if bot_id else "[Bot]"
            self.logger.error(f"{log_prefix} Error deleting webhook: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }

