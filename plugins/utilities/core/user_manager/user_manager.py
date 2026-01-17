"""
Утилита для управления данными пользователей с кэшированием
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class UserManager:
    """
    Утилита для управления данными пользователей с кэшированием
    - Автоматическое сохранение данных пользователей
    - Кэширование для предотвращения частых обращений к БД
    - Предоставление API для работы с данными пользователей
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_manager = kwargs['database_manager']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.cache_manager = kwargs['cache_manager']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("user_manager")
        
        # TTL для кэша (используется при явном указании, иначе берется из cache_manager)
        self.cache_ttl = settings.get('cache_ttl', 600)  # 10 минут по умолчанию
        
        # Получаем мастер-репозиторий
        self._master_repository = None
    
    def _get_master_repository(self):
        """Получение мастер-репозитория (ленивая инициализация)"""
        if self._master_repository is None:
            self._master_repository = self.database_manager.get_master_repository()
        return self._master_repository
    
    def _get_cache_key(self, user_id: int, tenant_id: int) -> str:
        """Генерация ключа кэша в формате cache_manager"""
        return f"user:{user_id}:{tenant_id}"
    
    async def save_user_data(self, user_data: Dict[str, Any]) -> bool:
        """
        Сохранение данных пользователя с кэшированием
        """
        try:
            user_id = user_data.get('user_id')
            tenant_id = user_data.get('tenant_id')
            
            if not user_id or not tenant_id:
                self.logger.warning("[UserManager] user_id и tenant_id обязательны для сохранения данных пользователя")
                return False
            
            cache_key = self._get_cache_key(user_id, tenant_id)
            
            # Проверяем кэш через cache_manager
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data is not None:
                # Данные есть в кэше - ничего не делаем
                return True
            
            # Получаем мастер-репозиторий
            master_repo = self._get_master_repository()
            
            # Проверяем, существует ли пользователь
            existing_user = await master_repo.get_user_by_id(user_id, tenant_id)
            
            if existing_user is not None:
                # Обновляем существующего пользователя
                success = await master_repo.update_user(user_id, tenant_id, user_data)
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка обновления пользователя")
                    return False
            else:
                # Создаем нового пользователя
                success = await master_repo.create_user(user_data)
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка создания пользователя")
                    return False
            
            # Загружаем полные данные из БД после операции
            full_user_data = await master_repo.get_user_by_id(user_id, tenant_id)
            
            # Сохраняем полные данные в кэш через cache_manager
            await self.cache_manager.set(cache_key, full_user_data.copy(), ttl=self.cache_ttl)
            
            return True
                
        except Exception as e:
            self.logger.error(f"Ошибка в save_user_data: {e}")
            return False
    
    async def get_user_by_id(self, user_id: int, tenant_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Получение данных пользователя
        """
        try:
            cache_key = self._get_cache_key(user_id, tenant_id)
            
            # Проверяем кэш через cache_manager (если не принудительное обновление)
            if not force_refresh:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data is not None:
                    return cached_data.copy()
            
            # Получаем из БД
            master_repo = self._get_master_repository()
            user_data = await master_repo.get_user_by_id(user_id, tenant_id)
            
            if user_data:
                # Сохраняем в кэш через cache_manager
                await self.cache_manager.set(cache_key, user_data.copy(), ttl=self.cache_ttl)
                
                return user_data
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка в get_user_data: {e}")
            return None
    
    async def set_user_state(self, user_id: int, tenant_id: int, state: Optional[str], expires_in_seconds: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Установка состояния пользователя с возвратом полных данных пользователя
        """
        try:
            # Если состояние None или пустая строка - сбрасываем
            if state is None or state == "":
                success = await self.clear_user_state(user_id, tenant_id)
                if success:
                    return await self.get_user_by_id(user_id, tenant_id, force_refresh=True)
                else:
                    return None
            
            # Вычисляем время истечения
            if expires_in_seconds is None or expires_in_seconds == 0:
                # Навсегда - устанавливаем дату в 3000 году
                expires_at = datetime(3000, 1, 1, 0, 0, 0)
            else:
                # Добавляем секунды к текущему времени
                current_time = await self.datetime_formatter.now_local()
                expires_at = current_time + timedelta(seconds=expires_in_seconds)
            
            # Обновляем БД
            master_repo = self._get_master_repository()
            success = await master_repo.update_user(user_id, tenant_id, {
                'user_state': state,
                'user_state_expired_at': expires_at
            })
            
            if success:
                # Получаем обновленные данные (принудительно)
                return await self.get_user_by_id(user_id, tenant_id, force_refresh=True)
            else:
                self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка установки состояния")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка в set_user_state: {e}")
            return None
    
    async def _validate_user_state(self, user_id: int, tenant_id: int, state: Optional[str], expires_at: Optional[datetime]) -> Optional[str]:
        """
        Валидация состояния пользователя с проверкой истечения
        """
        # Проверяем истечение
        if state is not None and expires_at is None:
            # Ошибка - есть состояние, но нет даты истечения, очищаем состояние
            self.logger.warning(f"[Tenant-{tenant_id}] [User-{user_id}] Состояние без даты истечения - очищаем")
            await self.clear_user_state(user_id, tenant_id)
            return None
        elif expires_at is not None and await self.datetime_formatter.now_local() > expires_at:
            # Состояние истекло - очищаем
            await self.clear_user_state(user_id, tenant_id)
            return None
        
        return state

    async def get_user_state(self, user_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение состояния пользователя с проверкой истечения
        Возвращает словарь с состоянием и временем истечения
        """
        try:
            # Получаем данные пользователя (метод сам работает с кэшем)
            user_data = await self.get_user_by_id(user_id, tenant_id)
            
            if user_data:
                state = user_data.get('user_state')
                expires_at = user_data.get('user_state_expired_at')
                
                # Проверяем истечение
                validated_state = await self._validate_user_state(user_id, tenant_id, state, expires_at)
                
                return {
                    'user_state': validated_state,
                    'user_state_expired_at': expires_at if validated_state else None
                }
            else:
                return {
                    'user_state': None,
                    'user_state_expired_at': None
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка в get_user_state: {e}")
            return None
    
    async def clear_user_state(self, user_id: int, tenant_id: int) -> bool:
        """
        Очистка состояния пользователя
        """
        try:
            # Обновляем БД
            master_repo = self._get_master_repository()
            success = await master_repo.update_user(user_id, tenant_id, {
                'user_state': None,
                'user_state_expired_at': None
            })
            
            if success:
                # Очищаем кэш для этого пользователя через cache_manager
                cache_key = self._get_cache_key(user_id, tenant_id)
                await self.cache_manager.delete(cache_key)
                return True
            else:
                self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка очистки состояния")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка в clear_user_state: {e}")
            return False
