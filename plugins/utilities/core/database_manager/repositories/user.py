"""
Репозиторий для работы с пользователями
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select, update

from ..models import TenantUser
from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    Репозиторий для работы с пользователями
    """
    
    async def get_user_ids_by_tenant(self, tenant_id: int) -> Optional[List[int]]:
        """
        Получить список всех user_id для указанного тенанта
        """
        try:
            with self._get_session() as session:
                stmt = select(TenantUser.user_id).where(TenantUser.tenant_id == tenant_id)
                result = session.execute(stmt).scalars().all()
                
                return list(result)
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения списка пользователей: {e}")
            return None
    
    async def get_user_by_id(self, user_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение данных пользователя по Telegram user_id и tenant_id
        """
        try:
            with self._get_session() as session:
                stmt = select(TenantUser).where(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id
                )
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                    
        except Exception as e:
            self.logger.error(f"Ошибка получения данных пользователя: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[bool]:
        """
        Создать пользователя
        """
        try:
            with self._get_session() as session:
                # Подготавливаем данные для вставки через data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=TenantUser,
                    fields={
                        'tenant_id': user_data.get('tenant_id'),
                        'user_id': user_data.get('user_id'),
                        'username': user_data.get('username'),
                        'first_name': user_data.get('first_name'),
                        'last_name': user_data.get('last_name'),
                        'language_code': user_data.get('language_code'),
                        'is_bot': user_data.get('is_bot', False),
                        'is_premium': user_data.get('is_premium', False)
                    },
                    json_fields=[]
                )
                
                stmt = insert(TenantUser).values(**prepared_fields)
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка создания пользователя: {e}")
            return None
    
    async def update_user(self, user_id: int, tenant_id: int, user_data: Dict[str, Any]) -> Optional[bool]:
        """
        Обновить пользователя
        """
        try:
            with self._get_session() as session:
                # Подготавливаем данные для обновления через data_preparer
                # Передаем весь user_data - data_preparer сам отфильтрует существующие поля
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=TenantUser,
                    fields=user_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    self.logger.warning(f"[Tenant-{tenant_id}] [User-{user_id}] Нет полей для обновления пользователя")
                    return False
                
                stmt = update(TenantUser).where(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.user_id == user_id
                ).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                if result.rowcount > 0:
                    return True
                else:
                    self.logger.warning(f"[Tenant-{tenant_id}] [User-{user_id}] Пользователь не найден для обновления")
                    return False
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка обновления пользователя: {e}")
            return None

