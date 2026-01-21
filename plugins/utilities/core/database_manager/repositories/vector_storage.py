"""
Repository for working with vector storage (vector_storage)
"""

import json
from typing import Any, Dict, List, Optional

from pgvector.sqlalchemy import Vector as PgVector
from sqlalchemy import delete, insert, literal, select, text, update

from ..models import VectorStorage
from .base import BaseRepository


class VectorStorageRepository(BaseRepository):
    """
    Repository for working with vector storage (RAG)
    """
    
    async def get_chunks_by_document(self, tenant_id: int, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all document chunks by document_id
        """
        try:
            with self._get_session() as session:
                stmt = select(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_id == document_id
                ).order_by(VectorStorage.chunk_index)
                
                result = session.execute(stmt).scalars().all()
                return await self._to_dict_list(result)  # JSONB is automatically handled by SQLAlchemy
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting document chunks {document_id}: {e}")
            return None
    
    async def get_chunks_by_type(self, tenant_id: int, document_type: str, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get chunks by document type
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
                return await self._to_dict_list(result)  # JSONB is automatically handled by SQLAlchemy
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting chunks of type {document_type}: {e}")
            return None
    
    async def get_recent_chunks(self, tenant_id: int, limit: int, document_type: Optional[List[str]] = None,
                                document_id: Optional[List[str]] = None, until_date=None, since_date=None,
                                metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get last N chunks by created_at date (descending sort)
        Uses created_at for correct history sorting.
        
        Multi-level sorting for determinism:
        1. created_at DESC (primary level)
        2. processed_at DESC (second level - for chunks with same created_at)
        3. chunk_index ASC (third level - for correct chunk order in document)
        4. document_id ASC (fourth level - for full determinism)
        """
        try:
            with self._get_session() as session:
                # Base conditions
                conditions = [VectorStorage.tenant_id == tenant_id]
                
                # Filter by document_type
                if document_type:
                    if isinstance(document_type, str):
                        conditions.append(VectorStorage.document_type == document_type)
                    elif isinstance(document_type, list) and document_type:
                        conditions.append(VectorStorage.document_type.in_(document_type))
                
                # Filter by document_id
                if document_id:
                    if isinstance(document_id, str):
                        conditions.append(VectorStorage.document_id == document_id)
                    elif isinstance(document_id, list) and document_id:
                        conditions.append(VectorStorage.document_id.in_(document_id))
                
                # Filter by processed_at date (inclusive)
                if until_date is not None:
                    conditions.append(VectorStorage.processed_at <= until_date)
                
                if since_date is not None:
                    conditions.append(VectorStorage.processed_at >= since_date)
                
                # Filter by metadata (JSONB)
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
                    VectorStorage.created_at.desc(),  # Primary sort by created_at (newest first)
                    VectorStorage.processed_at.desc(),  # Second level: by processed_at (newest first)
                    VectorStorage.chunk_index.asc(),  # Third level: by chunk_index (ascending)
                    VectorStorage.document_id.asc()  # Fourth level: by document_id (ascending) for determinism
                ).limit(limit)
                
                result = session.execute(stmt).all()
                
                # Form result
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
            self.logger.error(f"[Tenant-{tenant_id}] Error getting recent chunks: {e}")
            return None
    
    async def delete_document(self, tenant_id: int, document_id: str) -> Optional[int]:
        """
        Delete all document chunks by document_id
        Returns number of deleted chunks
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
            self.logger.error(f"[Tenant-{tenant_id}] Error deleting document {document_id}: {e}")
            return None
    
    async def delete_by_date(self, tenant_id: int, until_date=None, since_date=None,
                            metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """
        Delete chunks by processed_at date
        Can specify since_date (delete from date inclusive) or until_date (delete until date inclusive), or both
        Can also specify metadata_filter for filtering by metadata
        """
        try:
            with self._get_session() as session:
                conditions = [VectorStorage.tenant_id == tenant_id]
                
                if until_date is not None:
                    conditions.append(VectorStorage.processed_at <= until_date)
                
                if since_date is not None:
                    conditions.append(VectorStorage.processed_at >= since_date)
                
                # Filter by metadata (JSONB)
                if metadata_filter:
                    metadata_json = json.dumps(metadata_filter)
                    conditions.append(
                        VectorStorage.chunk_metadata.op('@>')(text(f"'{metadata_json}'::jsonb"))
                    )
                
                if until_date is None and since_date is None and not metadata_filter:
                    self.logger.error("Must specify at least one parameter: until_date, since_date or metadata_filter")
                    return None
                
                stmt = delete(VectorStorage).where(*conditions)
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error deleting by date: {e}")
            return None
    
    async def create_chunk(self, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """
        Create document chunk
        Returns True on successful creation
        """
        try:
            with self._get_session() as session:
                fields_dict = {
                    'tenant_id': chunk_data.get('tenant_id'),
                    'document_id': chunk_data.get('document_id'),
                    'document_type': chunk_data.get('document_type'),
                    'role': chunk_data.get('role', 'user'),  # Default 'user'
                    'chunk_index': chunk_data.get('chunk_index'),
                    'content': chunk_data.get('content'),
                    'embedding': chunk_data.get('embedding'),
                    'embedding_model': chunk_data.get('embedding_model'),  # Model for embedding generation
                    'chunk_metadata': chunk_data.get('chunk_metadata'),  # Metadata (JSONB)
                    'created_at': chunk_data.get('created_at')  # Always explicitly set for consistency (if provided)
                }
                
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=VectorStorage,
                    fields=fields_dict,
                    json_fields=['chunk_metadata']  # JSONB field
                )
                
                stmt = insert(VectorStorage).values(**prepared_fields)
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error creating chunk: {e}")
            return None
    
    async def create_chunks_batch(self, chunks_data: List[Dict[str, Any]]) -> Optional[int]:
        """
        Create multiple chunks with one query (batch insert)
        Returns number of created chunks
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
                        'role': chunk_data.get('role', 'user'),  # Default 'user'
                        'chunk_index': chunk_data.get('chunk_index'),
                        'content': chunk_data.get('content'),
                        'embedding': chunk_data.get('embedding'),
                        'embedding_model': chunk_data.get('embedding_model'),  # Model for embedding generation
                        'chunk_metadata': chunk_data.get('chunk_metadata'),  # Metadata (JSONB)
                        'created_at': chunk_data.get('created_at')  # Always explicitly set for consistency (if provided)
                    }
                    
                    prepared_fields = await self.data_preparer.prepare_for_insert(
                        model=VectorStorage,
                        fields=fields_dict,
                        json_fields=['chunk_metadata']  # JSONB field
                    )
                    prepared_inserts.append(prepared_fields)
                
                if prepared_inserts:
                    session.execute(insert(VectorStorage), prepared_inserts)
                    session.commit()
                    
                    return len(prepared_inserts)
                else:
                    return 0
                
        except Exception as e:
            self.logger.error(f"Error batch creating chunks: {e}")
            return None
    
    async def get_chunk(self, tenant_id: int, document_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """
        Get chunk by composite key (tenant_id, document_id, chunk_index)
        """
        try:
            with self._get_session() as session:
                stmt = select(VectorStorage).where(
                    VectorStorage.tenant_id == tenant_id,
                    VectorStorage.document_id == document_id,
                    VectorStorage.chunk_index == chunk_index
                )
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)  # JSONB is automatically handled by SQLAlchemy
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting chunk {document_id}[{chunk_index}]: {e}")
            return None
    
    async def update_chunk(self, tenant_id: int, document_id: str, chunk_index: int, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """
        Update chunk by composite key (tenant_id, document_id, chunk_index)
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=VectorStorage,
                    fields={
                        'content': chunk_data.get('content'),
                        'embedding': chunk_data.get('embedding'),
                        'embedding_model': chunk_data.get('embedding_model')  # Model for embedding generation
                    },
                    json_fields=[]  # JSONB is automatically handled by SQLAlchemy
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
            self.logger.error(f"[Tenant-{tenant_id}] Error updating chunk {document_id}[{chunk_index}]: {e}")
            return None
    
    async def search_similar(self, tenant_id: int, query_vector: List[float], limit: int = 5,
                            min_similarity: float = 0.7, document_type: Optional[List[str]] = None,
                            document_id: Optional[List[str]] = None, until_date=None, since_date=None,
                            metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Search similar chunks by vector (cosine similarity)
        """
        try:
            from sqlalchemy import text
            
            with self._get_session() as session:
                # pgvector uses <=> operator for cosine distance
                # similarity = 1 - (embedding <=> query_vector)
                # embedding action returns ready Python list, pass it directly
                
                # Base conditions
                conditions = [VectorStorage.tenant_id == tenant_id]
                
                # Filter by document_type
                if document_type:
                    if isinstance(document_type, str):
                        conditions.append(VectorStorage.document_type == document_type)
                    elif isinstance(document_type, list) and document_type:
                        conditions.append(VectorStorage.document_type.in_(document_type))
                
                # Filter by document_id
                if document_id:
                    if isinstance(document_id, str):
                        conditions.append(VectorStorage.document_id == document_id)
                    elif isinstance(document_id, list) and document_id:
                        conditions.append(VectorStorage.document_id.in_(document_id))
                
                # Filter by created_at date (inclusive) - use created_at for correct sorting
                if until_date is not None:
                    conditions.append(VectorStorage.created_at <= until_date)
                
                if since_date is not None:
                    conditions.append(VectorStorage.created_at >= since_date)
                
                # Filter by metadata (JSONB)
                if metadata_filter:
                    # Use @> operator to check for keys and values in JSONB
                    # This works faster and supports indexes
                    metadata_json = json.dumps(metadata_filter)
                    conditions.append(
                        VectorStorage.chunk_metadata.op('@>')(text(f"'{metadata_json}'::jsonb"))
                    )
                
                # Filter: only records with non-null embedding (for vector search)
                conditions.append(VectorStorage.embedding.isnot(None))
                
                # Search by cosine similarity
                # Use SQL expression to calculate similarity
                # 1 - (embedding <=> query_vector) = cosine similarity
                # 
                # SOLUTION: Use native SQLAlchemy constructs with Vector type
                # instead of text() and bindparam() - this ensures correct SQL generation
                # and support for .label() to create alias
                
                # Convert Python list to pgvector Vector via literal()
                # literal() creates SQL literal from Python value that pgvector can process
                # Use PgVector for correct list to vector type conversion
                query_vec_expr = literal(query_vector, type_=PgVector(1024))
                
                # Create similarity expression using <=> operator via .op()
                # Use literal(1) for literal value 1 so it doesn't become a parameter
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
                    similarity_expr.label('similarity')  # Now .label() works correctly
                ).where(
                    *conditions
                ).order_by(
                    similarity_expr.desc()  # Use same expression for sorting
                ).limit(limit)
                
                # Execute query (query_vector already converted to vector via cast)
                result = session.execute(stmt).all()
                
                # Form result (filtering by min_similarity already done in SQL)
                chunks = []
                for row in result:
                    similarity = float(row.similarity)
                    # Additional check just in case (should be redundant)
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
                            "similarity": round(similarity, 4)  # Round to 4 decimal places
                        })
                
                return chunks
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error searching similar chunks: {e}")
            return None

