"""
RateLimiter - ограничение частоты запросов к Telegram API на основе Token Bucket
"""

import asyncio
import time
from typing import Any, Callable, Dict


class TokenBucket:
    """Token Bucket для rate limiting"""
    
    def __init__(self, bucket_size: int, tokens_per_minute: int):
        self.bucket_size = bucket_size
        self.tokens_per_second = tokens_per_minute / 60.0
        self.tokens = bucket_size
        self.last_refill = time.time()
    
    def _refill_tokens(self):
        """Восстановление токенов на основе прошедшего времени"""
        now = time.time()
        time_passed = now - self.last_refill
        
        # Вычисляем сколько токенов восстановилось
        tokens_to_add = time_passed * self.tokens_per_second
        self.tokens = min(self.bucket_size, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """Попытка получить токены с ожиданием"""
        self._refill_tokens()
        
        if self.tokens >= tokens:
            # Токены есть - сразу берем
            self.tokens -= tokens
            return True
        
        # Токенов нет - вычисляем время ожидания
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.tokens_per_second
        
        # Ждем точное время до появления токенов
        await asyncio.sleep(wait_time)
        
        # После ожидания токены точно есть
        self._refill_tokens()
        self.tokens -= tokens
        return True

class RateLimiter:
    """Rate limiter для HTTP запросов к Telegram API на основе Token Bucket"""
    
    def __init__(self, settings: dict, **kwargs):
        self.logger = kwargs['logger']
        
        # Получаем настройки напрямую
        self.bot_bucket_size = settings.get('bot_bucket_size', 20)
        self.bot_tokens_per_minute = settings.get('bot_tokens_per_minute', 1800)
        self.chat_bucket_size = settings.get('chat_bucket_size', 20)
        self.chat_tokens_per_minute = settings.get('chat_tokens_per_minute', 20)
        
        # Token Buckets для каждого бота (bot_id -> TokenBucket)
        self._bot_buckets: Dict[int, TokenBucket] = {}
        
        # Token Buckets для каждого чата в рамках бота ((bot_id, chat_id) -> TokenBucket)
        self._chat_buckets: Dict[tuple, TokenBucket] = {}
    
    def _get_bot_bucket(self, bot_id: int) -> TokenBucket:
        """Получить TokenBucket для конкретного бота"""
        if bot_id not in self._bot_buckets:
            self._bot_buckets[bot_id] = TokenBucket(
                self.bot_bucket_size, 
                self.bot_tokens_per_minute
            )
        return self._bot_buckets[bot_id]
    
    def _get_chat_bucket(self, bot_id: int, chat_id: int) -> TokenBucket:
        """Получить TokenBucket для конкретного чата в рамках бота"""
        key = (bot_id, chat_id)
        if key not in self._chat_buckets:
            self._chat_buckets[key] = TokenBucket(
                self.chat_bucket_size, 
                self.chat_tokens_per_minute
            )
        return self._chat_buckets[key]
    
    async def execute_with_rate_limit(self, api_function: Callable, **kwargs) -> Any:
        """Выполнить API функцию с учетом rate limiting"""
        bot_id = kwargs.pop('bot_id', None)  # Извлекаем и удаляем bot_id
        chat_id = kwargs.pop('chat_id', 0)    # Извлекаем и удаляем chat_id
        
        if not bot_id:
            self.logger.warning("bot_id не указан, выполняем без rate limiting")
            return await api_function(**kwargs)
        
        # 1. Bot-level лимит (всегда применяется)
        bot_bucket = self._get_bot_bucket(bot_id)
        await bot_bucket.try_acquire(1)
        
        # 2. Chat-level лимит (только для групп/каналов: chat_id < 0)
        if chat_id < 0:  # Группа или канал
            chat_bucket = self._get_chat_bucket(bot_id, chat_id)
            await chat_bucket.try_acquire(1)
        
        # Выполняем API функцию БЕЗ bot_id и chat_id
        return await api_function(**kwargs)
    
    def cleanup(self):
        """Очистка rate limiter"""
        self._bot_buckets.clear()
        self._chat_buckets.clear()
