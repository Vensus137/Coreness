import os
from typing import Optional

from aiogram import Bot


class BotInitializer:
    """
    Утилита для централизованной инициализации Telegram бота.
    Получает токен из переменной окружения TELEGRAM_BOT_TOKEN.
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self._bot: Optional[Bot] = None
        self._token: Optional[str] = None
        
        # Получаем токен из переменной окружения
        self._token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self._token:
            self.logger.warning("BotInitializer: переменная окружения TELEGRAM_BOT_TOKEN не установлена")
    
    def get_token(self) -> str:
        """Получить токен бота"""
        return self._token or ""
    
    def is_initialized(self) -> bool:
        """Проверить, инициализирован ли бот"""
        return self._bot is not None
    
    def get_bot(self) -> Bot:
        """Получить экземпляр инициализированного бота"""
        if not self._bot:
            if not self._token:
                raise ValueError("Токен бота не найден. Установите переменную окружения TELEGRAM_BOT_TOKEN")
            
            self.logger.info("BotInitializer: инициализация Telegram бота...")
            self._bot = Bot(token=self._token)
            self.logger.info("BotInitializer: бот успешно инициализирован")
        
        return self._bot
    
    def shutdown(self):
        """Корректное завершение работы бота"""
        if self._bot:
            self.logger.info("BotInitializer: завершение работы бота...")
            # Здесь можно добавить логику для корректного завершения сессии
            self._bot = None
            self.logger.info("BotInitializer: бот завершен") 