"""
Repository for working with tenant data storage (tenant_storage)
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, distinct, insert, select, update

from ..models import TenantStorage
from .base import BaseRepository


class TenantStorageRepository(BaseRepository):
    """
    Repository for working with tenant data storage
    """
    
    async def get_records(
        self,
        tenant_id: int,
        group_key: Optional[str] = None,
        group_key_pattern: Optional[str] = None,
        key: Optional[str] = None,
        key_pattern: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Universal get storage records
        
        Mode determination logic:
        - If all parameters None - get all tenant records
        - If only group_key/group_key_pattern specified - get group/groups
        - If group_key/pattern + key/pattern specified - get value/values
        
        Values are converted to required types (int, float, bool, list, dict or str)
        
        limit: optional limit on number of returned records
        """
        try:
            with self._get_session() as session:
                conditions = [TenantStorage.tenant_id == tenant_id]
                
                # Group: if exact value exists - use it, otherwise pattern
                if group_key:
                    conditions.append(TenantStorage.group_key == group_key)
                elif group_key_pattern:
                    conditions.append(TenantStorage.group_key.ilike(group_key_pattern))
                
                # Key: if exact value exists - use it, otherwise pattern
                # Convert key to string, as key has String type in DB
                if key:
                    conditions.append(TenantStorage.key == str(key))
                elif key_pattern:
                    conditions.append(TenantStorage.key.ilike(key_pattern))
                
                stmt = select(TenantStorage).where(*conditions)
                
                # Apply limit if specified
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                
                # Convert value automatically via convert_text_fields
                return await self._to_dict_list(result, convert_text_fields=['value'])
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting storage records: {e}")
            return None
    
    async def delete_records(
        self,
        tenant_id: int,
        group_key: Optional[str] = None,
        group_key_pattern: Optional[str] = None,
        key: Optional[str] = None,
        key_pattern: Optional[str] = None
    ) -> Optional[int]:
        """
        Universal delete storage records
        
        Logic:
        - If key or key_pattern specified - delete values (records with specified keys)
        - If key/key_pattern not specified, but group_key/pattern specified - delete groups (all group records)
        - If all parameters None - delete all tenant records
        
        Returns number of deleted records
        """
        try:
            with self._get_session() as session:
                conditions = [TenantStorage.tenant_id == tenant_id]
                
                # Group: if exact value exists - use it, otherwise pattern
                if group_key:
                    conditions.append(TenantStorage.group_key == group_key)
                elif group_key_pattern:
                    conditions.append(TenantStorage.group_key.ilike(group_key_pattern))
                
                # Key: if exact value exists - use it, otherwise pattern
                # Convert key to string, as key has String type in DB
                if key:
                    conditions.append(TenantStorage.key == str(key))
                elif key_pattern:
                    conditions.append(TenantStorage.key.ilike(key_pattern))
                
                stmt = delete(TenantStorage).where(*conditions)
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error deleting storage records: {e}")
            return None
    
    async def set_records(
        self,
        tenant_id: int,
        values: Dict[str, Dict[str, Any]]
    ) -> Optional[bool]:
        """
        Universal set storage records (batch for all groups)
        
        Accepts structure {group_key: {key: value}} for setting one or multiple values
        Optimized version: first get all existing records with one query,
        then perform batch insert/update
        """
        try:
            if not values:
                return True  # No data to set
            
            with self._get_session() as session:
                # Collect all keys for existence check
                all_keys_to_check = []
                for group_key, group_data in values.items():
                    for key in group_data.keys():
                        all_keys_to_check.append((group_key, key))
                
                # Get all existing records with one query
                existing_records = set()
                if all_keys_to_check:
                    # Build conditions for all combinations of tenant_id + group_key + key
                    from sqlalchemy import or_
                    combined_conditions = []
                    
                    for group_key, key in all_keys_to_check:
                        # Convert key to string, as key has String type in DB
                        combined_conditions.append(
                            (TenantStorage.tenant_id == tenant_id) &
                            (TenantStorage.group_key == str(group_key)) & 
                            (TenantStorage.key == str(key))
                        )
                    
                    if combined_conditions:
                        conditions = [or_(*combined_conditions)]
                        
                        existing = session.execute(
                            select(TenantStorage.tenant_id, TenantStorage.group_key, TenantStorage.key).where(*conditions)
                        ).all()
                        existing_records = {(r.tenant_id, r.group_key, r.key) for r in existing}
                
                # Split into insert and update
                to_insert = []
                to_update = []
                
                for group_key, group_data in values.items():
                    for key, value in group_data.items():
                        # Convert key to string for comparison and saving, as key has String type in DB
                        key_str = str(key)
                        group_key_str = str(group_key)
                        if (tenant_id, group_key_str, key_str) in existing_records:
                            to_update.append((group_key_str, key_str, value))
                        else:
                            to_insert.append({
                                'tenant_id': tenant_id,
                                'group_key': group_key_str,
                                'key': key_str,
                                'value': value
                            })
                
                # Batch insert for new records
                if to_insert:
                    prepared_inserts = []
                    for record in to_insert:
                        prepared_fields = await self.data_preparer.prepare_for_insert(
                            model=TenantStorage,
                            fields=record,
                            json_fields=[]
                        )
                        prepared_inserts.append(prepared_fields)
                    
                    if prepared_inserts:
                        session.execute(insert(TenantStorage), prepared_inserts)
                
                # Batch update for existing records
                if to_update:
                    for group_key, key, value in to_update:
                        prepared_fields = await self.data_preparer.prepare_for_update(
                            model=TenantStorage,
                            fields={'value': value},
                            json_fields=[]
                        )
                        # Convert key and group_key to strings, as they have String type in DB
                        stmt = update(TenantStorage).where(
                            TenantStorage.tenant_id == tenant_id,
                            TenantStorage.group_key == str(group_key),
                            TenantStorage.key == str(key)
                        ).values(**prepared_fields)
                        session.execute(stmt)
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error setting storage records: {e}")
            return None
    
    async def delete_groups_batch(self, tenant_id: int, group_keys: List[str]) -> Optional[int]:
        """
        Batch delete multiple groups with one query
        
        Optimized deletion: deletes all specified groups with one SQL query
        instead of multiple separate queries.
        
        Returns number of deleted records
        """
        try:
            if not group_keys:
                return 0
            
            with self._get_session() as session:
                from sqlalchemy import or_
                
                # Build OR conditions for all groups
                group_conditions = [
                    TenantStorage.group_key == group_key 
                    for group_key in group_keys
                ]
                
                if group_conditions:
                    conditions = [
                        TenantStorage.tenant_id == tenant_id,
                        or_(*group_conditions)
                    ]
                    
                    stmt = delete(TenantStorage).where(*conditions)
                    result = session.execute(stmt)
                    session.commit()
                    
                    return result.rowcount
                else:
                    return 0
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error batch deleting storage groups: {e}")
            return None
    
    async def get_group_keys(self, tenant_id: int, limit: Optional[int] = None) -> Optional[List[str]]:
        """
        Get list of unique group keys for tenant
        
        Returns list of all unique group_key for specified tenant_id
        limit: optional limit on number of returned groups
        """
        try:
            with self._get_session() as session:
                stmt = select(distinct(TenantStorage.group_key)).where(
                    TenantStorage.tenant_id == tenant_id
                ).order_by(TenantStorage.group_key)
                
                # Apply limit if specified
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                return list(result) if result else []
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting storage group keys list: {e}")
            return None
