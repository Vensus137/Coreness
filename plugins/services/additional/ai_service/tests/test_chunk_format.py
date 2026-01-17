"""
Тесты для функциональности chunk_format в ai_client
Проверяем корректность применения шаблонов с маркерами $ к чанкам
"""
from unittest.mock import MagicMock

import pytest

from plugins.utilities.ai.ai_client.ai_client import AIClient


@pytest.fixture(scope="module")
def ai_client():
    """Создает AIClient с моками один раз на модуль (для ускорения тестов)"""
    mock_logger = MagicMock()
    mock_settings_manager = MagicMock()
    mock_settings_manager.get_plugin_settings.return_value = {
        "api_key": "test_key",
        "base_url": "https://api.polza.ai/v1",
        "default_model": "test-model",
        "max_tokens": 200,
        "temperature": 0.7,
        "default_embedding_model": "text-embedding-3-small",
        "default_embedding_dimensions": 1024
    }
    
    mock_data_converter = MagicMock()
    
    client = AIClient(
        logger=mock_logger,
        settings_manager=mock_settings_manager,
        data_converter=mock_data_converter
    )
    
    return client


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ _apply_chunk_template - БАЗОВАЯ ФУНКЦИОНАЛЬНОСТЬ
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_apply_chunk_template_simple_content(ai_client):
    """Тест: Простая подстановка $content"""
    template = "$content"
    content = "Текст чанка"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Текст чанка"


@pytest.mark.unit
def test_apply_chunk_template_with_username(ai_client):
    """Тест: Подстановка username из chunk_metadata"""
    template = "[$username]: $content"
    content = "Привет!"
    chunk = {"chunk_metadata": {"username": "@john_doe"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john_doe]: Привет!"


@pytest.mark.unit
def test_apply_chunk_template_with_fallback(ai_client):
    """Тест: Использование fallback когда поле отсутствует"""
    template = "[$username|fallback:Пользователь]: $content"
    content = "Привет!"
    chunk = {"chunk_metadata": {}}  # username отсутствует
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь]: Привет!"


@pytest.mark.unit
def test_apply_chunk_template_fallback_with_empty_string(ai_client):
    """Тест: Fallback используется когда поле пустое"""
    template = "[$username|fallback:Пользователь]: $content"
    content = "Привет!"
    chunk = {"chunk_metadata": {"username": ""}}  # Пустая строка
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь]: Привет!"


@pytest.mark.unit
def test_apply_chunk_template_multiple_fields(ai_client):
    """Тест: Несколько полей из chunk_metadata"""
    template = "[$username] ($user_id): $content"
    content = "Сообщение"
    chunk = {"chunk_metadata": {"username": "@john_doe", "user_id": 12345}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john_doe] (12345): Сообщение"


@pytest.mark.unit
def test_apply_chunk_template_complex_format(ai_client):
    """Тест: Сложный формат с несколькими полями и fallback"""
    template = "[$username|fallback:Пользователь] ($user_id|fallback:Неизвестно): $content"
    content = "Текст сообщения"
    chunk = {"chunk_metadata": {"username": "@john_doe"}}  # user_id отсутствует
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john_doe] (Неизвестно): Текст сообщения"


@pytest.mark.unit
def test_apply_chunk_template_with_category(ai_client):
    """Тест: Использование category для knowledge чанков"""
    template = "[$category|fallback:База знаний] $content"
    content = "Документация по API"
    chunk = {"chunk_metadata": {"category": "DOCUMENTATION"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[DOCUMENTATION] Документация по API"


@pytest.mark.unit
def test_apply_chunk_template_with_version(ai_client):
    """Тест: Использование version в шаблоне"""
    template = "[$category] v$version: $content"
    content = "Описание функции"
    chunk = {"chunk_metadata": {"category": "API", "version": "1.2.3"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[API] v1.2.3: Описание функции"


@pytest.mark.unit
def test_apply_chunk_template_multiline_format(ai_client):
    """Тест: Многострочный формат"""
    template = "$content\n\n📎 Источник: $source|fallback:Неизвестно"
    content = "Текст чанка"
    chunk = {"chunk_metadata": {"source": "Документация"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Текст чанка\n\n📎 Источник: Документация"


@pytest.mark.unit
def test_apply_chunk_template_no_metadata(ai_client):
    """Тест: chunk_metadata отсутствует (None)"""
    template = "[$username|fallback:Пользователь]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": None}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь]: Текст"


@pytest.mark.unit
def test_apply_chunk_template_empty_metadata(ai_client):
    """Тест: chunk_metadata пустой словарь"""
    template = "[$username|fallback:Пользователь]: $content"
    content = "Текст"
    chunk = {}  # chunk_metadata отсутствует
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь]: Текст"


@pytest.mark.unit
def test_apply_chunk_template_numeric_values(ai_client):
    """Тест: Числовые значения из chunk_metadata"""
    template = "User ID: $user_id, Chat ID: $chat_id, Message: $content"
    content = "Текст сообщения"
    chunk = {"chunk_metadata": {"user_id": 12345, "chat_id": 67890}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "User ID: 12345, Chat ID: 67890, Message: Текст сообщения"


@pytest.mark.unit
def test_apply_chunk_template_boolean_values(ai_client):
    """Тест: Булевы значения из chunk_metadata"""
    template = "Is admin: $is_admin, Content: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {"is_admin": True}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Is admin: True, Content: Текст"


@pytest.mark.unit
def test_apply_chunk_template_nested_metadata_not_supported(ai_client):
    """Тест: Вложенные поля не поддерживаются (только плоские ключи)"""
    template = "$content from $user.name"
    content = "Текст"
    chunk = {"chunk_metadata": {"user": {"name": "John"}}}
    
    # Вложенные поля не поддерживаются - $user.name не будет найдено
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    # $user.name не найден, вернется пустая строка (без fallback)
    assert "from " in result
    assert "Текст" in result


@pytest.mark.unit
def test_apply_chunk_template_special_characters_in_fallback(ai_client):
    """Тест: Специальные символы в fallback значении"""
    template = "[$username|fallback:Пользователь (неизвестно)]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь (неизвестно)]: Текст"


@pytest.mark.unit
def test_apply_chunk_template_dollar_in_content(ai_client):
    """Тест: Символ $ в самом контенте не обрабатывается как маркер"""
    template = "$content"
    content = "Цена: $100"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Цена: $100"


@pytest.mark.unit
def test_apply_chunk_template_multiple_same_field(ai_client):
    """Тест: Одно поле используется несколько раз в шаблоне"""
    template = "$username сказал: $content (от $username)"
    content = "Привет!"
    chunk = {"chunk_metadata": {"username": "@john_doe"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "@john_doe сказал: Привет! (от @john_doe)"


@pytest.mark.unit
def test_apply_chunk_template_field_not_in_metadata_no_fallback(ai_client):
    """Тест: Поле отсутствует и нет fallback - пустая строка"""
    template = "[$username]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {}}  # username отсутствует, fallback нет
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[]: Текст"  # Пустая строка вместо $username


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ _apply_chunk_format - ИНТЕГРАЦИЯ
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_apply_chunk_format_no_format(ai_client):
    """Тест: chunk_format не указан - возвращается оригинальный контент"""
    content = "Оригинальный текст"
    chunk = {"document_type": "chat_history", "chunk_metadata": {"username": "@john"}}
    chunk_format = None
    
    result = ai_client._apply_chunk_format(content, chunk, "chat_history", chunk_format)
    
    assert result == "Оригинальный текст"


@pytest.mark.unit
def test_apply_chunk_format_no_template_for_type(ai_client):
    """Тест: Шаблон не указан для типа документа - возвращается оригинальный контент"""
    content = "Оригинальный текст"
    chunk = {"document_type": "chat_history", "chunk_metadata": {"username": "@john"}}
    chunk_format = {"knowledge": "[$category]: $content"}  # Нет шаблона для chat_history
    
    result = ai_client._apply_chunk_format(content, chunk, "chat_history", chunk_format)
    
    assert result == "Оригинальный текст"


@pytest.mark.unit
def test_apply_chunk_format_chat_history(ai_client):
    """Тест: Применение шаблона для chat_history"""
    content = "Привет!"
    chunk = {"document_type": "chat_history", "chunk_metadata": {"username": "@john_doe"}}
    chunk_format = {"chat_history": "[$username|fallback:Пользователь]: $content"}
    
    result = ai_client._apply_chunk_format(content, chunk, "chat_history", chunk_format)
    
    assert result == "[@john_doe]: Привет!"


@pytest.mark.unit
def test_apply_chunk_format_knowledge(ai_client):
    """Тест: Применение шаблона для knowledge"""
    content = "Документация"
    chunk = {"document_type": "knowledge", "chunk_metadata": {"category": "API"}}
    chunk_format = {"knowledge": "[$category|fallback:База знаний] $content"}
    
    result = ai_client._apply_chunk_format(content, chunk, "knowledge", chunk_format)
    
    assert result == "[API] Документация"


@pytest.mark.unit
def test_apply_chunk_format_other(ai_client):
    """Тест: Применение шаблона для other"""
    content = "Текст"
    chunk = {"document_type": "other", "chunk_metadata": {"source": "Внешний источник"}}
    chunk_format = {"other": "$content\n\nИсточник: $source|fallback:Неизвестно"}
    
    result = ai_client._apply_chunk_format(content, chunk, "other", chunk_format)
    
    assert result == "Текст\n\nИсточник: Внешний источник"


@pytest.mark.unit
def test_apply_chunk_format_all_types(ai_client):
    """Тест: Применение шаблонов для всех типов документов"""
    chunk_format = {
        "chat_history": "[$username|fallback:Пользователь]: $content",
        "knowledge": "[$category|fallback:База знаний] $content",
        "other": "$content"
    }
    
    # Chat history
    result1 = ai_client._apply_chunk_format(
        "Привет!",
        {"chunk_metadata": {"username": "@john"}},
        "chat_history",
        chunk_format
    )
    assert result1 == "[@john]: Привет!"
    
    # Knowledge
    result2 = ai_client._apply_chunk_format(
        "Документация",
        {"chunk_metadata": {"category": "API"}},
        "knowledge",
        chunk_format
    )
    assert result2 == "[API] Документация"
    
    # Other
    result3 = ai_client._apply_chunk_format(
        "Текст",
        {"chunk_metadata": {}},
        "other",
        chunk_format
    )
    assert result3 == "Текст"


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ _build_messages - ИНТЕГРАЦИЯ С RAG
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_build_messages_chat_history_with_format(ai_client):
    """Тест: Форматирование chat_history чанков в messages"""
    rag_chunks = [
        {
            "content": "Привет!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john_doe"}
        },
        {
            "content": "Привет, Джон!",
            "document_type": "chat_history",
            "role": "assistant",
            "processed_at": "2024-01-01T10:00:01",
            "chunk_metadata": {}
        }
    ]
    
    chunk_format = {"chat_history": "[$username|fallback:Пользователь]: $content"}
    
    messages = ai_client._build_messages(
        prompt="Как дела?",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Проверяем, что chat_history отформатированы
    assert len(messages) == 3  # system (нет), 2 chat_history, 1 final user
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "[@john_doe]: Привет!"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "[Пользователь]: Привет, Джон!"  # fallback для assistant


@pytest.mark.unit
def test_build_messages_knowledge_with_format(ai_client):
    """Тест: Форматирование knowledge чанков в KNOWLEDGE блоке"""
    rag_chunks = [
        {
            "content": "Документация по API",
            "document_type": "knowledge",
            "similarity": 0.9,
            "chunk_metadata": {"category": "DOCUMENTATION"}
        },
        {
            "content": "Примеры использования",
            "document_type": "knowledge",
            "similarity": 0.85,
            "chunk_metadata": {"category": "EXAMPLES"}
        }
    ]
    
    chunk_format = {"knowledge": "[$category|fallback:База знаний] $content"}
    
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Проверяем KNOWLEDGE блок
    assert len(messages) == 1  # Только final user
    final_content = messages[0]["content"]
    assert "[DOCUMENTATION] Документация по API" in final_content
    assert "[EXAMPLES] Примеры использования" in final_content
    assert "KNOWLEDGE" in final_content


@pytest.mark.unit
def test_build_messages_other_with_format(ai_client):
    """Тест: Форматирование other чанков в ДОП. КОНТЕКСТ"""
    rag_chunks = [
        {
            "content": "Дополнительная информация",
            "document_type": "other",
            "chunk_metadata": {"source": "Внешний источник"}
        }
    ]
    
    chunk_format = {"other": "$content\n\n📎 Источник: $source|fallback:Неизвестно"}
    
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Проверяем ДОП. КОНТЕКСТ блок
    assert len(messages) == 1
    final_content = messages[0]["content"]
    assert "Дополнительная информация" in final_content
    assert "📎 Источник: Внешний источник" in final_content
    assert "ДОП. КОНТЕКСТ" in final_content


@pytest.mark.unit
def test_build_messages_mixed_types_with_format(ai_client):
    """Тест: Смешанные типы чанков с разными форматами"""
    rag_chunks = [
        {
            "content": "Привет!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john"}
        },
        {
            "content": "Документация",
            "document_type": "knowledge",
            "similarity": 0.9,
            "chunk_metadata": {"category": "API"}
        },
        {
            "content": "Доп. инфо",
            "document_type": "other",
            "chunk_metadata": {"source": "Внешний"}
        }
    ]
    
    chunk_format = {
        "chat_history": "[$username|fallback:Пользователь]: $content",
        "knowledge": "[$category|fallback:База знаний] $content",
        "other": "$content (источник: $source|fallback:Неизвестно)"
    }
    
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Проверяем все типы
    assert len(messages) == 2  # 1 chat_history + 1 final user
    assert "[@john]: Привет!" in messages[0]["content"]
    assert "[API] Документация" in messages[1]["content"]
    assert "Доп. инфо (источник: Внешний)" in messages[1]["content"]


@pytest.mark.unit
def test_build_messages_no_format_applied(ai_client):
    """Тест: Без chunk_format используется оригинальный контент"""
    rag_chunks = [
        {
            "content": "Привет!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john"}
        }
    ]
    
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=None
    )
    
    # Без формата используется оригинальный контент
    assert messages[0]["content"] == "Привет!"


@pytest.mark.unit
def test_build_messages_partial_format(ai_client):
    """Тест: Формат указан только для одного типа"""
    rag_chunks = [
        {
            "content": "Привет!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john"}
        },
        {
            "content": "Документация",
            "document_type": "knowledge",
            "similarity": 0.9,
            "chunk_metadata": {"category": "API"}
        }
    ]
    
    # Формат только для chat_history
    chunk_format = {"chat_history": "[$username|fallback:Пользователь]: $content"}
    
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # chat_history отформатирован, knowledge - нет
    assert "[@john]: Привет!" in messages[0]["content"]
    assert "Документация" in messages[1]["content"]  # Оригинальный контент для knowledge


# ═══════════════════════════════════════════════════════════
# ТЕСТЫ ГРАНИЧНЫХ СЛУЧАЕВ
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_apply_chunk_template_empty_content(ai_client):
    """Тест: Пустой контент"""
    template = "[$username]: $content"
    content = ""
    chunk = {"chunk_metadata": {"username": "@john"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john]: "


@pytest.mark.unit
def test_apply_chunk_template_content_only_no_metadata(ai_client):
    """Тест: Только $content, метаданные не используются"""
    template = "$content"
    content = "Текст"
    chunk = {"chunk_metadata": {"username": "@john"}}  # Есть метаданные, но не используются
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Текст"


@pytest.mark.unit
def test_apply_chunk_template_all_fields_missing(ai_client):
    """Тест: Все поля отсутствуют, используются fallback"""
    template = "[$username|fallback:Пользователь] ($user_id|fallback:Неизвестно): $content"
    content = "Текст"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь] (Неизвестно): Текст"


@pytest.mark.unit
def test_apply_chunk_template_null_values(ai_client):
    """Тест: None значения в chunk_metadata"""
    template = "[$username|fallback:Пользователь]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {"username": None}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[Пользователь]: Текст"  # None обрабатывается как отсутствие


@pytest.mark.unit
def test_apply_chunk_template_zero_value(ai_client):
    """Тест: Нулевое значение (0) не считается пустым"""
    template = "User ID: $user_id, Content: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {"user_id": 0}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "User ID: 0, Content: Текст"


@pytest.mark.unit
def test_apply_chunk_template_false_value(ai_client):
    """Тест: False значение не считается пустым"""
    template = "Is active: $is_active, Content: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {"is_active": False}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Is active: False, Content: Текст"


@pytest.mark.unit
def test_apply_chunk_template_very_long_fallback(ai_client):
    """Тест: Очень длинное fallback значение"""
    template = "[$username|fallback:Очень длинное имя пользователя которое может быть очень длинным]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert "Очень длинное имя пользователя которое может быть очень длинным" in result
    assert "Текст" in result


@pytest.mark.unit
def test_apply_chunk_template_special_chars_in_metadata(ai_client):
    """Тест: Специальные символы в значениях метаданных"""
    template = "[$username]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {"username": "@user_123!@#$%^&*()"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@user_123!@#$%^&*()]: Текст"


@pytest.mark.unit
def test_apply_chunk_template_unicode_in_metadata(ai_client):
    """Тест: Unicode символы в метаданных"""
    template = "[$username]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {"username": "👤 Пользователь"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[👤 Пользователь]: Текст"


@pytest.mark.unit
def test_apply_chunk_template_regex_special_chars(ai_client):
    """Тест: Специальные символы regex в шаблоне (не должны ломать парсинг)"""
    template = "[$username]: $content (.*+?^${}[]|)"
    content = "Текст"
    chunk = {"chunk_metadata": {"username": "@john"}}
    
    # Не должно быть ошибки парсинга
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert "[@john]: Текст" in result


@pytest.mark.unit
def test_apply_chunk_template_multiple_fallbacks(ai_client):
    """Тест: Несколько полей с fallback в одном шаблоне"""
    template = "[$username|fallback:Пользователь] ($user_id|fallback:Неизвестно) в чате $chat_id|fallback:Неизвестный: $content"
    content = "Сообщение"
    chunk = {"chunk_metadata": {"username": "@john"}}  # Только username есть
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert "[@john]" in result
    assert "(Неизвестно)" in result
    assert "Неизвестный" in result
    assert "Сообщение" in result


@pytest.mark.unit
def test_apply_chunk_template_content_with_dollar_signs(ai_client):
    """Тест: Контент содержит символы $ (не должны обрабатываться как маркеры)"""
    template = "[$username]: $content"
    content = "Цена: $100, скидка: $20"
    chunk = {"chunk_metadata": {"username": "@john"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john]: Цена: $100, скидка: $20"


@pytest.mark.unit
def test_apply_chunk_template_fallback_with_dollar_sign(ai_client):
    """Тест: Fallback содержит символ $ - не поддерживается, т.к. $ зарезервирован для маркеров"""
    template = "[$username|fallback:unknown user]: $content"
    content = "Текст"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[unknown user]: Текст"


@pytest.mark.unit
def test_build_messages_empty_rag_chunks(ai_client):
    """Тест: Пустой массив rag_chunks"""
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=[],
        chunk_format={"chat_history": "[$username]: $content"}
    )
    
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Вопрос"


@pytest.mark.unit
def test_build_messages_none_rag_chunks(ai_client):
    """Тест: rag_chunks = None"""
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=None,
        chunk_format={"chat_history": "[$username]: $content"}
    )
    
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Вопрос"


@pytest.mark.unit
def test_build_messages_chunk_without_metadata_key(ai_client):
    """Тест: Чанк без ключа chunk_metadata"""
    rag_chunks = [
        {
            "content": "Привет!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00"
            # Нет chunk_metadata
        }
    ]
    
    chunk_format = {"chat_history": "[$username|fallback:Пользователь]: $content"}
    
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Должен использоваться fallback
    assert "[Пользователь]: Привет!" in messages[0]["content"]


@pytest.mark.unit
def test_build_messages_invalid_document_type(ai_client):
    """Тест: Неизвестный document_type (не обрабатывается форматом)"""
    rag_chunks = [
        {
            "content": "Текст",
            "document_type": "unknown_type",
            "chunk_metadata": {"username": "@john"}
        }
    ]
    
    chunk_format = {"chat_history": "[$username]: $content"}
    
    # Не должно быть ошибки, просто не применяется формат
    messages = ai_client._build_messages(
        prompt="Вопрос",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # unknown_type не обрабатывается, но не должно быть ошибки
    assert len(messages) >= 1

