"""
Утилита для генерации детерминированных уникальных ID через IdSequence
"""

import hashlib
import uuid
from typing import Optional


class IdGenerator:
    """
    Утилита для генерации детерминированных уникальных ID
    При одинаковых seed возвращает тот же ID
    Поддерживает кэширование через cache_manager
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_manager = kwargs['database_manager']
        self.cache_manager = kwargs['cache_manager']
        self.settings_manager = kwargs['settings_manager']
        
        # Получаем настройки кэша
        settings = self.settings_manager.get_plugin_settings('id_generator')
        self.cache_ttl = settings.get('cache_ttl', 600)  # 10 минут по умолчанию
    
    def _calculate_hash(self, seed: str) -> str:
        """
        Вычисление MD5 хэша от seed
        """
        return hashlib.md5(seed.encode('utf-8')).hexdigest()
    
    def _get_cache_key(self, hash_value: str) -> str:
        """Генерация ключа кэша в формате cache_manager"""
        return f"id:hash:{hash_value}"
    
    async def get_or_create_unique_id(self, seed: Optional[str] = None) -> Optional[int]:
        """
        Получение или создание уникального ID для seed
        Возвращает существующий ID если seed уже был, или создает новый
        
        Если seed не указан, генерируется случайный UUID (сохраняется в БД для отладки)
        Поддерживает кэширование через cache_manager
        """
        try:
            # Если seed не передан, генерируем UUID (сохраняется в БД для отладки)
            if seed is None:
                seed = str(uuid.uuid4())
            else:
                # Преобразуем в строку, если это не строка
                if not isinstance(seed, str):
                    try:
                        seed = str(seed)
                    except Exception as e:
                        self.logger.error(f"Не удалось преобразовать seed в строку: {e}")
                        return None
            
            # Вычисляем хэш от seed
            hash_value = self._calculate_hash(seed)
            
            # Проверяем кэш
            cache_key = self._get_cache_key(hash_value)
            cached_id = await self.cache_manager.get(cache_key)
            if cached_id is not None:
                return cached_id
            
            # Получаем master repository
            master_repo = self.database_manager.get_master_repository()
            
            # Используем метод-обертку для получения или создания ID
            # seed всегда сохраняется в БД (либо переданный пользователем, либо сгенерированный UUID) для удобства отладки
            unique_id = await master_repo.get_or_create_id_sequence(
                hash_value=hash_value,
                seed=seed
            )
            
            # Сохраняем в кэш (если ID получен)
            if unique_id is not None:
                await self.cache_manager.set(cache_key, unique_id, ttl=self.cache_ttl)
            
            return unique_id
                
        except Exception as e:
            self.logger.error(f"Ошибка генерации уникального ID: {e}")
            return None
    

