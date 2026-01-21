"""
Repository for working with unique ID generator (id_sequence)
"""

from typing import Any, Dict, Optional

from sqlalchemy import insert, select

from ..models import IdSequence
from .base import BaseRepository


class IdSequenceRepository(BaseRepository):
    """
    Repository for working with unique ID generator
    """
    
    async def get_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """
        Get record by hash
        """
        try:
            with self._get_session() as session:
                stmt = select(IdSequence).where(IdSequence.hash == hash_value)
                result = session.execute(stmt).scalar_one_or_none()
                
                if result:
                    return await self._to_dict(result)
                else:
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting record by hash {hash_value}: {e}")
            return None
    
    async def get_id_by_hash(self, hash_value: str) -> Optional[int]:
        """
        Get ID by hash (fast method, returns only ID)
        """
        try:
            with self._get_session() as session:
                stmt = select(IdSequence.id).where(IdSequence.hash == hash_value)
                result = session.execute(stmt).scalar_one_or_none()
                
                return result if result else None
                    
        except Exception:
            # If record not found, it's normal - return None
            return None
    
    async def create(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """
        Create new record with unique ID
        Returns created ID
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=IdSequence,
                    fields={
                        'hash': hash_value,
                        'seed': seed
                    },
                    json_fields=[]
                )
                
                stmt = insert(IdSequence).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                return result.inserted_primary_key[0] if result.inserted_primary_key else None
                
        except Exception as e:
            self.logger.error(f"Error creating id_sequence record with hash {hash_value}: {e}")
            return None
    
    async def get_or_create(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """
        Get existing ID by hash or create new record
        Returns unique ID
        """
        try:
            # First try to find existing record
            existing_id = await self.get_id_by_hash(hash_value)
            
            if existing_id is not None:
                return existing_id
            
            # Record not found - create new
            return await self.create(hash_value, seed)
            
        except Exception as e:
            self.logger.error(f"Error get_or_create for hash {hash_value}: {e}")
            return None
