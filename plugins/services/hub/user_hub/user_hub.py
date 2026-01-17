"""
User Hub Service - центральный сервис для управления состояниями пользователей
"""

from typing import Any, Dict

from .storage.user_storage_manager import UserStorageManager


class UserHubService:
    """
    Центральный сервис для управления состояниями пользователей
    Обертка над user_manager для использования в сценариях
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.user_manager = kwargs['user_manager']
        self.database_manager = kwargs['database_manager']
        
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('user_hub')
        
        # Регистрируем себя в ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('user_hub', self)
        
        # Создаем менеджер хранилища пользователя
        self.user_storage_manager = UserStorageManager(
            self.database_manager,
            self.logger,
            self.settings_manager
        )
    
    # === Actions для ActionHub ===
    
    async def set_user_state(self, data: dict) -> Dict[str, Any]:
        """
        Установка состояния пользователя
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            user_id = data.get('user_id')
            tenant_id = data.get('tenant_id')
            state = data.get('state')
            expires_in_seconds = data.get('expires_in_seconds')
            
            # Вызываем метод user_manager (теперь возвращает полные данные)
            user_data = await self.user_manager.set_user_state(
                user_id=user_id,
                tenant_id=tenant_id,
                state=state,
                expires_in_seconds=expires_in_seconds
            )
            
            if user_data is not None:
                return {
                    "result": "success",
                    "response_data": {
                        "user_state": user_data.get('user_state'),
                        "user_state_expired_at": user_data.get('user_state_expired_at')
                    }
                }
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось установить состояние пользователя"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка установки состояния пользователя: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_user_state(self, data: dict) -> Dict[str, Any]:
        """
        Получение состояния пользователя
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            user_id = data.get('user_id')
            tenant_id = data.get('tenant_id')
            
            # Получаем состояние и время истечения одним вызовом
            state_data = await self.user_manager.get_user_state(user_id, tenant_id)
            
            if state_data:
                return {
                    "result": "success",
                    "response_data": {
                        "user_state": state_data.get('user_state'),
                        "user_state_expired_at": state_data.get('user_state_expired_at')
                    }
                }
            else:
                return {
                    "result": "success",
                    "response_data": {
                        "user_state": None,
                        "user_state_expired_at": None
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения состояния пользователя: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def clear_user_state(self, data: dict) -> Dict[str, Any]:
        """
        Очистка состояния пользователя
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            user_id = data.get('user_id')
            tenant_id = data.get('tenant_id')
            
            # Вызываем метод user_manager для очистки состояния
            success = await self.user_manager.clear_user_state(
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            if success:
                return {"result": "success"}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось очистить состояние пользователя"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка очистки состояния пользователя: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    # === User Storage Actions ===
    
    async def get_user_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Получение значений storage для пользователя"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Преобразуем число в строку для key (если передано число)
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.user_storage_manager.get_storage(
                data.get('tenant_id'),
                data.get('user_id'),
                key=key,
                key_pattern=data.get('key_pattern'),
                format_yaml=data.get('format', False)
            )
        except Exception as e:
            self.logger.error(f"Ошибка получения storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def set_user_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Установка значений storage для пользователя
        Поддерживает смешанный подход с приоритетом: key -> value -> values
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            user_id = data.get('user_id')
            key = data.get('key')
            # Преобразуем число в строку для key (если передано число)
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            value = data.get('value')
            values = data.get('values')
            
            return await self.user_storage_manager.set_storage(
                tenant_id,
                user_id,
                key=key,
                value=value,
                values=values,
                format_yaml=data.get('format', False)
            )
        except Exception as e:
            self.logger.error(f"Ошибка установки storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def delete_user_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление значений из storage"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Преобразуем число в строку для key (если передано число)
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.user_storage_manager.delete_storage(
                data.get('tenant_id'),
                data.get('user_id'),
                key=key,
                key_pattern=data.get('key_pattern')
            )
        except Exception as e:
            self.logger.error(f"Ошибка удаления storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_tenant_users(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение списка всех user_id для указанного тенанта
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            master_repo = self.database_manager.get_master_repository()
            user_ids = await master_repo.get_user_ids_by_tenant(tenant_id)
            
            return {
                "result": "success",
                "response_data": {
                    "user_ids": user_ids,
                    "user_count": len(user_ids)
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения списка пользователей: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_users_by_storage_value(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Поиск пользователей по ключу и значению в storage
        Позволяет найти всех пользователей, у которых в storage есть определенный ключ с определенным значением
        Например, найти всех пользователей с подключенной подпиской
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            key = data.get('key')
            value = data.get('value')
            
            # Используем UserStorageManager для поиска
            user_ids = await self.user_storage_manager.find_users_by_storage_value(
                tenant_id=tenant_id,
                key=key,
                value=value
            )
            
            return {
                "result": "success",
                "response_data": {
                    "user_ids": user_ids,
                    "user_count": len(user_ids)
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка поиска пользователей по storage key={key}, value={value}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }