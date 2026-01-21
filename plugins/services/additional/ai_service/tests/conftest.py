"""
Fixtures for ai_service tests
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="module")
def logger():
    """Create mock logger for tests (scope=module for speed)"""
    return MagicMock()


@pytest.fixture
def mock_database_manager():
    """Create mock DatabaseManager"""
    mock = MagicMock()
    mock.get_master_repository = MagicMock()
    return mock


@pytest.fixture
def mock_master_repository():
    """Create mock MasterRepository"""
    mock = MagicMock()
    mock.create_chunks_batch = AsyncMock(return_value=2)  # Returns number of saved chunks
    mock.get_chunks_by_document = AsyncMock(return_value=None)  # No existing chunks
    mock.search_vector_storage_similar = AsyncMock(return_value=[
        {
            "content": "Test chunk 1",
            "document_id": "doc_1",
            "chunk_index": 0,
            "document_type": "knowledge",
            "role": "user",
            "similarity": 0.85,
            "created_at": "2024-01-01T00:00:00",
            "chunk_metadata": None
        }
    ])
    mock.get_recent_vector_storage_chunks = AsyncMock(return_value=[
        {
            "content": "Recent chunk",
            "document_id": "doc_1",
            "chunk_index": 0,
            "document_type": "chat_history",
            "role": "user",
            "created_at": "2024-01-01T00:00:00",
            "chunk_metadata": {"chat_id": 123}
        }
    ])
    mock.delete_document = AsyncMock(return_value=1)
    mock.delete_vector_storage_by_date = AsyncMock(return_value=2)
    return mock


@pytest.fixture
def mock_ai_client():
    """Create mock AIClient"""
    mock = MagicMock()
    mock.embedding = AsyncMock(return_value={
        "result": "success",
        "response_data": {
            "embedding": [0.1] * 1024,
            "model": "text-embedding-3-small",
            "total_tokens": 10
        }
    })
    return mock


@pytest.fixture
def mock_text_processor():
    """Create mock TextProcessor"""
    mock = MagicMock()
    mock.clean_text = MagicMock(return_value="Cleaned text")
    mock.split_into_chunks = MagicMock(return_value=["Chunk 1", "Chunk 2"])
    return mock


@pytest.fixture
def mock_embedding_generator():
    """Create mock EmbeddingGenerator"""
    mock = MagicMock()
    # generate_embeddings_parallel returns list of results in format {"result": "success", "response_data": {...}}
    mock.generate_embeddings_parallel = AsyncMock(return_value=[
        {
            "result": "success",
            "response_data": {
                "embedding": [0.1] * 1024,
                "model": "text-embedding-3-small",
                "total_tokens": 10
            }
        },
        {
            "result": "success",
            "response_data": {
                "embedding": [0.2] * 1024,
                "model": "text-embedding-3-small",
                "total_tokens": 10
            }
        }
    ])
    return mock


@pytest.fixture
def mock_id_generator():
    """Create mock IdGenerator"""
    mock = MagicMock()
    mock.get_or_create_unique_id = AsyncMock(return_value=12345)
    return mock


@pytest.fixture
def mock_task_manager():
    """Create mock TaskManager"""
    mock = MagicMock()
    
    # submit_task returns Future with result or executes coroutine immediately
    async def mock_submit_task(task_id, coro, queue_name, return_future=False):
        # Execute coroutine immediately (for tests)
        result = await coro()
        
        if return_future:
            # Return simple Future with result
            future = asyncio.Future()
            future.set_result(result)
            return future
        return result
    
    mock.submit_task = AsyncMock(side_effect=mock_submit_task)
    return mock


@pytest.fixture
def mock_datetime_formatter():
    """Create mock DateTimeFormatter"""
    mock = MagicMock()
    # now_local returns current local time (datetime object)
    from datetime import datetime
    mock.now_local = AsyncMock(return_value=datetime(2024, 1, 1, 12, 0, 0))
    # parse_to_local parses string to local time
    mock.parse_to_local = AsyncMock(return_value=datetime(2024, 1, 1, 12, 0, 0))
    return mock


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    return {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "min_chunk_size": 50,
        "search_limit_chunks": 10,
        "search_min_similarity": 0.7
    }
