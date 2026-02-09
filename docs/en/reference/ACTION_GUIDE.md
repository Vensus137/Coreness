---
title: Actions Guide
description: Complete reference of all available actions in Coreness. Sending messages, AI operations, HTTP requests, validation, payments and more.
keywords: coreness actions, send_message, completion, validate, telegram api, AI actions
---

# 🎯 Actions Guide

> **Note:** This guide is being translated. Some parts may still be in Russian or incomplete.

Complete description of all available actions with their parameters and results.

## 📋 Table of Contents

- [ai_rag_service](#ai_rag_service) (4 actions)
  - [⭐ delete_embedding](#delete_embedding)
  - [⭐ get_recent_chunks](#get_recent_chunks)
  - [⭐ save_embedding](#save_embedding)
  - [⭐ search_embedding](#search_embedding)
- [ai_service](#ai_service) (2 actions)
  - [completion](#completion)
  - [embedding](#embedding)
- [download_service](#download_service) (1 actions)
  - [⭐ download_and_extract](#download_and_extract)
- [invoice_service](#invoice_service) (7 actions)
  - [cancel_invoice](#cancel_invoice)
  - [confirm_payment](#confirm_payment)
  - [create_invoice](#create_invoice)
  - [get_invoice](#get_invoice)
  - [get_user_invoices](#get_user_invoices)
  - [mark_invoice_as_paid](#mark_invoice_as_paid)
  - [reject_payment](#reject_payment)
- [scenario_helper](#scenario_helper) (9 actions)
  - [check_value_in_array](#check_value_in_array)
  - [choose_from_array](#choose_from_array)
  - [format_data_to_text](#format_data_to_text)
  - [generate_array](#generate_array)
  - [generate_int](#generate_int)
  - [generate_unique_id](#generate_unique_id)
  - [modify_array](#modify_array)
  - [set_cache](#set_cache)
  - [sleep](#sleep)
- [scenario_processor](#scenario_processor) (2 actions)
  - [execute_scenario](#execute_scenario)
  - [wait_for_action](#wait_for_action)
- [storage_hub](#storage_hub) (4 actions)
  - [delete_storage](#delete_storage)
  - [get_storage](#get_storage)
  - [get_storage_groups](#get_storage_groups)
  - [set_storage](#set_storage)
- [telegram_bot_api](#telegram_bot_api) (5 actions)
  - [answer_callback_query](#answer_callback_query)
  - [build_keyboard](#build_keyboard)
  - [delete_message](#delete_message)
  - [restrict_chat_member](#restrict_chat_member)
  - [send_message](#send_message)
- [user_hub](#user_hub) (8 actions)
  - [clear_user_state](#clear_user_state)
  - [delete_user_storage](#delete_user_storage)
  - [get_tenant_users](#get_tenant_users)
  - [get_user_state](#get_user_state)
  - [get_user_storage](#get_user_storage)
  - [get_users_by_storage_value](#get_users_by_storage_value)
  - [set_user_state](#set_user_state)
  - [set_user_storage](#set_user_storage)
- [validator](#validator) (1 actions)
  - [validate](#validate)

<sup>⭐ — extension (additional plugin). For more information contact the [developer](https://t.me/vensus137).</sup>

<a id="ai_rag_service"></a>
## ai_rag_service

**Description:** RAG extension for AI Service (vector search and embeddings management)

<a id="delete_embedding"></a>
### ⭐ delete_embedding

**Description:** Delete data from vector_storage by document_id or processed_at date

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`document_id`** (`string`, optional) — Document ID to delete (all chunks); if set, other params ignored
- **`until_date`** (`string`, optional) — Delete chunks with processed_at <= until_date (YYYY-MM-DD)
- **`since_date`** (`string`, optional) — Delete chunks with processed_at >= since_date (YYYY-MM-DD)
- **`metadata_filter`** (`object`, optional) — Metadata filter (JSON); e.g. chat_id, username

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error info
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
- **`response_data`** (`object`) — Response data
  - **`deleted_chunks_count`** (`integer`) — Number of deleted chunks

**Usage Example:**

```yaml
# In scenario
- action: "delete_embedding"
  params:
    tenant_id: 123
    # document_id: string (optional)
    # until_date: string (optional)
    # since_date: string (optional)
    # metadata_filter: object (optional)
```

<details>
<summary>📖 Additional Information</summary>

**Удаление данных из vector_storage:**

**Способы удаления:**
1. По `document_id` - удаляет все чанки документа (остальные параметры игнорируются)
2. По дате `processed_at` - удаляет чанки по дате обработки
3. По `metadata_filter` - удаляет чанки с определенными метаданными

**Параметры даты:**
- `since_date`: удалить с даты (включительно)
- `until_date`: удалить до даты (включительно)
- Можно указать оба параметра (диапазон)
- Формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'

**Примеры:**
```yaml
# По document_id
data:
  document_id: "doc_12345"

# По дате
data:
  until_date: "2024-01-01"

# Диапазон дат
data:
  since_date: "2024-01-01"
  until_date: "2024-12-31"

# По метаданным
data:
  metadata_filter: {chat_id: 123}
```

</details>


<a id="get_recent_chunks"></a>
### ⭐ get_recent_chunks

**Description:** Get last N chunks by created_at (date-based, not vector search; sorted by created_at)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`limit_chunks`** (`integer`, optional, range: 1-200) — Number of chunks (default from search_limit_chunks); works with limit_chars
- **`limit_chars`** (`integer`, optional, min: 1) — Character limit (applied after limit_chunks)
- **`document_type`** (`string|array`, optional) — Filter by document type (string or array)
- **`document_id`** (`string|array`, optional) — Filter by document_id (string or array)
- **`until_date`** (`string`, optional) — Filter: chunks with processed_at <= until_date
- **`since_date`** (`string`, optional) — Filter: chunks with processed_at >= since_date
- **`metadata_filter`** (`object`, optional) — Metadata filter (JSON)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error info
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
- **`response_data`** (`object`) — Response data
  - **`chunks`** (`array (of object)`) — Array of chunks (sorted by created_at DESC)
  - **`chunks_count`** (`integer`) — Number of chunks found

**Usage Example:**

```yaml
# In scenario
- action: "get_recent_chunks"
  params:
    tenant_id: 123
    # limit_chunks: integer (optional)
    # limit_chars: integer (optional)
    # document_type: string|array (optional)
    # document_id: string|array (optional)
    # until_date: string (optional)
    # since_date: string (optional)
    # metadata_filter: object (optional)
```

<details>
<summary>📖 Additional Information</summary>

**Получение последних чанков по дате (НЕ векторный поиск):**
- Возвращает последние N чанков, отсортированных по `created_at` (новые первыми, для правильного порядка истории)
- Полезно для получения последних сообщений или истории диалога

**Параметры:**
- `limit_chunks`: количество чанков (по умолчанию 10)
- `limit_chars`: лимит по символам (работает поверх `limit_chunks`)

**Фильтры (комбинируются):**
- `document_type`, `document_id`: строка или массив
- `since_date`, `until_date`: диапазон дат (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS')
- `metadata_filter`: JSON объект (например, `{chat_id: 123}`)

**Примеры:**
```yaml
# Последние 10 чанков
data:
  limit_chunks: 10

# Последние сообщения
data:
  document_type: "message"
  limit_chunks: 20

# Последние чанки документа
data:
  document_id: "doc_123"
  limit_chunks: 10

# Последние чанки за период
data:
  since_date: "2024-01-01"
  until_date: "2024-12-31"
  limit_chunks: 50
```

</details>


<a id="save_embedding"></a>
### ⭐ save_embedding

**Description:** Save text to vector_storage with chunking and embeddings; supports text-only via generate_embedding=false

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`text`** (`string`) — Text to save (cleaned and chunked)
- **`document_id`** (`string`, optional) — Unique document ID; auto-generated if omitted
- **`document_type`** (`string`, required, values: [`knowledge`, `chat_history`, `other`]) — Document type: knowledge, chat_history, other
- **`role`** (`string`, optional, values: [`system`, `user`, `assistant`]) — OpenAI message role (default user)
- **`chunk_metadata`** (`object`, optional) — Chunk metadata (JSON): chat_id, username etc.; used for filtering and in context
- **`model`** (`string`, optional) — Embedding model (default from ai_client)
- **`dimensions`** (`integer`, optional) — Embedding dimensions (default 1024)
- **`chunk_size`** (`integer`, optional, range: 100-8000) — Chunk size in characters (default 1000, ~300-400 tokens, adaptively increased for tables)
- **`chunk_overlap`** (`integer`, optional, range: 0-1000) — Chunk overlap in characters (~20% of chunk_size)
- **`replace_existing`** (`boolean`, optional) — Replace existing document (default false; ALREADY_EXISTS if exists)
- **`generate_embedding`** (`boolean`, optional) — Generate embeddings for chunks (default true); false = text only
- **`created_at`** (`string`, optional) — Creation date (ISO/YYYY-MM-DD); default current time
- 🔑 **`ai_token`** (`string`, optional) — AI API key from tenant config; required if generate_embedding=true

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code: ALREADY_EXISTS, INTERNAL_ERROR, VALIDATION_ERROR
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details (e.g. field validation errors)
- **`response_data`** (`object`) — Response data
  - **`document_id`** (`string`) — Saved document ID (provided or generated)
  - **`document_type`** (`string`) — Document type
  - **`chunks_count`** (`integer`) — Number of chunks created
  - **`model`** (`string`) (optional) — Embedding model used (if generate_embedding=true)
  - **`dimensions`** (`integer`) (optional) — Embedding dimensions (if generate_embedding=true)
  - **`total_tokens`** (`integer`) (optional) — Total tokens in chunks (if generate_embedding=true)
  - **`text_length`** (`integer`) — Source text length (after cleaning)

**Note:**
- 🔑 — field that is automatically taken from tenant configuration (_config) and does not require explicit passing in params

**Usage Example:**

```yaml
# In scenario
- action: "save_embedding"
  params:
    tenant_id: 123
    text: "example"
    # document_id: string (optional)
    document_type: "example"
    # role: string (optional)
    # chunk_metadata: object (optional)
    # model: string (optional)
    # dimensions: integer (optional)
    # chunk_size: integer (optional)
    # chunk_overlap: integer (optional)
    # replace_existing: boolean (optional)
    # generate_embedding: boolean (optional)
    # created_at: string (optional)
    # ai_token: string (optional)
```

<details>
<summary>📖 Additional Information</summary>

**Автоматическое сохранение текста с разбиением на чанки:**
1. Очистка текста (лишние пробелы, невидимые символы)
2. Разбиение на чанки (гибридный подход: по предложениям/абзацам → по символам)
3. Генерация embeddings (параллельно, если `generate_embedding=true`)
4. Сохранение в `vector_storage`

**Режимы сохранения:**
- `generate_embedding=true` (по умолчанию): с эмбеддингами для векторного поиска
- `generate_embedding=false`: только текст без эмбеддингов (экономит токены, не требует `ai_token`)

**Перекрытие чанков (chunk_overlap):**
- Сохраняет контекст на границах для лучшего поиска
- Рекомендуется ~20% от `chunk_size` (по умолчанию 100 при `chunk_size=512`)
- Расширяется до целых предложений при разбиении

**Генерация document_id:**
- Если не указан → генерируется автоматически (детерминированный)
- Seed: `{tenant_id}:{document_type}:{MD5(text)}`
- Повторная загрузка того же текста вернет тот же ID

**Обработка существующих документов:**
- `replace_existing=false` (по умолчанию): ошибка ALREADY_EXISTS если документ существует
- `replace_existing=true`: старые чанки удаляются, создаются новые

**Пример:**
```yaml
action: save_embedding
data:
  text: "Длинный текст..."
  document_type: "knowledge"
  chunk_size: 512
  chunk_overlap: 100

# Ответ:
result: success
response_data:
  document_id: "doc_12345"
  chunks_count: 5
  total_tokens: 150
```

</details>


<a id="search_embedding"></a>
### ⭐ search_embedding

**Description:** Search similar chunks by text or vector (cosine similarity)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`query_text`** (`string`, optional) — Query text (converted to embedding); use query_text or query_vector
- **`query_vector`** (`array`, optional) — Precomputed vector (array); use query_text or query_vector
- **`limit_chunks`** (`integer`, optional, range: 1-200) — Number of results (top-k); works with limit_chars
- **`limit_chars`** (`integer`, optional, min: 1) — Character limit (applied after limit_chunks)
- **`min_similarity`** (`number`, optional, range: 0.0-1.0) — Min similarity threshold (cosine)
- **`document_id`** (`string|array`, optional) — Filter by document_id (string or array)
- **`document_type`** (`string|array`, optional) — Filter by document type (string or array)
- **`until_date`** (`string`, optional) — Filter: chunks with processed_at <= until_date
- **`since_date`** (`string`, optional) — Filter: chunks with processed_at >= since_date
- **`metadata_filter`** (`object`, optional) — Metadata filter (JSON)
- **`model`** (`string`, optional) — Embedding model (if query_text)
- **`dimensions`** (`integer`, optional) — Embedding dimensions (if query_text)
- 🔑 **`ai_token`** (`string`, optional) — AI API key; required if query_text set

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error info
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
- **`response_data`** (`object`) — Response data
  - **`chunks`** (`array (of object)`) — Array of found chunks
  - **`chunks_count`** (`integer`) — Number of chunks found

**Note:**
- 🔑 — field that is automatically taken from tenant configuration (_config) and does not require explicit passing in params

**Usage Example:**

```yaml
# In scenario
- action: "search_embedding"
  params:
    tenant_id: 123
    # query_text: string (optional)
    # query_vector: array (optional)
    # limit_chunks: integer (optional)
    # limit_chars: integer (optional)
    # min_similarity: number (optional)
    # document_id: string|array (optional)
    # document_type: string|array (optional)
    # until_date: string (optional)
    # since_date: string (optional)
    # metadata_filter: object (optional)
    # model: string (optional)
    # dimensions: integer (optional)
    # ai_token: string (optional)
```

<details>
<summary>📖 Additional Information</summary>

**Семантический поиск похожих чанков:**
- Поиск по cosine similarity между векторами
- Использует HNSW индекс для быстрого поиска
- Результаты сортируются по убыванию similarity

**Запрос (требуется одно из):**
- `query_text`: текст (генерируется embedding автоматически)
- `query_vector`: готовый вектор (не требует API ключ)

**Параметры поиска:**
- `limit_chunks`: top-k результатов (по умолчанию 10)
- `limit_chars`: лимит по символам (работает поверх `limit_chunks`)
- `min_similarity`: минимальный порог (0.0-1.0, по умолчанию 0.7)

**Фильтры (комбинируются):**
- `document_type`, `document_id`: строка или массив
- `since_date`, `until_date`: диапазон дат (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS')
- `metadata_filter`: JSON объект (например, `{chat_id: 123}`)

**Примеры:**
```yaml
# Поиск по тексту
data:
  query_text: "Как работает RAG?"
  limit_chunks: 10
  min_similarity: 0.75

# Поиск с фильтрами
data:
  query_text: "Вопрос"
  document_type: ["message", "document"]
  since_date: "2024-01-01"
  until_date: "2024-12-31"

# Поиск с лимитом по символам
data:
  query_text: "Вопрос"
  limit_chunks: 20
  limit_chars: 5000
```

</details>


<a id="ai_service"></a>
## ai_service

**Description:** Service for AI integration in scenarios

<a id="completion"></a>
### completion

**Description:** AI completion via AI

**Input Parameters:**

- **`prompt`** (`string`) — User request text
- **`system_prompt`** (`string`, optional) — System prompt for context
- **`model`** (`string`, optional) — AI model (default from settings)
- **`max_tokens`** (`integer`, optional) — Maximum tokens (default from settings)
- **`temperature`** (`float`, optional, range: 0.0-2.0) — Generation temperature (default from settings)
- **`context`** (`string`, optional) — Custom context (added to final user message in ADDITIONAL CONTEXT block with other chunks from rag_chunks)
- **`rag_chunks`** (`array (of object)`, optional) — Array of RAG search chunks for building messages. Types: chat_history, knowledge, other. Format: [{content, document_type, role, processed_at, ...}]
- **`json_mode`** (`string`, optional, values: [`json_object`, `json_schema`]) — JSON mode for structured response: 'json_object' or 'json_schema'
- **`json_schema`** (`object`, optional) — JSON schema for json_schema mode (required when json_mode='json_schema')
- **`tools`** (`array (of object)`, optional) — Array of tool objects (tool calling). Each item is an object: type 'function', function: { name, description, parameters }. parameters is JSON Schema for the call arguments (OpenAI-compatible format).
- **`tool_choice`** (`string`, optional) — Tool selection. String: 'none' (do not call), 'auto' (default when tools present), 'required' (must call at least one). Object: force one function — {"type": "function", "function": {"name": "function_name"}}.
- **`chunk_format`** (`object`, optional) — Chunk display format in context. Templates use $ markers. $content + chunk_metadata. Fallback: $field|fallback:value. Markers apply only to chunk data.
- 🔑 **`ai_token`** (`string`) — AI API key from tenant config (_config.ai_token)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, timeout
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details (e.g. field validation errors)
- **`response_data`** (`object`) — Response data
  - **`response_completion`** (`string`) — AI completion response
  - **`prompt_tokens`** (`integer`) — Input tokens (prompt + context)
  - **`completion_tokens`** (`integer`) — Output tokens (generated response)
  - **`total_tokens`** (`integer`) — Total tokens (prompt + completion)
  - **`model`** (`string`) — Model used
  - **`response_dict`** (`object`) (optional) — Parsed dict from JSON response (when using json_mode)
  - **`tool_calls`** (`array (of object)`) (optional) — When using tools — array of call objects. Each item: id, type, function: { name, arguments }. arguments is a JSON string with call parameters (different keys per function); parse in scenario if needed.

**Note:**
- 🔑 — field that is automatically taken from tenant configuration (_config) and does not require explicit passing in params

**Usage Example:**

```yaml
# In scenario
- action: "completion"
  params:
    prompt: "example"
    # system_prompt: string (optional)
    # model: string (optional)
    # max_tokens: integer (optional)
    # temperature: float (optional)
    # context: string (optional)
    # rag_chunks: array (optional)
    # json_mode: string (optional)
    # json_schema: object (optional)
    # tools: array (optional)
    # tool_choice: string (optional)
    # chunk_format: object (optional)
    ai_token: "example"
```

<details>
<summary>📖 Additional Information</summary>

**JSON режимы:**
- `json_object`: модель возвращает валидный JSON (парсится в `response_dict`)
- `json_schema`: строгая JSON схема (требуется `json_schema` параметр)

**Tool Calling:**
- `tools` — массив объектов (каждый: type, function.name, function.description, function.parameters по JSON Schema)
- Модель решает, какие функции вызвать и с какими параметрами; вызовы возвращаются в `response_data.tool_calls`
- `tool_calls` — массив объектов: id, type, function.name, function.arguments (JSON-строка); обработка и циклы — в сценарии
- `tool_choice`: строка 'none'|'auto'|'required' или объект для принудительного вызова одной функции

**Формат чанков (chunk_format):**
- Настройка отображения чанков из RAG через шаблоны с маркерами `$`
- Доступны: `$content` (обязательно) + любые поля из `chunk_metadata`
- Поддерживается fallback: `$field|fallback:значение` (если поле пустое/отсутствует)
- Маркеры работают только с данными чанка (content + chunk_metadata)
- Примеры: `"[$username]: $content"`, `"[$category|fallback:Общее]: $content"`
- Можно задать разные шаблоны для `chat_history`, `knowledge`, `other`

</details>


<a id="embedding"></a>
### embedding

**Description:** Generate text embedding via AI

**Input Parameters:**

- **`text`** (`string`) — Text for embedding generation
- **`model`** (`string`, optional) — Embedding model (default from ai_client.default_embedding_model)
- **`dimensions`** (`integer`, optional) — Embedding dimensions (default from ai_client). Supported for OpenAI text-embedding-3-* only
- 🔑 **`ai_token`** (`string`) — AI API key from tenant config (_config.ai_token)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details (e.g. field validation errors)
- **`response_data`** (`object`) — Response data
  - **`embedding`** (`array (of number)`) — Embedding vector (list of numbers)
  - **`model`** (`string`) — Model used
  - **`dimensions`** (`integer`) — Embedding dimensions
  - **`total_tokens`** (`integer`) — Total tokens

**Note:**
- 🔑 — field that is automatically taken from tenant configuration (_config) and does not require explicit passing in params

**Usage Example:**

```yaml
# In scenario
- action: "embedding"
  params:
    text: "example"
    # model: string (optional)
    # dimensions: integer (optional)
    ai_token: "example"
```

<details>
<summary>📖 Additional Information</summary>

**Генерация векторных представлений текста (embeddings):**
- Используется для RAG (Retrieval-Augmented Generation) и векторного поиска
- Возвращает массив чисел (`embedding`) - векторное представление текста

**Размерность (dimensions):**
- По умолчанию 1024 (настраивается в `ai_client.default_embedding_dimensions`)
- Поддерживается не всеми моделями (для моделей без поддержки размерность фиксирована)

**Пример:**
```yaml
action: embedding
data:
  text: "Текст для векторизации"
  dimensions: 1024

# Ответ:
result: success
response_data:
  embedding: [0.123, -0.456, ...]  # Вектор из 1024 чисел
  dimensions: 1024
  total_tokens: 15
```

</details>


<a id="download_service"></a>
## download_service

**Description:** Service for downloading files from URLs and extracting text content

<a id="download_and_extract"></a>
### ⭐ download_and_extract

**Description:** Download file from URL and extract text content. Supports: PDF, DOCX, TXT, MD, HTML, CSV (incl. Google Sheets). Auto-detects file type via magic bytes, Content-Type or extension

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required for file isolation)
- **`url`** (`string`) — URL to download file from (direct link, Google Drive, Google Docs/Sheets, etc.)
- **`file_type`** (`string`, optional, values: [`pdf`, `docx`, `txt`, `md`, `html`, `csv`]) — File type hint (pdf, docx, txt, md, html, csv). If not set - auto-detected via magic bytes, Content-Type or extension
- **`keep_file`** (`boolean`, optional) — Keep downloaded file instead of auto-cleanup (default false - file deleted after extraction)
- **`max_file_size_mb`** (`integer`, optional, range: 1-500) — Max file size in MB for this specific action (overrides default setting). Checked via HEAD request before download
- **`download_timeout_seconds`** (`integer`, optional, range: 10-3600) — Download timeout in seconds for this specific action (overrides default setting)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code: VALIDATION_ERROR, FILE_TOO_LARGE, DOWNLOAD_FAILED, UNSUPPORTED_FORMAT, EXTRACTION_FAILED, TIMEOUT, INTERNAL_ERROR
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details (e.g. field validation errors)
- **`response_data`** (`object`) — Response data
  - **`file_text`** (`string`) — Extracted text from file
  - **`file_path`** (`string`) (optional) — Path to downloaded file (only if keep_file=true, otherwise null)
  - **`file_metadata`** (`object`) — File metadata

**Usage Example:**

```yaml
# In scenario
- action: "download_and_extract"
  params:
    tenant_id: 123
    url: "example"
    # file_type: string (optional)
    # keep_file: boolean (optional)
    # max_file_size_mb: integer (optional)
    # download_timeout_seconds: integer (optional)
```


<a id="invoice_service"></a>
## invoice_service

**Description:** Service for invoices (create, manage, process payments)

<a id="cancel_invoice"></a>
### cancel_invoice

**Description:** Cancel invoice (set is_cancelled flag)

**Input Parameters:**

- **`invoice_id`** (`integer`, required, min: 1) — Invoice ID (required)

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "cancel_invoice"
  params:
    invoice_id: 123
```


<a id="confirm_payment"></a>
### confirm_payment

**Description:** Confirm payment (answer pre_checkout_query with confirm)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`pre_checkout_query_id`** (`string`, required, min length: 1) — Pre-checkout query ID (required)
- **`invoice_payload`** (`string`, optional, min length: 1) — Invoice ID from payload (optional, to check status before confirm)
- **`error_message`** (`string`, optional) — Error message when rejecting payment (optional; when invoice cancelled or already paid)

**Output Parameters:**

- **`result`** (`string`) — Result: success (payment confirmed), failed (rejected by business logic), error (technical error)
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code: INVOICE_CANCELLED, INVOICE_ALREADY_PAID (when result=failed)
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "confirm_payment"
  params:
    tenant_id: 123
    bot_id: 123
    pre_checkout_query_id: "example"
    # invoice_payload: string (optional)
    # error_message: string (optional)
```


<a id="create_invoice"></a>
### create_invoice

**Description:** Create invoice in DB and send/create link

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`target_user_id`** (`integer`, optional, min: 1) — User ID for invoice (optional, default from event user_id)
- **`chat_id`** (`integer`, optional) — Chat ID for sending (required for send, not for link)
- **`title`** (`string`, required, min length: 1) — Product/service title (required)
- **`description`** (`string`) — Product/service description
- **`amount`** (`integer`, required, min: 1) — Star amount (required, integer)
- **`currency`** (`string`, optional) — Currency (default XTR for stars)
- **`as_link`** (`boolean`, optional) — Create as link instead of send (default false)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data
  - **`invoice_id`** (`integer`) — Created invoice ID
  - **`invoice_message_id`** (`integer`) (optional) — Sent message ID with invoice (when as_link=false)
  - **`invoice_link`** (`string`) (optional) — Invoice link (when as_link=true)

**Usage Example:**

```yaml
# In scenario
- action: "create_invoice"
  params:
    tenant_id: 123
    bot_id: 123
    # target_user_id: integer (optional)
    # chat_id: integer (optional)
    title: "example"
    description: "example"
    amount: 123
    # currency: string (optional)
    # as_link: boolean (optional)
```


<a id="get_invoice"></a>
### get_invoice

**Description:** Get invoice info

**Input Parameters:**

- **`invoice_id`** (`integer`, required, min: 1) — Invoice ID (required)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data
  - **`invoice`** (`object`) — Invoice data

**Usage Example:**

```yaml
# In scenario
- action: "get_invoice"
  params:
    invoice_id: 123
```


<a id="get_user_invoices"></a>
### get_user_invoices

**Description:** Get all user invoices

**Input Parameters:**

- **`target_user_id`** (`integer`, optional, min: 1) — User ID for invoices (optional; default from event user_id)
- **`include_cancelled`** (`boolean`, optional) — Include cancelled invoices (default false)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data
  - **`invoices`** (`array (of object)`) — Array of user invoices

**Usage Example:**

```yaml
# In scenario
- action: "get_user_invoices"
  params:
    # target_user_id: integer (optional)
    # include_cancelled: boolean (optional)
```


<a id="mark_invoice_as_paid"></a>
### mark_invoice_as_paid

**Description:** Mark invoice as paid (payment_successful event handler)

**Input Parameters:**

- **`invoice_payload`** (`string`, required, min length: 1) — ID инвойса из payload события (обязательно)
- **`telegram_payment_charge_id`** (`string`, required, min length: 1) — ID платежа в Telegram (обязательно)
- **`paid_at`** (`string`, optional) — Дата оплаты (опционально, по умолчанию текущая дата)

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "mark_invoice_as_paid"
  params:
    invoice_payload: "example"
    telegram_payment_charge_id: "example"
    # paid_at: string (optional)
```


<a id="reject_payment"></a>
### reject_payment

**Description:** Reject payment (answer pre_checkout_query with reject)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`pre_checkout_query_id`** (`string`, required, min length: 1) — Pre-checkout query ID (required)
- **`error_message`** (`string`, optional) — Error message (optional)

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "reject_payment"
  params:
    tenant_id: 123
    bot_id: 123
    pre_checkout_query_id: "example"
    # error_message: string (optional)
```


<a id="scenario_helper"></a>
## scenario_helper

**Description:** Helper utilities for scenario execution management

<a id="check_value_in_array"></a>
### check_value_in_array

**Description:** Check if value exists in array

**Input Parameters:**

- **`array`** (`array`) — Массив для проверки
- **`value`** (`any`) — Значение для поиска в массиве

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success (найдено), not_found (не найдено), error (ошибка)
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`response_index`** (`integer`) — Порядковый номер (индекс) первого вхождения значения в массиве (только при result: success)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "check_value_in_array"
  params:
    array: []
    value: "value"
```


<a id="choose_from_array"></a>
### choose_from_array

**Description:** Pick random items from array without repeats

**Input Parameters:**

- **`array`** (`array`) — Исходный массив для выбора элементов
- **`count`** (`integer`, required, min: 1) — Количество элементов для выбора (без повторений)
- **`seed`** (`any`, optional) — Seed для детерминированной генерации (опционально, может быть числом, строкой или другим типом)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`random_list`** (`array`) — Массив выбранных элементов (без повторений)
  - **`random_seed`** (`string`) (optional) — Использованный seed (если был передан, сохраняется как есть)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "choose_from_array"
  params:
    array: []
    count: 123
    # seed: any (optional)
```


<a id="format_data_to_text"></a>
### format_data_to_text

**Description:** Format structured data (JSON/YAML) to text for prompts and messages

**Input Parameters:**

- **`format_type`** (`string`, required, values: [`list`, `structured`]) — Тип форматирования: 'list' (простой список с шаблоном через $), 'structured' (структурированный формат с заголовками и вложенными блоками)
- **`input_data`** (`any`) — Массив объектов для форматирования
- **`title`** (`string`, optional) — Заголовок для списка (опционально)
- **`item_template`** (`string`, optional, min length: 1) — Шаблон элемента для формата 'list' через $ (например: '- "$id" - $description'). Обязателен при format_type: 'list'

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`formatted_text`** (`string`) — Отформатированный текст

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "format_data_to_text"
  params:
    format_type: "example"
    input_data: "value"
    # title: string (optional)
    # item_template: string (optional)
```

<details>
<summary>📖 Additional Information</summary>

**Форматы:**

- **`list`** — простой список с шаблоном через `$`
- **`structured`** — структурированный формат: `name — description`, блок `Параметры:` с деталями

**Примеры:**

```yaml
# Формат list
- action: "format_data_to_text"
  params:
    format_type: "list"
    title: "Доступные намерения:"
    item_template: '- "$id" - $description'
    input_data: "{storage_values.ai_router.intents}"
# Результат в _cache.format_data_to_text.formatted_text:
# Доступные намерения:
# - "random_user" - Выбрать случайного пользователя

# Формат structured
- action: "format_data_to_text"
  params:
    format_type: "structured"
    title: "Доступные действия:"
    input_data: "{storage_values.ai_router.actions}"
# Результат в _cache.format_data_to_text.formatted_text:
# Доступные действия:
# call_random_user — Выбрать N пользователей из группы
#   Параметры:
#   - count (integer) — Количество пользователей. По умолчанию: 1
```

**Важно:**
- Шаблон для `list` использует `$` вместо `{}` для избежания конфликта с плейсхолдерами
- Результат сохраняется в `_cache.format_data_to_text.formatted_text` (по умолчанию)
- Если указан `_namespace` в params, результат будет в `_cache.{_namespace}.formatted_text`

</details>


<a id="generate_array"></a>
### generate_array

**Description:** Generate array of random numbers in range (default no repeats)

**Input Parameters:**

- **`min`** (`integer`) — Minimum value (inclusive)
- **`max`** (`integer`) — Maximum value (inclusive)
- **`count`** (`integer`, required, min: 1) — Количество чисел для генерации
- **`seed`** (`any`, optional) — Seed для детерминированной генерации (опционально, может быть числом, строкой или другим типом)
- **`allow_duplicates`** (`boolean`, optional) — Разрешить повторения в массиве (по умолчанию false - без повторений)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`random_list`** (`array (of integer)`) — Массив сгенерированных чисел
  - **`random_seed`** (`string`) (optional) — Использованный seed (если был передан, сохраняется как есть)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "generate_array"
  params:
    min: 123
    max: 123
    count: 123
    # seed: any (optional)
    # allow_duplicates: boolean (optional)
```


<a id="generate_int"></a>
### generate_int

**Description:** Generate random integer in range

**Input Parameters:**

- **`min`** (`integer`) — Minimum value (inclusive)
- **`max`** (`integer`) — Maximum value (inclusive)
- **`seed`** (`any`, optional) — Seed для детерминированной генерации (опционально, может быть числом, строкой или другим типом)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`random_value`** (`integer`) — Generated random number
  - **`random_seed`** (`string`) (optional) — Использованный seed (если был передан, сохраняется как есть)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "generate_int"
  params:
    min: 123
    max: 123
    # seed: any (optional)
```


<a id="generate_unique_id"></a>
### generate_unique_id

**Description:** Generate unique ID via DB autoincrement (deterministic; same seed = same ID). If no seed, random UUID

**Input Parameters:**

- **`seed`** (`string`, optional, min length: 1) — Seed для генерации ID. При повторном запросе с тем же seed вернется тот же ID. Если не указан, генерируется случайный UUID

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`unique_id`** (`integer`) — Уникальный ID (гарантированно уникальный, при одинаковых входных данных возвращается тот же ID)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "generate_unique_id"
  params:
    # seed: string (optional)
```


<a id="modify_array"></a>
### modify_array

**Description:** Modify array: add, remove items or clear

**Input Parameters:**

- **`operation`** (`string`, required, values: [`add`, `remove`, `clear`]) — Операция: 'add' (добавить элемент), 'remove' (удалить элемент), 'clear' (очистить массив)
- **`array`** (`array`) — Исходный массив для модификации
- **`value`** (`any`, optional) — Значение для добавления или удаления (обязательно для операций 'add' и 'remove')
- **`skip_duplicates`** (`boolean`, optional) — Пропускать дубликаты при добавлении (по умолчанию true - не добавлять если элемент уже есть)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success (успешно), not_found (элемент не найден при операции remove), error (ошибка)
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`modified_array`** (`array`) — Модифицированный массив

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "modify_array"
  params:
    operation: "example"
    array: []
    # value: any (optional)
    # skip_duplicates: boolean (optional)
```


<a id="set_cache"></a>
### set_cache

**Description:** Set temporary data in scenario cache. All params returned in response_data and go to flat _cache by default.

**Input Parameters:**

- **`cache`** (`object`) — Объект с данными для установки в кэш. Все переданные параметры будут доступны в последующих шагах сценария через {_cache.ключ} (плоский доступ по умолчанию)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Все переданные параметры из объекта cache возвращаются в response_data и автоматически попадают в плоский _cache по умолчанию.
  - **`*`** (`any`) — Динамические ключи из переданного объекта cache. Все ключи доступны через {_cache.имя_ключа} (плоский доступ по умолчанию)

**Usage Example:**

```yaml
# In scenario
- action: "set_cache"
  params:
    cache: {}
```

<details>
<summary>📖 Additional Information</summary>

**Пример использования:**

```yaml
step:
  - action: "set_cache"
    params:
      cache:
        selected_user: "@username"
        reason: "Случайный выбор"
        metadata:
          timestamp: "2024-01-15"
          source: "ai_router"
  
  - action: "send_message"
    params:
      text: |
        Пользователь: {_cache.selected_user}
        Причина: {_cache.reason}
        Время: {_cache.metadata.timestamp}
        Источник: {_cache.metadata.source}
```

**Важно:**
- Данные должны быть переданы в ключе `cache` в params
- Это позволяет явно указать, что именно нужно кэшировать
- Весь контекст сценария (user_id, chat_id, bot_id и др.) не попадет в кэш

**Доступ к данным:**
- Все переданные параметры доступны через плейсхолдеры `{_cache.ключ}` (плоский доступ по умолчанию)
- Поддерживаются вложенные структуры: `{_cache.metadata.timestamp}`
- Данные автоматически очищаются после завершения выполнения сценария

</details>


<a id="sleep"></a>
### sleep

**Description:** Delay execution for given seconds

**Input Parameters:**

- **`seconds`** (`float`, required, min: 0.0) — Seconds to delay (float allowed, e.g. 0.5, 22.5)

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "sleep"
  params:
    seconds: "value"
```


<a id="scenario_processor"></a>
## scenario_processor

**Description:** Service for processing events by scenarios

<a id="execute_scenario"></a>
### execute_scenario

**Description:** Execute scenario or array of scenarios by name

**Input Parameters:**

- **`scenario`** (`string|array`) — Scenario name (string) or array of scenario names
- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (passed from context)
- **`return_cache`** (`boolean`, optional) — Return _cache from executed scenario (default true). Only for single scenario (string), ignored for array

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data with scenario execution result
  - **`scenario_result`** (`string`) — Scenario result: success, error, abort, break, stop
  - **`_cache`** (`object`) (optional) — Cache from executed scenario (single scenario only, when return_cache=true). Data in _cache[action_name]

**Usage Example:**

```yaml
# In scenario
- action: "execute_scenario"
  params:
    scenario: "value"
    tenant_id: 123
    # return_cache: boolean (optional)
```


<a id="wait_for_action"></a>
### wait_for_action

**Description:** Wait for async action by action_id. Returns main action result AS IS

**Input Parameters:**

- **`action_id`** (`string`, required, min length: 1) — Unique async action ID to wait for
- **`timeout`** (`integer`, optional, min: 0.0) — Wait timeout in seconds (optional). On timeout returns timeout error; scenario continues; async action keeps running in background.

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result from main action on success, or wait error (timeout/error) on wait failure
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data from main action on success; absent on wait error

**Usage Example:**

```yaml
# In scenario
- action: "wait_for_action"
  params:
    action_id: "example"
    # timeout: integer (optional)
```


<a id="storage_hub"></a>
## storage_hub

**Description:** Service for managing tenant storage

<a id="delete_storage"></a>
### delete_storage

**Description:** Delete values or groups from storage. If key or key_pattern set - delete value, else delete group

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`group_key`** (`string`, optional) — Group key (exact match, takes priority over group_key_pattern)
- **`group_key_pattern`** (`string`, optional, min length: 1) — Pattern for group search (ILIKE, used when group_key not specified)
- **`key`** (`string`, optional) — Attribute key (exact match). If set - delete value, else delete group
- **`key_pattern`** (`string`, optional, min length: 1) — Pattern for key (ILIKE). If set - delete value, else delete group

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, not_found
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "delete_storage"
  params:
    tenant_id: 123
    # group_key: string (optional)
    # group_key_pattern: string (optional)
    # key: string (optional)
    # key_pattern: string (optional)
```


<a id="get_storage"></a>
### get_storage

**Description:** Get storage values for tenant. Supports full values, group, single value, and pattern search

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`group_key`** (`string`, optional) — Group key (exact match, takes priority over group_key_pattern)
- **`group_key_pattern`** (`string`, optional, min length: 1) — Pattern for group search (ILIKE, used when group_key not specified)
- **`key`** (`string`, optional) — Attribute key (exact match, priority over key_pattern). Only when group_key or group_key_pattern specified
- **`key_pattern`** (`string`, optional, min length: 1) — Pattern for key search (ILIKE, used when key not specified). Only when group_key or group_key_pattern specified
- **`format`** (`boolean`, optional) — If true, returns additional formatted_text field with YAML data

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, not_found
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`storage_values`** (`any`) — Requested data. If group_key and key set - raw value. If only group_key - group structure {key: value}. If none - full structure {group_key: {key: value}}
  - **`formatted_text`** (`string`) (optional) — Formatted text in YAML (returned only when format=true)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "get_storage"
  params:
    tenant_id: 123
    # group_key: string (optional)
    # group_key_pattern: string (optional)
    # key: string (optional)
    # key_pattern: string (optional)
    # format: boolean (optional)
```


<a id="get_storage_groups"></a>
### get_storage_groups

**Description:** Get list of unique group keys for tenant. Returns group_key list only (limited by storage_groups_max_limit)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`group_keys`** (`array (of string)`) — List of unique group keys (limited by storage_groups_max_limit)
  - **`is_truncated`** (`boolean`) (optional) — Flag that list was truncated (true if more groups than limit)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "get_storage_groups"
  params:
    tenant_id: 123
```


<a id="set_storage"></a>
### set_storage

**Description:** Set storage values for tenant. Supports full structure via values or partial via group_key/key/value

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID (required)
- **`group_key`** (`string`, optional) — Group key (placeholder support). If set, mixed approach is used
- **`key`** (`string`, optional) — Value key (placeholder support). Used with group_key
- **`value`** (`any`, optional) — Value to set. Used with group_key and key
- **`values`** (`object`, optional) — Structure to set. If group_key set - group {key: value}, else full {group_key: {key: value}}
- **`format`** (`boolean`, optional) — If true, returns additional formatted_text field with YAML data

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`storage_values`** (`any`) — Set data. Single value returns raw value; group returns {key: value}; full returns {group_key: {key: value}}
  - **`formatted_text`** (`string`) (optional) — Formatted text in YAML (returned only when format=true)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "set_storage"
  params:
    tenant_id: 123
    # group_key: string (optional)
    # key: string (optional)
    # value: any (optional)
    # values: object (optional)
    # format: boolean (optional)
```


<a id="telegram_bot_api"></a>
## telegram_bot_api

**Description:** Service for executing actions via Telegram Bot API

<a id="answer_callback_query"></a>
### answer_callback_query

**Description:** Answer callback query (popup notification)

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`callback_query_id`** (`string`, required, min length: 1) — Callback query ID from Telegram
- **`text`** (`string`, optional, max length: 200) — Notification text
- **`show_alert`** (`boolean`, optional) — Show as alert instead of notification
- **`cache_time`** (`integer`, optional, range: 0-3600) — Answer cache time (seconds)

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "answer_callback_query"
  params:
    bot_id: 123
    callback_query_id: "example"
    # text: string (optional)
    # show_alert: boolean (optional)
    # cache_time: integer (optional)
```


<a id="build_keyboard"></a>
### build_keyboard

**Description:** Build keyboard from ID array using templates

**Input Parameters:**

- **`items`** (`array`) — Array of IDs for button generation
- **`keyboard_type`** (`string`, required, values: [`inline`, `reply`]) — Keyboard type (inline or reply)
- **`text_template`** (`string`, required, min length: 1) — Text template with $value$ placeholder
- **`callback_template`** (`string`, optional, min length: 1) — Callback data template for inline (required for inline)
- **`buttons_per_row`** (`integer`, optional, range: 1-8) — Buttons per row

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Build result
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Keyboard data
  - **`keyboard`** (`array`) — Array of button rows
  - **`keyboard_type`** (`string`) — Keyboard type
  - **`rows_count`** (`integer`) — Number of rows
  - **`buttons_count`** (`integer`) — Number of buttons

**Usage Example:**

```yaml
# In scenario
- action: "build_keyboard"
  params:
    items: []
    keyboard_type: "example"
    text_template: "example"
    # callback_template: string (optional)
    # buttons_per_row: integer (optional)
```


<a id="delete_message"></a>
### delete_message

**Description:** Delete message by bot

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`delete_message_id`** (`integer`, optional, min: 1) — Message ID to delete

**Output Parameters:**

- **`result`** (`string`) — Delete result
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "delete_message"
  params:
    bot_id: 123
    # delete_message_id: integer (optional)
```


<a id="restrict_chat_member"></a>
### restrict_chat_member

**Description:** Restrict a user in a supergroup (permission groups: messages, attachments, other, management)

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`chat_id`** (`integer|string`) — Chat ID (supergroup)
- **`target_user_id`** (`integer`) — User ID to restrict (target; does not conflict with context user_id)
- **`messages`** (`boolean`, optional) — Allow text messages, contacts, locations, etc. If omitted — not sent to API
- **`attachments`** (`boolean`, optional) — Allow audio, documents, photos, videos, video notes, voice. If omitted — not sent to API
- **`other`** (`boolean`, optional) — Allow polls, stickers, games, inline, link previews. If omitted — not sent to API
- **`management`** (`boolean`, optional) — Allow change info, invite users, pin messages, manage topics. If omitted — not sent to API
- **`until_date`** (`integer`, optional, min: 0) — Unix time when restrictions are lifted; 0 or omit — forever

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "restrict_chat_member"
  params:
    bot_id: 123
    chat_id: "value"
    target_user_id: 123
    # messages: boolean (optional)
    # attachments: boolean (optional)
    # other: boolean (optional)
    # management: boolean (optional)
    # until_date: integer (optional)
```


<a id="send_message"></a>
### send_message

**Description:** Send message by bot

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`target_chat_id`** (`integer|array|string`, optional) — Chat ID or array of chat IDs
- **`text`** (`string`, optional) — Message text
- **`parse_mode`** (`string`, optional, values: [`HTML`, `Markdown`, `MarkdownV2`]) — Parse mode (HTML, Markdown, MarkdownV2)
- **`message_edit`** (`integer|boolean|string`, optional) — Message ID to edit or flag
- **`message_reply`** (`integer|boolean|string`, optional) — Reply to message: true (reply to current event message), integer/string (message ID)
- **`inline`** (`array`, optional) — Inline keyboard
- **`reply`** (`array`, optional) — Reply keyboard
- **`attachment`** (`array`, optional) — Attachments

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Send result
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data
  - **`last_message_id`** (`integer`) — Sent message ID

**Usage Example:**

```yaml
# In scenario
- action: "send_message"
  params:
    bot_id: 123
    # target_chat_id: integer|array|string (optional)
    # text: string (optional)
    # parse_mode: string (optional)
    # message_edit: integer|boolean|string (optional)
    # message_reply: integer|boolean|string (optional)
    # inline: array (optional)
    # reply: array (optional)
    # attachment: array (optional)
```


<a id="user_hub"></a>
## user_hub

**Description:** Central service for managing user states

<a id="clear_user_state"></a>
### clear_user_state

**Description:** Clear user state

**Input Parameters:**

- **`user_id`** (`integer`, required, min: 1) — Telegram user ID
- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "clear_user_state"
  params:
    user_id: 123
    tenant_id: 123
```


<a id="delete_user_storage"></a>
### delete_user_storage

**Description:** Delete values from user storage

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`user_id`** (`integer`, required, min: 1) — Telegram user ID
- **`key`** (`string`, optional) — Key to delete (exact). If key and key_pattern both unset - delete all user records
- **`key_pattern`** (`string`, optional, min length: 1) — Pattern for keys to delete (ILIKE). If both unset - delete all

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, not_found
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details (e.g. field validation errors)

**Usage Example:**

```yaml
# In scenario
- action: "delete_user_storage"
  params:
    tenant_id: 123
    user_id: 123
    # key: string (optional)
    # key_pattern: string (optional)
```


<a id="get_tenant_users"></a>
### get_tenant_users

**Description:** Get list of all user_id for tenant

**Input Parameters:**

- **`tenant_id`** (`integer`) — Tenant ID

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`user_ids`** (`array (of integer)`) — Array of Telegram user IDs
  - **`user_count`** (`integer`) — Number of users

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "get_tenant_users"
  params:
    tenant_id: 123
```


<a id="get_user_state"></a>
### get_user_state

**Description:** Get user state with expiry check

**Input Parameters:**

- **`user_id`** (`integer`, required, min: 1) — Telegram user ID
- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data
  - 🔀 **`user_state`** (`string`) (optional) — User state or None if expired/not set
  - **`user_state_expired_at`** (`string`) (optional) — State expiry time (ISO) or None if not set

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "get_user_state"
  params:
    user_id: 123
    tenant_id: 123
```


<a id="get_user_storage"></a>
### get_user_storage

**Description:** Get user storage values. Supports full values, single key, or key_pattern search

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`user_id`** (`integer`, required, min: 1) — Telegram user ID
- **`key`** (`string`, optional) — Key for single value (exact match, priority over key_pattern)
- **`key_pattern`** (`string`, optional, min length: 1) — Pattern for key search (ILIKE, used when key not set)
- **`format`** (`boolean`, optional) — If true, returns formatted_text with YAML data

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, not_found
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`user_storage_values`** (`any`) — Requested data. If key set - raw value. If none - full {key: value}
  - **`formatted_text`** (`string`) (optional) — Formatted YAML text (only when format=true)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "get_user_storage"
  params:
    tenant_id: 123
    user_id: 123
    # key: string (optional)
    # key_pattern: string (optional)
    # format: boolean (optional)
```


<a id="get_users_by_storage_value"></a>
### get_users_by_storage_value

**Description:** Find users by storage key and value (e.g. users with subscription)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`key`** (`string`, required, min length: 1) — Storage key to search
- **`value`** (`string|integer|float|boolean|array|object`) — Value to search (primitive or JSON object)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`user_ids`** (`array (of integer)`) — Array of Telegram user IDs where storage[key] == value
  - **`user_count`** (`integer`) — Number of users found

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "get_users_by_storage_value"
  params:
    tenant_id: 123
    key: "example"
    value: "value"
```


<a id="set_user_state"></a>
### set_user_state

**Description:** Set user state

**Input Parameters:**

- **`user_id`** (`integer`, required, min: 1) — Telegram user ID
- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`state`** (`string`, optional) — User state (None or empty to clear)
- **`expires_in_seconds`** (`integer`, optional, min: 0) — Expiry in seconds (None or 0 = forever)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Response data
  - **`user_state`** (`string`) (optional) — User state or None if expired/not set
  - **`user_state_expired_at`** (`string`) (optional) — State expiry time (ISO) or None if not set

**Usage Example:**

```yaml
# In scenario
- action: "set_user_state"
  params:
    user_id: 123
    tenant_id: 123
    # state: string (optional)
    # expires_in_seconds: integer (optional)
```


<a id="set_user_storage"></a>
### set_user_storage

**Description:** Set user storage. Full structure via values or partial via key/value

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`user_id`** (`integer`, required, min: 1) — Telegram user ID
- **`key`** (`string`, optional) — Value key (placeholder support). If set, mixed approach
- **`value`** (`any`, optional) — Value to set. Used with key
- **`values`** (`object`, optional) — Full structure to set {key: value}. Only when key not set
- **`format`** (`boolean`, optional) — If true, returns formatted_text with YAML data

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — 
  - 🔀 **`user_storage_values`** (`any`) — Set data. Single value or full {key: value} structure
  - **`formatted_text`** (`string`) (optional) — Formatted YAML text (only when format=true)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

**Usage Example:**

```yaml
# In scenario
- action: "set_user_storage"
  params:
    tenant_id: 123
    user_id: 123
    # key: string (optional)
    # value: any (optional)
    # values: object (optional)
    # format: boolean (optional)
```


<a id="validator"></a>
## validator

**Description:** Service for validating conditions in scenarios

<a id="validate"></a>
### validate

**Description:** Validate condition and return result

**Input Parameters:**

- **`condition`** (`string`, required, min length: 1) — Condition to validate (supports all condition_parser operators)

**Output Parameters:**

- **`result`** (`string`) — Result: success, failed, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "validate"
  params:
    condition: "example"
```

<details>
<summary>📖 Additional Information</summary>

Поддерживаемые операторы: `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `~`, `!~`, `regex`, `is_null`, `not is_null`

**Плейсхолдеры:**
- ✅ `condition: "{_cache.storage_values.tenant_owner|exists} == True and {_cache.storage_values.tenant_owner|length} > 0"`
- ✅ `condition: "{_cache.storage_values.tenant_id} == 137"`
- ✅ `condition: "{_cache.storage_values.tenant_id} > 100"`

**Маркеры:**
- ✅ `condition: "$user_id > 100"`
- ✅ `condition: "$_cache.storage_values.tenant_owner not is_null"`
- ✅ `condition: "$event_type == 'message' and $user_id > 100"`

</details>

