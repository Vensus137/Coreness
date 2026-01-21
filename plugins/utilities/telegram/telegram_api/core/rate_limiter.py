"""
RateLimiter - rate limiting for Telegram API requests based on Token Bucket
"""

import asyncio
import time
from typing import Any, Callable, Dict


class TokenBucket:
    """Token Bucket for rate limiting"""
    
    def __init__(self, bucket_size: int, tokens_per_minute: int):
        self.bucket_size = bucket_size
        self.tokens_per_second = tokens_per_minute / 60.0
        self.tokens = bucket_size
        self.last_refill = time.time()
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        time_passed = now - self.last_refill
        
        # Calculate how many tokens were refilled
        tokens_to_add = time_passed * self.tokens_per_second
        self.tokens = min(self.bucket_size, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens with waiting"""
        self._refill_tokens()
        
        if self.tokens >= tokens:
            # Tokens available - take immediately
            self.tokens -= tokens
            return True
        
        # No tokens - calculate wait time
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.tokens_per_second
        
        # Wait exact time until tokens appear
        await asyncio.sleep(wait_time)
        
        # After waiting tokens are definitely available
        self._refill_tokens()
        self.tokens -= tokens
        return True

class RateLimiter:
    """Rate limiter for HTTP requests to Telegram API based on Token Bucket"""
    
    def __init__(self, settings: dict, **kwargs):
        self.logger = kwargs['logger']
        
        # Get settings directly
        self.bot_bucket_size = settings.get('bot_bucket_size', 20)
        self.bot_tokens_per_minute = settings.get('bot_tokens_per_minute', 1800)
        self.chat_bucket_size = settings.get('chat_bucket_size', 20)
        self.chat_tokens_per_minute = settings.get('chat_tokens_per_minute', 20)
        
        # Token Buckets for each bot (bot_id -> TokenBucket)
        self._bot_buckets: Dict[int, TokenBucket] = {}
        
        # Token Buckets for each chat within bot ((bot_id, chat_id) -> TokenBucket)
        self._chat_buckets: Dict[tuple, TokenBucket] = {}
    
    def _get_bot_bucket(self, bot_id: int) -> TokenBucket:
        """Get TokenBucket for specific bot"""
        if bot_id not in self._bot_buckets:
            self._bot_buckets[bot_id] = TokenBucket(
                self.bot_bucket_size, 
                self.bot_tokens_per_minute
            )
        return self._bot_buckets[bot_id]
    
    def _get_chat_bucket(self, bot_id: int, chat_id: int) -> TokenBucket:
        """Get TokenBucket for specific chat within bot"""
        key = (bot_id, chat_id)
        if key not in self._chat_buckets:
            self._chat_buckets[key] = TokenBucket(
                self.chat_bucket_size, 
                self.chat_tokens_per_minute
            )
        return self._chat_buckets[key]
    
    async def execute_with_rate_limit(self, api_function: Callable, **kwargs) -> Any:
        """Execute API function with rate limiting"""
        bot_id = kwargs.pop('bot_id', None)  # Extract and remove bot_id
        chat_id = kwargs.pop('chat_id', 0)    # Extract and remove chat_id
        
        if not bot_id:
            self.logger.warning("bot_id not specified, executing without rate limiting")
            return await api_function(**kwargs)
        
        # 1. Bot-level limit (always applied)
        bot_bucket = self._get_bot_bucket(bot_id)
        await bot_bucket.try_acquire(1)
        
        # 2. Chat-level limit (only for groups/channels: chat_id < 0)
        if chat_id < 0:  # Group or channel
            chat_bucket = self._get_chat_bucket(bot_id, chat_id)
            await chat_bucket.try_acquire(1)
        
        # Execute API function WITHOUT bot_id and chat_id
        return await api_function(**kwargs)
    
    def cleanup(self):
        """Cleanup rate limiter"""
        self._bot_buckets.clear()
        self._chat_buckets.clear()
