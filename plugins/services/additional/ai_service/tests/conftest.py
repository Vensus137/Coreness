"""
Фикстуры для тестов ai_service
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(scope="module")
def logger():
    """Создает мок logger для тестов (scope=module для ускорения)"""
    return MagicMock()


@pytest.fixture
def mock_database_manager():
    """Создает мок DatabaseManager"""
    mock = MagicMock()
    mock.get_master_repository = MagicMock()
    return mock


@pytest.fixture
def mock_master_repository():
    """Создает мок MasterRepository"""
    mock = MagicMock()
    mock.create_chunks_batch = AsyncMock(return_value=2)  # Возвращает количество сохраненных чанков
    mock.get_chunks_by_document = AsyncMock(return_value=None)  # Нет существующих чанков
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
    """Создает мок AIClient"""
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
    """Создает мок TextProcessor"""
    mock = MagicMock()
    mock.clean_text = MagicMock(return_value="Cleaned text")
    mock.split_into_chunks = MagicMock(return_value=["Chunk 1", "Chunk 2"])
    return mock


@pytest.fixture
def mock_embedding_generator():
    """Создает мок EmbeddingGenerator"""
    mock = MagicMock()
    # generate_embeddings_parallel возвращает список результатов в формате {"result": "success", "response_data": {...}}
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
    """Создает мок IdGenerator"""
    mock = MagicMock()
    mock.get_or_create_unique_id = AsyncMock(return_value=12345)
    return mock


@pytest.fixture
def mock_task_manager():
    """Создает мок TaskManager"""
    mock = MagicMock()
    
    # submit_task возвращает Future с результатом или выполняет корутину сразу
    async def mock_submit_task(task_id, coro, queue_name, return_future=False):
        # Выполняем coroutine сразу (для тестов)
        result = await coro()
        
        if return_future:
            # Возвращаем простой Future с результатом
            future = asyncio.Future()
            future.set_result(result)
            return future
        return result
    
    mock.submit_task = AsyncMock(side_effect=mock_submit_task)
    return mock


@pytest.fixture
def mock_datetime_formatter():
    """Создает мок DateTimeFormatter"""
    mock = MagicMock()
    # now_local возвращает текущее локальное время (datetime объект)
    from datetime import datetime
    mock.now_local = AsyncMock(return_value=datetime(2024, 1, 1, 12, 0, 0))
    # parse_to_local парсит строку в локальное время
    mock.parse_to_local = AsyncMock(return_value=datetime(2024, 1, 1, 12, 0, 0))
    return mock


@pytest.fixture
def mock_settings():
    """Создает мок настроек"""
    return {
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "min_chunk_size": 50,
        "search_limit_chunks": 10,
        "search_min_similarity": 0.7
    }
