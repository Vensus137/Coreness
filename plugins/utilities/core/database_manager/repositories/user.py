"""
Repository for working with users
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select, update

from ..models import TenantUser
from .base import BaseRepository


class UserRepository(BaseRepository):
    """
    Repository for working with users
    """
    
    async def get_user_ids_by_tenant(self, tenant_id: int) -> Optional[List[int]]:
        """
        Get list of all user_id for specified tenant
        """
        try:
            with self._get_session() as session:
                stmt = select(TenantUser.user_id).where(TenantUser.tenant_id == tenant_id)
                result = session.execute(stmt).scalars().all()
                
                return list(result)
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting user list: {e}")
            return None
    
    async def get_user_by_id(self, user_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user data by Telegram user_id and tenant_id
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
            self.logger.error(f"Error getting user data: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[bool]:
        """
        Create user
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
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
            self.logger.error(f"Error creating user: {e}")
            return None
    
    async def update_user(self, user_id: int, tenant_id: int, user_data: Dict[str, Any]) -> Optional[bool]:
        """
        Update user
        """
        try:
            with self._get_session() as session:
                # Prepare data for update via data_preparer
                # Pass entire user_data - data_preparer will filter existing fields itself
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=TenantUser,
                    fields=user_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    self.logger.warning(f"[Tenant-{tenant_id}] [User-{user_id}] No fields to update user")
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
                    self.logger.warning(f"[Tenant-{tenant_id}] [User-{user_id}] User not found for update")
                    return False
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error updating user: {e}")
            return None

