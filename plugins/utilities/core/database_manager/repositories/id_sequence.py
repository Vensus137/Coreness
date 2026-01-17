"""
Репозиторий для работы с генератором уникальных ID (id_sequence)
"""

from typing import Any, Dict, Optional

from sqlalchemy import insert, select

from ..models import IdSequence
from .base import BaseRepository


class IdSequenceRepository(BaseRepository):
    """
    Репозиторий для работы с генератором уникальных ID
    """
    
    async def get_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """
        Получение записи по хэшу
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
            self.logger.error(f"Ошибка получения записи по хэшу {hash_value}: {e}")
            return None
    
    async def get_id_by_hash(self, hash_value: str) -> Optional[int]:
        """
        Получение ID по хэшу (быстрый метод, возвращает только ID)
        """
        try:
            with self._get_session() as session:
                stmt = select(IdSequence.id).where(IdSequence.hash == hash_value)
                result = session.execute(stmt).scalar_one_or_none()
                
                return result if result else None
                    
        except Exception:
            # Если запись не найдена, это нормально - возвращаем None
            return None
    
    async def create(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """
        Создание новой записи с уникальным ID
        Возвращает созданный ID
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
            self.logger.error(f"Ошибка создания записи id_sequence с хэшем {hash_value}: {e}")
            return None
    
    async def get_or_create(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """
        Получить существующий ID по хэшу или создать новую запись
        Возвращает уникальный ID
        """
        try:
            # Сначала пытаемся найти существующую запись
            existing_id = await self.get_id_by_hash(hash_value)
            
            if existing_id is not None:
                return existing_id
            
            # Запись не найдена - создаем новую
            return await self.create(hash_value, seed)
            
        except Exception as e:
            self.logger.error(f"Ошибка get_or_create для хэша {hash_value}: {e}")
            return None
