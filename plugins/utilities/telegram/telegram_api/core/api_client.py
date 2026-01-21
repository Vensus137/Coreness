"""
APIClient - HTTP client for Telegram Bot API
"""

import json
from typing import Any, Dict

import aiohttp


class APIClient:
    """HTTP client for Telegram Bot API"""
    
    def __init__(self, session: aiohttp.ClientSession, rate_limiter, **kwargs):
        self.logger = kwargs['logger']
        self.session = session
        self.base_url = "https://api.telegram.org/bot"
        self.rate_limiter = rate_limiter
    
    async def make_request(self, bot_token: str, method: str, payload: dict) -> Dict[str, Any]:
        """Execute request to Telegram API without rate limiting (regular requests)"""
        return await self._make_http_request(bot_token, method, payload)
    
    async def make_request_with_limit(self, bot_token: str, method: str, payload: dict, bot_id: int = 0, chat_id: int = 0) -> Dict[str, Any]:
        """Execute request to Telegram API with rate limiting (for spam actions)"""
        # If bot_id not provided, extract it from token
        if not bot_id:
            try:
                bot_id = int(bot_token.split(':')[0])
            except (ValueError, IndexError):
                self.logger.warning("Failed to extract bot_id from token, executing without rate limiting")
                return await self._make_http_request(bot_token, method, payload)
        
        # Use rate limiter to execute request
        return await self.rate_limiter.execute_with_rate_limit(
            self._make_http_request,
            token=bot_token,
            method=method,
            payload=payload,
            bot_id=bot_id,
            chat_id=chat_id
        )
    
    async def _make_http_request(self, token: str, method: str, payload: dict) -> Dict[str, Any]:
        """Execute HTTP request to Telegram API (internal method)"""
        try:
            # Build URL
            url = f"{self.base_url}{token}/{method}"
            
            # Clean payload from None values
            clean_payload = {k: v for k, v in payload.items() if v is not None}
            
            # Execute HTTP request
            async with self.session.post(
                url,
                json=clean_payload,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                # Get response
                response_data = await response.json()
                
                # Process response
                return self._process_response(response.status, response_data)
                
        except aiohttp.ClientTimeout:
            self.logger.warning(f"Request timeout to API: {method}")
            return {
                "result": "timeout",
                "error": {
                    "code": "TIMEOUT",
                    "message": "Request timeout"
                }
            }
            
        except aiohttp.ClientError as e:
            self.logger.error(f"Network error on API request: {method} - {e}")
            return {
                "result": "timeout",
                "error": {
                    "code": "TIMEOUT",
                    "message": f"Network error: {e}"
                }
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error in response: {method} - {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": f"Invalid JSON response: {e}"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Unexpected error on API request: {method} - {e}")
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": f"Unexpected error: {e}"
                }
            }
    
    def _process_response(self, status_code: int, response_data: dict) -> Dict[str, Any]:
        """Process response from Telegram API"""
        
        # Successful response (200)
        if status_code == 200:
            if response_data.get('ok', False):
                return {
                    "result": "success",
                    "response_data": response_data.get('result', {})
                }
            else:
                # Telegram API returned error
                error_code = response_data.get('error_code', 0)
                description = response_data.get('description', 'Unknown error')
                
                # Determine error type
                if error_code == 401:
                    return {
                        "result": "not_found",
                        "error": {
                            "code": "NOT_FOUND",
                            "message": f"HTTP {error_code}: {description}"
                        }
                    }
                elif error_code == 429:
                    return {
                        "result": "timeout",
                        "error": {
                            "code": "TIMEOUT",
                            "message": f"HTTP {error_code}: {description}"
                        }
                    }
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "API_ERROR",
                            "message": f"HTTP {error_code}: {description}"
                        }
                    }
        
        # HTTP errors
        elif status_code == 401:
            return {
                "result": "not_found",
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Unauthorized"
                }
            }
        elif status_code == 429:
            return {
                "result": "timeout",
                "error": {
                    "code": "TIMEOUT",
                    "message": "Too Many Requests"
                }
            }
        elif status_code >= 400:
            # For HTTP errors try to extract description from response_data
            description = response_data.get('description', f'HTTP {status_code}')
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": f"HTTP {status_code}: {description}"
                }
            }
        else:
            return {
                "result": "error",
                "error": {
                    "code": "API_ERROR",
                    "message": f"Unexpected status code: {status_code}"
                }
            }
