"""
Репозиторий для работы с векторным хранилищем (vector_storage)
"""

import json
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy import delete, insert, literal, select, text, update

from ..models import VectorStorage
from .base import BaseRepository


class VectorStorageRepository(BaseRepository):
    """
    Репозиторий для работы с векторным хранилищем (RAG)
    """
    
    async def get_chunks_by_document(self, tenant_id: int, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Получить все чанки документа по document_id
        """
        try:
            with self._get_session() as session:
                stmt = select(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_id == document_id
                ).order_by(VectorStorage.chunk_index)
                
                result = session.execute(stmt).scalars().all()
                return await self._to_dict_list(result)  # JSONB обрабатывается автоматически SQLAlchemy
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения чанков документа {document_id}: {e}")
            return None
    
    async def get_chunks_by_type(self, tenant_id: int, document_type: str, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Получить чанки по типу документа
        """
        try:
            with self._get_session() as session:
                stmt = select(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_type == document_type
                ).order_by(VectorStorage.document_id, VectorStorage.chunk_index)
                
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                return await self._to_dict_list(result)  # JSONB обрабатывается автоматически SQLAlchemy
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения чанков типа {document_type}: {e}")
            return None
    
    async def get_recent_chunks(self, tenant_id: int, limit: int, document_type: Optional[List[str]] = None,
                                document_id: Optional[List[str]] = None, until_date=None, since_date=None,
                                metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Получить последние N чанков по дате created_at (сортировка по убыванию)
        Используется created_at для правильной сортировки истории.
        
        Многоуровневая сортировка для детерминированности:
        1. created_at DESC (основной уровень)
        2. processed_at DESC (второй уровень - для чанков с одинаковым created_at)
        3. chunk_index ASC (третий уровень - для правильного порядка чанков в документе)
        4. document_id ASC (четвертый уровень - для полной детерминированности)
        """
        try:
            with self._get_session() as session:
                # Базовые условия
                conditions = [VectorStorage.tenant_id == tenant_id]
                
                # Фильтр по document_type
                if document_type:
                    if isinstance(document_type, str):
                        conditions.append(VectorStorage.document_type == document_type)
                    elif isinstance(document_type, list) and document_type:
                        conditions.append(VectorStorage.document_type.in_(document_type))
                
                # Фильтр по document_id
                if document_id:
                    if isinstance(document_id, str):
                        conditions.append(VectorStorage.document_id == document_id)
                    elif isinstance(document_id, list) and document_id:
                        conditions.append(VectorStorage.document_id.in_(document_id))
                
                # Фильтр по дате processed_at (включительно)
                if until_date is not None:
                    conditions.append(VectorStorage.processed_at <= until_date)
                
                if since_date is not None:
                    conditions.append(VectorStorage.processed_at >= since_date)
                
                # Фильтр по метаданным (JSONB)
                if metadata_filter:
                    metadata_json = json.dumps(metadata_filter)
                    conditions.append(
                        VectorStorage.chunk_metadata.op('@>')(text(f"'{metadata_json}'::jsonb"))
                    )
                
                stmt = select(
                    VectorStorage.content,
                    VectorStorage.document_id,
                    VectorStorage.chunk_index,
                    VectorStorage.document_type,
                    VectorStorage.role,
                    VectorStorage.chunk_metadata,
                    VectorStorage.embedding_model,
                    VectorStorage.created_at,
                    VectorStorage.processed_at
                ).where(
                    *conditions
                ).order_by(
                    VectorStorage.created_at.desc(),  # Основная сортировка по created_at (новые первыми)
                    VectorStorage.processed_at.desc(),  # Второй уровень: по processed_at (новые первыми)
                    VectorStorage.chunk_index.asc(),  # Третий уровень: по chunk_index (по возрастанию)
                    VectorStorage.document_id.asc()  # Четвертый уровень: по document_id (по возрастанию) для детерминированности
                ).limit(limit)
                
                result = session.execute(stmt).all()
                
                # Формируем результат
                chunks = []
                for row in result:
                    chunks.append({
                        "content": row.content,
                        "document_id": row.document_id,
                        "chunk_index": row.chunk_index,
                        "document_type": row.document_type,
                        "role": row.role,
                        "chunk_metadata": row.chunk_metadata,
                        "embedding_model": row.embedding_model,
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                        "processed_at": row.processed_at.isoformat() if row.processed_at else None
                    })
                
                return chunks
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения последних чанков: {e}")
            return None
    
    async def delete_document(self, tenant_id: int, document_id: str) -> Optional[int]:
        """
        Удалить все чанки документа по document_id
        Возвращает количество удаленных чанков
        """
        try:
            with self._get_session() as session:
                stmt = delete(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_id == document_id
                )
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка удаления документа {document_id}: {e}")
            return None
    
    async def delete_by_date(self, tenant_id: int, until_date=None, since_date=None,
                            metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Удалить чанки по дате processed_at
        Можно указать since_date (удалить с даты включительно) или until_date (удалить до даты включительно), или оба
        Также можно указать metadata_filter для фильтрации по метаданным
        """
        try:
            with self._get_session() as session:
                conditions = [VectorStorage.tenant_id == tenant_id]
                
                if until_date is not None:
                    conditions.append(VectorStorage.processed_at <= until_date)
                
                if since_date is not None:
                    conditions.append(VectorStorage.processed_at >= since_date)
                
                # Фильтр по метаданным (JSONB)
                if metadata_filter:
                    metadata_json = json.dumps(metadata_filter)
                    conditions.append(
                        VectorStorage.chunk_metadata.op('@>')(text(f"'{metadata_json}'::jsonb"))
                    )
                
                if until_date is None and since_date is None and not metadata_filter:
                    self.logger.error("Необходимо указать хотя бы один параметр: until_date, since_date или metadata_filter")
                    return None
                
                stmt = delete(VectorStorage).where(*conditions)
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка удаления по дате: {e}")
            return None
    
    async def create_chunk(self, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """
        Создать чанк документа
        Возвращает True при успешном создании
        """
        try:
            with self._get_session() as session:
                fields_dict = {
                    'tenant_id': chunk_data.get('tenant_id'),
                    'document_id': chunk_data.get('document_id'),
                    'document_type': chunk_data.get('document_type'),
                    'role': chunk_data.get('role', 'user'),  # По умолчанию 'user'
                    'chunk_index': chunk_data.get('chunk_index'),
                    'content': chunk_data.get('content'),
                    'embedding': chunk_data.get('embedding'),
                    'embedding_model': chunk_data.get('embedding_model'),  # Модель для генерации embedding
                    'chunk_metadata': chunk_data.get('chunk_metadata'),  # Метаданные (JSONB)
                    'created_at': chunk_data.get('created_at')  # Всегда явно устанавливаем для единообразия (если передан)
                }
                
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=VectorStorage,
                    fields=fields_dict,
                    json_fields=['chunk_metadata']  # JSONB поле
                )
                
                stmt = insert(VectorStorage).values(**prepared_fields)
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка создания чанка: {e}")
            return None
    
    async def create_chunks_batch(self, chunks_data: List[Dict[str, Any]]) -> Optional[int]:
        """
        Создать несколько чанков одним запросом (batch insert)
        Возвращает количество созданных чанков
        """
        try:
            if not chunks_data:
                return 0
            
            with self._get_session() as session:
                prepared_inserts = []
                for chunk_data in chunks_data:
                    fields_dict = {
                        'tenant_id': chunk_data.get('tenant_id'),
                        'document_id': chunk_data.get('document_id'),
                        'document_type': chunk_data.get('document_type'),
                        'role': chunk_data.get('role', 'user'),  # По умолчанию 'user'
                        'chunk_index': chunk_data.get('chunk_index'),
                        'content': chunk_data.get('content'),
                        'embedding': chunk_data.get('embedding'),
                        'embedding_model': chunk_data.get('embedding_model'),  # Модель для генерации embedding
                        'chunk_metadata': chunk_data.get('chunk_metadata'),  # Метаданные (JSONB)
                        'created_at': chunk_data.get('created_at')  # Всегда явно устанавливаем для единообразия (если передан)
                    }
                    
                    prepared_fields = await self.data_preparer.prepare_for_insert(
                        model=VectorStorage,
                        fields=fields_dict,
                        json_fields=['chunk_metadata']  # JSONB поле
                    )
                    prepared_inserts.append(prepared_fields)
                
                if prepared_inserts:
                    session.execute(insert(VectorStorage), prepared_inserts)
                    session.commit()
                    
                    return len(prepared_inserts)
                else:
                    return 0
                
        except Exception as e:
            self.logger.error(f"Ошибка batch создания чанков: {e}")
            return None
    
    async def get_chunk(self, tenant_id: int, document_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """
        Получить чанк по составному ключу (tenant_id, document_id, chunk_index)
        """
        try:
            with self._get_session() as session:
                stmt = select(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_id == document_id,
                    VectorStorage.chunk_index == chunk_index
                )
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)  # JSONB обрабатывается автоматически SQLAlchemy
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения чанка {document_id}[{chunk_index}]: {e}")
            return None
    
    async def update_chunk(self, tenant_id: int, document_id: str, chunk_index: int, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """
        Обновить чанк по составному ключу (tenant_id, document_id, chunk_index)
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=VectorStorage,
                    fields={
                        'content': chunk_data.get('content'),
                        'embedding': chunk_data.get('embedding'),
                        'embedding_model': chunk_data.get('embedding_model')  # Модель для генерации embedding
                    },
                    json_fields=[]  # JSONB обрабатывается автоматически SQLAlchemy
                )
                
                stmt = update(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_id == document_id,
                    VectorStorage.chunk_index == chunk_index
                ).values(**prepared_fields)
                
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка обновления чанка {document_id}[{chunk_index}]: {e}")
            return None
    
    async def search_similar(self, tenant_id: int, query_vector: List[float], limit: int = 5,
                            min_similarity: float = 0.7, document_type: Optional[List[str]] = None,
                            document_id: Optional[List[str]] = None, until_date=None, since_date=None,
                            metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Поиск похожих чанков по вектору (cosine similarity)
        """
        try:
            from sqlalchemy import text
            
            with self._get_session() as session:
                # pgvector использует оператор <=> для cosine distance
                # similarity = 1 - (embedding <=> query_vector)
                # embedding действие возвращает готовый список Python, передаем его напрямую
                
                # Базовые условия
                conditions = [VectorStorage.tenant_id == tenant_id]
                
                # Фильтр по document_type
                if document_type:
                    if isinstance(document_type, str):
                        conditions.append(VectorStorage.document_type == document_type)
                    elif isinstance(document_type, list) and document_type:
                        conditions.append(VectorStorage.document_type.in_(document_type))
                
                # Фильтр по document_id
                if document_id:
                    if isinstance(document_id, str):
                        conditions.append(VectorStorage.document_id == document_id)
                    elif isinstance(document_id, list) and document_id:
                        conditions.append(VectorStorage.document_id.in_(document_id))
                
                # Фильтр по дате created_at (включительно) - используем created_at для правильной сортировки
                if until_date is not None:
                    conditions.append(VectorStorage.created_at <= until_date)
                
                if since_date is not None:
                    conditions.append(VectorStorage.created_at >= since_date)
                
                # Фильтр по метаданным (JSONB)
                if metadata_filter:
                    # Используем оператор @> для проверки наличия ключей и значений в JSONB
                    # Это работает быстрее и поддерживает индексы
                    metadata_json = json.dumps(metadata_filter)
                    conditions.append(
                        VectorStorage.chunk_metadata.op('@>')(text(f"'{metadata_json}'::jsonb"))
                    )
                
                # Фильтр: только записи с не-null embedding (для векторного поиска)
                conditions.append(VectorStorage.embedding.isnot(None))
                
                # Поиск по cosine similarity
                # Используем SQL выражение для вычисления similarity
                # 1 - (embedding <=> query_vector) = cosine similarity
                # 
                # РЕШЕНИЕ: Используем нативные конструкции SQLAlchemy с типом Vector
                # вместо text() и bindparam() - это обеспечивает правильную генерацию SQL
                # и поддержку .label() для создания алиаса
                
                # Преобразуем Python список в pgvector Vector через literal()
                # literal() создает SQL литерал из Python значения, которое pgvector может обработать
                # Используем PgVector для правильного преобразования списка в векторный тип
                query_vec_expr = literal(query_vector, type_=PgVector(1024))
                
                # Создаем выражение similarity используя оператор <=> через .op()
                # Используем literal(1) для литерального значения 1, чтобы оно не стало параметром
                similarity_expr = literal(1) - (VectorStorage.embedding.op('<=>')(query_vec_expr))
                
                stmt = select(
                    VectorStorage.content,
                    VectorStorage.document_id,
                    VectorStorage.chunk_index,
                    VectorStorage.document_type,
                    VectorStorage.role,
                    VectorStorage.chunk_metadata,
                    VectorStorage.embedding_model,
                    VectorStorage.created_at,
                    VectorStorage.processed_at,
                    similarity_expr.label('similarity')  # Теперь .label() работает корректно
                ).where(
                    *conditions
                ).order_by(
                    similarity_expr.desc()  # Используем то же выражение для сортировки
                ).limit(limit)
                
                # Выполняем запрос (query_vector уже преобразован в вектор через cast)
                result = session.execute(stmt).all()
                
                # Формируем результат (фильтрация по min_similarity уже выполнена в SQL)
                chunks = []
                for row in result:
                    similarity = float(row.similarity)
                    # Дополнительная проверка на всякий случай (должна быть избыточной)
                    if similarity >= min_similarity:
                        chunks.append({
                            "content": row.content,
                            "document_id": row.document_id,
                            "chunk_index": row.chunk_index,
                            "document_type": row.document_type,
                            "role": row.role,
                            "chunk_metadata": row.chunk_metadata,
                            "embedding_model": row.embedding_model,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                            "processed_at": row.processed_at.isoformat() if row.processed_at else None,
                            "similarity": round(similarity, 4)  # Округляем до 4 знаков
                        })
                
                return chunks
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка поиска похожих чанков: {e}")
            return None

