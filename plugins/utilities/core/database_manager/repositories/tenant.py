"""
Repository for working with tenant data
Contains methods for getting tenant, bot and command configuration
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select

from ..models import Tenant
from .base import BaseRepository


class TenantRepository(BaseRepository):
    """
    Repository for working with tenant data
    """
    
    def __init__(self, session_factory, **kwargs):
        super().__init__(session_factory, **kwargs)
    
    async def get_all_tenant_ids(self) -> Optional[List[int]]:
        """
        Get list of all tenant IDs
        """
        try:
            with self._get_session() as session:
                stmt = select(Tenant.id)
                result = session.execute(stmt).scalars().all()
                
                return list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting tenant list: {e}")
            return None
    
    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tenant by ID
        """
        try:
            with self._get_session() as session:
                stmt = select(Tenant).where(Tenant.id == tenant_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                
        except Exception:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting tenant")
            return None
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Optional[int]:
        """
        Create tenant
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
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
            self.logger.error(f"Error creating tenant: {e}")
            return None
    
    async def update_tenant(self, tenant_id: int, tenant_data: Dict[str, Any]) -> Optional[bool]:
        """
        Update tenant
        """
        try:
            with self._get_session() as session:
                from sqlalchemy import update
                
                # Prepare data for update via data_preparer
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Tenant,
                    fields=tenant_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    self.logger.warning(f"[Tenant-{tenant_id}] No fields to update tenant")
                    return False
                
                stmt = update(Tenant).where(Tenant.id == tenant_id).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                if result.rowcount > 0:
                    return True
                else:
                    self.logger.warning(f"Tenant {tenant_id} not found for update")
                    return False
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error updating tenant: {e}")
            return None
    
