"""
Repository for working with user data storage (user_storage)
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select, update

from ..models import UserStorage
from .base import BaseRepository


class UserStorageRepository(BaseRepository):
    """
    Repository for working with user data storage
    """
    
    async def get_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Universal get storage records
        
        Mode determination logic:
        - If all parameters None (except tenant_id, user_id) - get all user records
        - If key specified - get specific value
        - If key_pattern specified - get values by pattern
        
        Values are converted to required types (int, float, bool, list, dict or str)
        
        limit: optional limit on number of returned records
        """
        try:
            with self._get_session() as session:
                conditions = [
                    UserStorage.tenant_id == tenant_id,
                    UserStorage.user_id == user_id
                ]
                
                # Key: if exact value exists - use it, otherwise pattern
                if key:
                    conditions.append(UserStorage.key == key)
                elif key_pattern:
                    conditions.append(UserStorage.key.ilike(key_pattern))
                
                stmt = select(UserStorage).where(*conditions)
                
                # Apply limit if specified
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                
                # Convert value automatically via convert_text_fields
                return await self._to_dict_list(result, convert_text_fields=['value'])
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error getting storage records: {e}")
            return None
    
    async def set_records(self, tenant_id: int, user_id: int, values: Dict[str, Any]) -> Optional[bool]:
        """
        Universal set storage records (batch for all keys)
        
        Accepts structure {key: value} for setting one or multiple values
        Optimized version: first get all existing records with one query,
        then perform batch insert/update
        """
        try:
            if not values:
                return True  # No data to set
            
            with self._get_session() as session:
                # Get all existing records for user with one query
                existing_keys = set()
                if values:
                    existing_records = session.execute(
                        select(UserStorage.key).where(
                            UserStorage.tenant_id == tenant_id,
                            UserStorage.user_id == user_id,
                            UserStorage.key.in_(values.keys())
                        )
                    ).scalars().all()
                    existing_keys = set(existing_records)
                
                # Split into insert and update
                to_insert = []
                to_update = []
                
                for key, value in values.items():
                    if key in existing_keys:
                        to_update.append((key, value))
                    else:
                        to_insert.append({
                            'tenant_id': tenant_id,
                            'user_id': user_id,
                            'key': key,
                            'value': value
                        })
                
                # Batch insert for new records
                if to_insert:
                    prepared_inserts = []
                    for record in to_insert:
                        prepared_fields = await self.data_preparer.prepare_for_insert(
                            model=UserStorage,
                            fields=record,
                            json_fields=[]
                        )
                        prepared_inserts.append(prepared_fields)
                    
                    if prepared_inserts:
                        session.execute(insert(UserStorage), prepared_inserts)
                
                # Batch update for existing records
                if to_update:
                    for key, value in to_update:
                        prepared_fields = await self.data_preparer.prepare_for_update(
                            model=UserStorage,
                            fields={'value': value},
                            json_fields=[]
                        )
                        stmt = update(UserStorage).where(
                            UserStorage.tenant_id == tenant_id,
                            UserStorage.user_id == user_id,
                            UserStorage.key == key
                        ).values(**prepared_fields)
                        session.execute(stmt)
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error setting storage records: {e}")
            return None
    
    async def delete_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None) -> Optional[int]:
        """
        Universal delete storage records
        
        Logic:
        - If key or key_pattern specified - delete records with specified keys
        - If key and key_pattern not specified - delete all user records
        
        Returns number of deleted records
        """
        try:
            with self._get_session() as session:
                conditions = [
                    UserStorage.tenant_id == tenant_id,
                    UserStorage.user_id == user_id
                ]
                
                # Key: if exact value exists - use it, otherwise pattern
                if key:
                    conditions.append(UserStorage.key == key)
                elif key_pattern:
                    conditions.append(UserStorage.key.ilike(key_pattern))
                
                stmt = delete(UserStorage).where(*conditions)
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Error deleting storage records: {e}")
            return None
    
    async def get_by_tenant_and_key(self, tenant_id: int, key: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all storage records for tenant by key
        Uses idx_user_storage_tenant_key index for fast search
        Values are converted to required types (int, float, bool, list or str)
        
        Used for finding users by value (find_users_by_storage_value)
        """
        try:
            with self._get_session() as session:
                stmt = select(UserStorage).where(
                    UserStorage.tenant_id == tenant_id,
                    UserStorage.key == key
                )
                result = session.execute(stmt).scalars().all()
                
                # Convert value automatically via convert_text_fields
                return await self._to_dict_list(result, convert_text_fields=['value'])
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting records by key {key}: {e}")
            return None
