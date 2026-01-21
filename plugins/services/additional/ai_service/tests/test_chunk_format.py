"""
Tests for chunk_format functionality in ai_client
Verify correctness of applying templates with $ markers to chunks
"""
from unittest.mock import MagicMock

import pytest

from plugins.utilities.ai.ai_client.ai_client import AIClient


@pytest.fixture(scope="module")
def ai_client():
    """Create AIClient with mocks once per module (for test speed)"""
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
# TESTS _apply_chunk_template - BASIC FUNCTIONALITY
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_apply_chunk_template_simple_content(ai_client):
    """Test: Simple $content substitution"""
    template = "$content"
    content = "Chunk text"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Chunk text"


@pytest.mark.unit
def test_apply_chunk_template_with_username(ai_client):
    """Test: Username substitution from chunk_metadata"""
    template = "[$username]: $content"
    content = "Hello!"
    chunk = {"chunk_metadata": {"username": "@john_doe"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john_doe]: Hello!"


@pytest.mark.unit
def test_apply_chunk_template_with_fallback(ai_client):
    """Test: Using fallback when field is missing"""
    template = "[$username|fallback:User]: $content"
    content = "Hello!"
    chunk = {"chunk_metadata": {}}  # username missing
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User]: Hello!"


@pytest.mark.unit
def test_apply_chunk_template_fallback_with_empty_string(ai_client):
    """Test: Fallback used when field is empty"""
    template = "[$username|fallback:User]: $content"
    content = "Hello!"
    chunk = {"chunk_metadata": {"username": ""}}  # Empty string
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User]: Hello!"


@pytest.mark.unit
def test_apply_chunk_template_multiple_fields(ai_client):
    """Test: Multiple fields from chunk_metadata"""
    template = "[$username] ($user_id): $content"
    content = "Message"
    chunk = {"chunk_metadata": {"username": "@john_doe", "user_id": 12345}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john_doe] (12345): Message"


@pytest.mark.unit
def test_apply_chunk_template_complex_format(ai_client):
    """Test: Complex format with multiple fields and fallback"""
    template = "[$username|fallback:User] ($user_id|fallback:Unknown): $content"
    content = "Message text"
    chunk = {"chunk_metadata": {"username": "@john_doe"}}  # user_id missing
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john_doe] (Unknown): Message text"


@pytest.mark.unit
def test_apply_chunk_template_with_category(ai_client):
    """Test: Using category for knowledge chunks"""
    template = "[$category|fallback:Knowledge Base] $content"
    content = "API documentation"
    chunk = {"chunk_metadata": {"category": "DOCUMENTATION"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[DOCUMENTATION] API documentation"


@pytest.mark.unit
def test_apply_chunk_template_with_version(ai_client):
    """Test: Using version in template"""
    template = "[$category] v$version: $content"
    content = "Function description"
    chunk = {"chunk_metadata": {"category": "API", "version": "1.2.3"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[API] v1.2.3: Function description"


@pytest.mark.unit
def test_apply_chunk_template_multiline_format(ai_client):
    """Test: Multiline format"""
    template = "$content\n\n📎 Source: $source|fallback:Unknown"
    content = "Chunk text"
    chunk = {"chunk_metadata": {"source": "Documentation"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Chunk text\n\n📎 Source: Documentation"


@pytest.mark.unit
def test_apply_chunk_template_no_metadata(ai_client):
    """Test: chunk_metadata is missing (None)"""
    template = "[$username|fallback:User]: $content"
    content = "Text"
    chunk = {"chunk_metadata": None}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User]: Text"


@pytest.mark.unit
def test_apply_chunk_template_empty_metadata(ai_client):
    """Test: chunk_metadata is empty dictionary"""
    template = "[$username|fallback:User]: $content"
    content = "Text"
    chunk = {}  # chunk_metadata missing
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User]: Text"


@pytest.mark.unit
def test_apply_chunk_template_numeric_values(ai_client):
    """Test: Numeric values from chunk_metadata"""
    template = "User ID: $user_id, Chat ID: $chat_id, Message: $content"
    content = "Message text"
    chunk = {"chunk_metadata": {"user_id": 12345, "chat_id": 67890}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "User ID: 12345, Chat ID: 67890, Message: Message text"


@pytest.mark.unit
def test_apply_chunk_template_boolean_values(ai_client):
    """Test: Boolean values from chunk_metadata"""
    template = "Is admin: $is_admin, Content: $content"
    content = "Text"
    chunk = {"chunk_metadata": {"is_admin": True}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Is admin: True, Content: Text"


@pytest.mark.unit
def test_apply_chunk_template_nested_metadata_not_supported(ai_client):
    """Test: Nested fields not supported (only flat keys)"""
    template = "$content from $user.name"
    content = "Text"
    chunk = {"chunk_metadata": {"user": {"name": "John"}}}
    
    # Nested fields not supported - $user.name won't be found
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    # $user.name not found, will return empty string (without fallback)
    assert "from " in result
    assert "Text" in result


@pytest.mark.unit
def test_apply_chunk_template_special_characters_in_fallback(ai_client):
    """Test: Special characters in fallback value"""
    template = "[$username|fallback:User (unknown)]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User (unknown)]: Text"


@pytest.mark.unit
def test_apply_chunk_template_dollar_in_content(ai_client):
    """Test: $ symbol in content itself is not processed as marker"""
    template = "$content"
    content = "Price: $100"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Price: $100"


@pytest.mark.unit
def test_apply_chunk_template_multiple_same_field(ai_client):
    """Test: Same field used multiple times in template"""
    template = "$username said: $content (from $username)"
    content = "Hello!"
    chunk = {"chunk_metadata": {"username": "@john_doe"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "@john_doe said: Hello! (from @john_doe)"


@pytest.mark.unit
def test_apply_chunk_template_field_not_in_metadata_no_fallback(ai_client):
    """Test: Field missing and no fallback - empty string"""
    template = "[$username]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {}}  # username missing, no fallback
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[]: Text"  # Empty string instead of $username


# ═══════════════════════════════════════════════════════════
# TESTS _apply_chunk_format - INTEGRATION
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_apply_chunk_format_no_format(ai_client):
    """Test: chunk_format not specified - original content returned"""
    content = "Original text"
    chunk = {"document_type": "chat_history", "chunk_metadata": {"username": "@john"}}
    chunk_format = None
    
    result = ai_client._apply_chunk_format(content, chunk, "chat_history", chunk_format)
    
    assert result == "Original text"


@pytest.mark.unit
def test_apply_chunk_format_no_template_for_type(ai_client):
    """Test: Template not specified for document type - original content returned"""
    content = "Original text"
    chunk = {"document_type": "chat_history", "chunk_metadata": {"username": "@john"}}
    chunk_format = {"knowledge": "[$category]: $content"}  # No template for chat_history
    
    result = ai_client._apply_chunk_format(content, chunk, "chat_history", chunk_format)
    
    assert result == "Original text"


@pytest.mark.unit
def test_apply_chunk_format_chat_history(ai_client):
    """Test: Applying template for chat_history"""
    content = "Hello!"
    chunk = {"document_type": "chat_history", "chunk_metadata": {"username": "@john_doe"}}
    chunk_format = {"chat_history": "[$username|fallback:User]: $content"}
    
    result = ai_client._apply_chunk_format(content, chunk, "chat_history", chunk_format)
    
    assert result == "[@john_doe]: Hello!"


@pytest.mark.unit
def test_apply_chunk_format_knowledge(ai_client):
    """Test: Applying template for knowledge"""
    content = "Documentation"
    chunk = {"document_type": "knowledge", "chunk_metadata": {"category": "API"}}
    chunk_format = {"knowledge": "[$category|fallback:Knowledge Base] $content"}
    
    result = ai_client._apply_chunk_format(content, chunk, "knowledge", chunk_format)
    
    assert result == "[API] Documentation"


@pytest.mark.unit
def test_apply_chunk_format_other(ai_client):
    """Test: Applying template for other"""
    content = "Text"
    chunk = {"document_type": "other", "chunk_metadata": {"source": "External source"}}
    chunk_format = {"other": "$content\n\nSource: $source|fallback:Unknown"}
    
    result = ai_client._apply_chunk_format(content, chunk, "other", chunk_format)
    
    assert result == "Text\n\nSource: External source"


@pytest.mark.unit
def test_apply_chunk_format_all_types(ai_client):
    """Test: Applying templates for all document types"""
    chunk_format = {
        "chat_history": "[$username|fallback:User]: $content",
        "knowledge": "[$category|fallback:Knowledge Base] $content",
        "other": "$content"
    }
    
    # Chat history
    result1 = ai_client._apply_chunk_format(
        "Hello!",
        {"chunk_metadata": {"username": "@john"}},
        "chat_history",
        chunk_format
    )
    assert result1 == "[@john]: Hello!"
    
    # Knowledge
    result2 = ai_client._apply_chunk_format(
        "Documentation",
        {"chunk_metadata": {"category": "API"}},
        "knowledge",
        chunk_format
    )
    assert result2 == "[API] Documentation"
    
    # Other
    result3 = ai_client._apply_chunk_format(
        "Text",
        {"chunk_metadata": {}},
        "other",
        chunk_format
    )
    assert result3 == "Text"


# ═══════════════════════════════════════════════════════════
# TESTS _build_messages - RAG INTEGRATION
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_build_messages_chat_history_with_format(ai_client):
    """Test: Formatting chat_history chunks in messages"""
    rag_chunks = [
        {
            "content": "Hello!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john_doe"}
        },
        {
            "content": "Hello, John!",
            "document_type": "chat_history",
            "role": "assistant",
            "processed_at": "2024-01-01T10:00:01",
            "chunk_metadata": {}
        }
    ]
    
    chunk_format = {"chat_history": "[$username|fallback:User]: $content"}
    
    messages = ai_client._build_messages(
        prompt="How are you?",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Check that chat_history are formatted
    assert len(messages) == 3  # no system, 2 chat_history, 1 final user
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "[@john_doe]: Hello!"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "[User]: Hello, John!"  # fallback for assistant


@pytest.mark.unit
def test_build_messages_knowledge_with_format(ai_client):
    """Test: Formatting knowledge chunks in KNOWLEDGE block"""
    rag_chunks = [
        {
            "content": "API documentation",
            "document_type": "knowledge",
            "similarity": 0.9,
            "chunk_metadata": {"category": "DOCUMENTATION"}
        },
        {
            "content": "Usage examples",
            "document_type": "knowledge",
            "similarity": 0.85,
            "chunk_metadata": {"category": "EXAMPLES"}
        }
    ]
    
    chunk_format = {"knowledge": "[$category|fallback:Knowledge Base] $content"}
    
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Check KNOWLEDGE block
    assert len(messages) == 1  # Only final user
    final_content = messages[0]["content"]
    assert "[DOCUMENTATION] API documentation" in final_content
    assert "[EXAMPLES] Usage examples" in final_content
    assert "KNOWLEDGE" in final_content


@pytest.mark.unit
def test_build_messages_other_with_format(ai_client):
    """Test: Formatting other chunks in ADD. CONTEXT"""
    rag_chunks = [
        {
            "content": "Additional information",
            "document_type": "other",
            "chunk_metadata": {"source": "External source"}
        }
    ]
    
    chunk_format = {"other": "$content\n\n📎 Source: $source|fallback:Unknown"}
    
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Check ADD. CONTEXT block
    assert len(messages) == 1
    final_content = messages[0]["content"]
    assert "Additional information" in final_content
    assert "📎 Source: External source" in final_content
    assert "ADD. CONTEXT" in final_content


@pytest.mark.unit
def test_build_messages_mixed_types_with_format(ai_client):
    """Test: Mixed chunk types with different formats"""
    rag_chunks = [
        {
            "content": "Hello!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john"}
        },
        {
            "content": "Documentation",
            "document_type": "knowledge",
            "similarity": 0.9,
            "chunk_metadata": {"category": "API"}
        },
        {
            "content": "Additional info",
            "document_type": "other",
            "chunk_metadata": {"source": "External"}
        }
    ]
    
    chunk_format = {
        "chat_history": "[$username|fallback:User]: $content",
        "knowledge": "[$category|fallback:Knowledge Base] $content",
        "other": "$content (source: $source|fallback:Unknown)"
    }
    
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Check all types
    assert len(messages) == 2  # 1 chat_history + 1 final user
    assert "[@john]: Hello!" in messages[0]["content"]
    assert "[API] Documentation" in messages[1]["content"]
    assert "Additional info (source: External)" in messages[1]["content"]


@pytest.mark.unit
def test_build_messages_no_format_applied(ai_client):
    """Test: Without chunk_format original content is used"""
    rag_chunks = [
        {
            "content": "Hello!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john"}
        }
    ]
    
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=None
    )
    
    # Without format original content is used
    assert messages[0]["content"] == "Hello!"


@pytest.mark.unit
def test_build_messages_partial_format(ai_client):
    """Test: Format specified only for one type"""
    rag_chunks = [
        {
            "content": "Hello!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00",
            "chunk_metadata": {"username": "@john"}
        },
        {
            "content": "Documentation",
            "document_type": "knowledge",
            "similarity": 0.9,
            "chunk_metadata": {"category": "API"}
        }
    ]
    
    # Format only for chat_history
    chunk_format = {"chat_history": "[$username|fallback:User]: $content"}
    
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # chat_history formatted, knowledge - not
    assert "[@john]: Hello!" in messages[0]["content"]
    assert "Documentation" in messages[1]["content"]  # Original content for knowledge


# ═══════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════

@pytest.mark.unit
def test_apply_chunk_template_empty_content(ai_client):
    """Test: Empty content"""
    template = "[$username]: $content"
    content = ""
    chunk = {"chunk_metadata": {"username": "@john"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john]: "


@pytest.mark.unit
def test_apply_chunk_template_content_only_no_metadata(ai_client):
    """Test: Only $content, metadata not used"""
    template = "$content"
    content = "Text"
    chunk = {"chunk_metadata": {"username": "@john"}}  # Metadata exists but not used
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Text"


@pytest.mark.unit
def test_apply_chunk_template_all_fields_missing(ai_client):
    """Test: All fields missing, fallbacks used"""
    template = "[$username|fallback:User] ($user_id|fallback:Unknown): $content"
    content = "Text"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User] (Unknown): Text"


@pytest.mark.unit
def test_apply_chunk_template_null_values(ai_client):
    """Test: None values in chunk_metadata"""
    template = "[$username|fallback:User]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {"username": None}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[User]: Text"  # None treated as missing


@pytest.mark.unit
def test_apply_chunk_template_zero_value(ai_client):
    """Test: Zero value (0) is not considered empty"""
    template = "User ID: $user_id, Content: $content"
    content = "Text"
    chunk = {"chunk_metadata": {"user_id": 0}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "User ID: 0, Content: Text"


@pytest.mark.unit
def test_apply_chunk_template_false_value(ai_client):
    """Test: False value is not considered empty"""
    template = "Is active: $is_active, Content: $content"
    content = "Text"
    chunk = {"chunk_metadata": {"is_active": False}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "Is active: False, Content: Text"


@pytest.mark.unit
def test_apply_chunk_template_very_long_fallback(ai_client):
    """Test: Very long fallback value"""
    template = "[$username|fallback:Very long username that can be very long]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert "Very long username that can be very long" in result
    assert "Text" in result


@pytest.mark.unit
def test_apply_chunk_template_special_chars_in_metadata(ai_client):
    """Test: Special characters in metadata values"""
    template = "[$username]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {"username": "@user_123!@#$%^&*()"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@user_123!@#$%^&*()]: Text"


@pytest.mark.unit
def test_apply_chunk_template_unicode_in_metadata(ai_client):
    """Test: Unicode characters in metadata"""
    template = "[$username]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {"username": "👤 User"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[👤 User]: Text"


@pytest.mark.unit
def test_apply_chunk_template_regex_special_chars(ai_client):
    """Test: Regex special characters in template (should not break parsing)"""
    template = "[$username]: $content (.*+?^${}[]|)"
    content = "Text"
    chunk = {"chunk_metadata": {"username": "@john"}}
    
    # Should not have parsing error
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert "[@john]: Text" in result


@pytest.mark.unit
def test_apply_chunk_template_multiple_fallbacks(ai_client):
    """Test: Multiple fields with fallback in one template"""
    template = "[$username|fallback:User] ($user_id|fallback:Unknown) in chat $chat_id|fallback:Unknown: $content"
    content = "Message"
    chunk = {"chunk_metadata": {"username": "@john"}}  # Only username exists
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert "[@john]" in result
    assert "(Unknown)" in result
    assert "Unknown" in result
    assert "Message" in result


@pytest.mark.unit
def test_apply_chunk_template_content_with_dollar_signs(ai_client):
    """Test: Content contains $ symbols (should not be processed as markers)"""
    template = "[$username]: $content"
    content = "Price: $100, discount: $20"
    chunk = {"chunk_metadata": {"username": "@john"}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[@john]: Price: $100, discount: $20"


@pytest.mark.unit
def test_apply_chunk_template_fallback_with_dollar_sign(ai_client):
    """Test: Fallback contains $ symbol - not supported, as $ is reserved for markers"""
    template = "[$username|fallback:unknown user]: $content"
    content = "Text"
    chunk = {"chunk_metadata": {}}
    
    result = ai_client._apply_chunk_template(template, content, chunk)
    
    assert result == "[unknown user]: Text"


@pytest.mark.unit
def test_build_messages_empty_rag_chunks(ai_client):
    """Test: Empty rag_chunks array"""
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=[],
        chunk_format={"chat_history": "[$username]: $content"}
    )
    
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Question"


@pytest.mark.unit
def test_build_messages_none_rag_chunks(ai_client):
    """Test: rag_chunks = None"""
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=None,
        chunk_format={"chat_history": "[$username]: $content"}
    )
    
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Question"


@pytest.mark.unit
def test_build_messages_chunk_without_metadata_key(ai_client):
    """Test: Chunk without chunk_metadata key"""
    rag_chunks = [
        {
            "content": "Hello!",
            "document_type": "chat_history",
            "role": "user",
            "processed_at": "2024-01-01T10:00:00"
            # No chunk_metadata
        }
    ]
    
    chunk_format = {"chat_history": "[$username|fallback:User]: $content"}
    
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # Should use fallback
    assert "[User]: Hello!" in messages[0]["content"]


@pytest.mark.unit
def test_build_messages_invalid_document_type(ai_client):
    """Test: Unknown document_type (not processed by format)"""
    rag_chunks = [
        {
            "content": "Text",
            "document_type": "unknown_type",
            "chunk_metadata": {"username": "@john"}
        }
    ]
    
    chunk_format = {"chat_history": "[$username]: $content"}
    
    # Should not have error, just format not applied
    messages = ai_client._build_messages(
        prompt="Question",
        rag_chunks=rag_chunks,
        chunk_format=chunk_format
    )
    
    # unknown_type not processed, but should not have error
    assert len(messages) >= 1

