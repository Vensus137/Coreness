"""
CacheManager - единая утилита для глобального кэширования данных
In-memory кэш для всех сервисов с поддержкой TTL и инвалидации
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class CacheManager:
    """
    Единая утилита для глобального кэширования данных
    - In-memory кэш (Python dicts)
    - Поддержка TTL
    - Инвалидация по паттернам
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Получаем настройки
        settings = self.settings_manager.get_plugin_settings("cache_manager")
        
        # Основной кэш (плоский словарь, ключи вида "group:key")
        self._cache: Dict[str, Any] = {}
        
        # Время истечения для элементов с TTL (как в Redis - храним expired_at)
        self._cache_expires_at: Dict[str, datetime] = {}
        
        # Дефолтный TTL для защиты от утечки памяти (если не указан явно при set())
        self._default_ttl = settings.get('default_ttl', 3600)  # 1 час по умолчанию
        
        # Настройки периодической очистки (алгоритм как в Redis)
        self._cleanup_interval = settings.get('cleanup_interval', 60)  # 1 минута по умолчанию
        self._cleanup_sample_size = settings.get('cleanup_sample_size', 50)  # Размер выборки
        self._cleanup_expired_threshold = settings.get('cleanup_expired_threshold', 0.25)  # Порог 25%
        
        # Фоновая задача для периодической очистки
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Запускаем фоновую задачу при инициализации
        self._start_background_cleanup()

    # === Фоновые задачи ===

    def _start_background_cleanup(self):
        """
        Запуск фоновой задачи при инициализации (синхронный метод)
        """
        if self._is_running:
            return
        
        try:
            # Пытаемся создать задачу (как в task_manager)
            # asyncio.ensure_future() работает если loop уже запущен или будет запущен
            self._is_running = True
            self._cleanup_task = asyncio.ensure_future(self._cleanup_loop())
            self.logger.info(f"Запланирована фоновая задача очистки кэша (интервал: {self._cleanup_interval} сек)")
        except RuntimeError as e:
            # Event loop не доступен - это проблема, задача не запустится
            self._is_running = False
            self.logger.error(f"Не удалось запустить фоновую задачу очистки кэша при инициализации: {e}. Периодическая очистка не будет работать!")
    
    async def _cleanup_loop(self):
        """
        Фоновый цикл периодической очистки кэша
        """
        try:
            while self._is_running:
                await asyncio.sleep(self._cleanup_interval)
                if self._is_running:
                    await self._clean_expired_cache()
        except asyncio.CancelledError:
            self.logger.info("Фоновая задача очистки кэша остановлена")
        except Exception as e:
            self.logger.error(f"Ошибка в фоновой задаче очистки кэша: {e}")
    
    def stop_background_cleanup(self):
        """
        Остановка фоновой задачи очистки кэша (синхронный метод для shutdown)
        """
        if not self._is_running:
            return
        
        self._is_running = False
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            # Не ждем завершения задачи здесь, т.к. это синхронный метод
            # Задача завершится при остановке event loop
        self.logger.info("Фоновая задача очистки кэша остановлена")

    # === Методы для работы с кэшем ===
    
    def _is_cache_valid(self, key: str) -> bool:
        """
        Проверка валидности элемента кэша (ленивая очистка, как в Redis)
        Если элемент истек - удаляется сразу
        """
        # Проверяем наличие значения в кэше
        if key not in self._cache:
            return False
        
        # Если нет времени истечения - кэш вечный
        if key not in self._cache_expires_at:
            return True
        
        # Простое сравнение времени (как в Redis - храним expired_at)
        current_time = datetime.now()
        if current_time >= self._cache_expires_at[key]:
            # Удаляем истекший элемент
            self._cache.pop(key, None)
            self._cache_expires_at.pop(key, None)
            return False
        
        return True
    
    async def _clean_expired_cache(self):
        """
        Периодическая очистка истекших элементов кэша (алгоритм как в Redis)
        1. Берем случайную выборку из всех элементов с TTL
        2. Если >25% истекли - делаем полную очистку
        3. Если <25% - только выборка
        """
        
        current_time = datetime.now()
        
        # Получаем все ключи с TTL
        keys_with_ttl = list(self._cache_expires_at.keys())
        
        if not keys_with_ttl:
            return
        
        # Берем случайную выборку (как в Redis)
        sample_size = min(self._cleanup_sample_size, len(keys_with_ttl))
        sample_keys = random.sample(keys_with_ttl, sample_size)
        
        # Проверяем выборку
        expired_in_sample = 0
        for key in sample_keys:
            if current_time >= self._cache_expires_at[key]:
                expired_in_sample += 1
        
        # Вычисляем процент истекших в выборке
        expired_ratio = expired_in_sample / sample_size if sample_size > 0 else 0
        
        # Если >25% истекли - делаем полную очистку
        if expired_ratio >= self._cleanup_expired_threshold:
            # Полная очистка - перебираем все элементы
            expired_keys = []
            for key in keys_with_ttl:
                if current_time >= self._cache_expires_at[key]:
                    expired_keys.append(key)
            
            # Удаляем истекшие
            for key in expired_keys:
                self._cache.pop(key, None)
                self._cache_expires_at.pop(key, None)
        else:
            # <25% истекли - удаляем только те, что нашли в выборке
            expired_keys = [key for key in sample_keys 
                           if current_time >= self._cache_expires_at[key]]
            
            for key in expired_keys:
                self._cache.pop(key, None)
                self._cache_expires_at.pop(key, None)
    
    # === Базовые методы ===
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша по ключу
        Ленивая очистка: проверка конкретного элемента при обращении (как в Redis)
        """
        try:
            # Ленивая очистка: проверяем валидность конкретного элемента
            if not self._is_cache_valid(key):
                return None
            
            return self._cache.get(key)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения значения из кэша для ключа '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Установка значения в кэш
        Если TTL не указан - используется default_ttl (защита от утечки памяти)
        """
        try:
            # Устанавливаем значение
            self._cache[key] = value
            
            # Определяем TTL (храним expired_at как в Redis)
            # Если TTL не указан - используем дефолтный
            final_ttl = ttl if ttl is not None else self._default_ttl
            
            # Устанавливаем время истечения (всегда есть TTL)
            self._cache_expires_at[key] = datetime.now() + timedelta(seconds=final_ttl)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка установки значения в кэш для ключа '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Удаление значения из кэша
        """
        try:
            # Проверяем валидность перед удалением (ленивая очистка)
            if not self._is_cache_valid(key):
                # Ключ истек или не существует
                return False
            
            deleted = False
            if key in self._cache:
                del self._cache[key]
                deleted = True
            
            if key in self._cache_expires_at:
                del self._cache_expires_at[key]
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления значения из кэша для ключа '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Проверка существования ключа в кэше
        """
        return self._is_cache_valid(key)
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидация ключей по паттерну
        Поддерживает простые паттерны: 'bot:*', 'tenant:123:*', '*:meta'
        """
        try:
            deleted_count = 0
            keys_to_delete = []
            
            # Простая реализация паттернов
            if pattern.endswith(':*'):
                prefix = pattern[:-2]  # Убираем ':*'
                keys_to_delete = [key for key in self._cache.keys() if key.startswith(prefix + ':')]
            elif pattern.startswith('*:'):
                suffix = pattern[2:]  # Убираем '*:'
                keys_to_delete = [key for key in self._cache.keys() if key.endswith(':' + suffix)]
            elif '*' in pattern:
                # Более сложный паттерн (можно расширить позже)
                prefix, suffix = pattern.split('*', 1)
                keys_to_delete = [
                    key for key in self._cache.keys()
                    if key.startswith(prefix) and key.endswith(suffix)
                ]
            else:
                # Точное совпадение
                keys_to_delete = [pattern] if pattern in self._cache else []
            
            for key in keys_to_delete:
                if await self.delete(key):
                    deleted_count += 1
            
            if deleted_count > 0:
                self.logger.info(f"Инвалидировано {deleted_count} ключей по паттерну '{pattern}'")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Ошибка инвалидации по паттерну '{pattern}': {e}")
            return 0
    
    async def clear(self) -> bool:
        """
        Очистка всего кэша
        """
        try:
            count = len(self._cache)
            self._cache.clear()
            self._cache_expires_at.clear()
            self.logger.info(f"Очищен весь кэш ({count} элементов)")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")
            return False
    
    # === Вспомогательные методы ===
    
    def shutdown(self):
        """
        Остановка фоновой задачи очистки кэша (для graceful shutdown)
        """
        self.stop_background_cleanup()
    

