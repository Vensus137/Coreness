"""
Репозиторий для работы с данными tenant'а
Содержит методы для получения конфигурации tenant'а, бота и команд
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select

from ..models import Tenant
from .base import BaseRepository


class TenantRepository(BaseRepository):
    """
    Репозиторий для работы с данными tenant'а
    """
    
    def __init__(self, session_factory, **kwargs):
        super().__init__(session_factory, **kwargs)
    
    async def get_all_tenant_ids(self) -> Optional[List[int]]:
        """
        Получить список всех ID тенантов
        """
        try:
            with self._get_session() as session:
                stmt = select(Tenant.id)
                result = session.execute(stmt).scalars().all()
                
                return list(result)
                
        except Exception as e:
            self.logger.error(f"Ошибка получения списка тенантов: {e}")
            return None
    
    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить тенанта по ID
        """
        try:
            with self._get_session() as session:
                stmt = select(Tenant).where(Tenant.id == tenant_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения тенанта")
            return None
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Optional[int]:
        """
        Создать тенанта
        """
        try:
            with self._get_session() as session:
                # Подготавливаем данные для вставки через data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=Tenant,
                    fields={
                        'id': tenant_data.get('id'),
                        'ai_token': tenant_data.get('ai_token')
                    },
                    json_fields=[]
                )
                
                stmt = insert(Tenant).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                tenant_id = result.inserted_primary_key[0]
                return tenant_id
                
        except Exception as e:
            self.logger.error(f"Ошибка создания тенанта: {e}")
            return None
    
    async def update_tenant(self, tenant_id: int, tenant_data: Dict[str, Any]) -> Optional[bool]:
        """
        Обновить тенанта
        """
        try:
            with self._get_session() as session:
                from sqlalchemy import update
                
                # Подготавливаем данные для обновления через data_preparer
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Tenant,
                    fields=tenant_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    self.logger.warning(f"[Tenant-{tenant_id}] Нет полей для обновления тенанта")
                    return False
                
                stmt = update(Tenant).where(Tenant.id == tenant_id).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                if result.rowcount > 0:
                    return True
                else:
                    self.logger.warning(f"Тенант {tenant_id} не найден для обновления")
                    return False
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка обновления тенанта: {e}")
            return None
    
