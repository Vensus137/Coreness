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
- [bot_hub](#bot_hub) (4 actions)
  - [answer_callback_query](#answer_callback_query)
  - [build_keyboard](#build_keyboard)
  - [delete_message](#delete_message)
  - [send_message](#send_message)
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
- [tenant_hub](#tenant_hub) (4 actions)
  - [delete_storage](#delete_storage)
  - [get_storage](#get_storage)
  - [get_storage_groups](#get_storage_groups)
  - [set_storage](#set_storage)
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

## ai_rag_service

**Description:** RAG-расширение для AI Service (векторный поиск и управление embeddings)

<a id="delete_embedding"></a>
### ⭐ delete_embedding

**Description:** Удаление данных из vector_storage по document_id или по дате processed_at

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`document_id`** (`string`, optional) — ID документа для удаления (удаляет все чанки документа). Если указан, остальные параметры игнорируются
- **`until_date`** (`string`, optional) — Удалить чанки с processed_at <= until_date включительно (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'). Можно использовать вместе с since_date
- **`since_date`** (`string`, optional) — Удалить чанки с processed_at >= since_date включительно (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'). Можно использовать вместе с until_date
- **`metadata_filter`** (`object`, optional) — Фильтр по метаданным (JSON объект): например, {'chat_id': 123, 'username': 'user1'}. Используется для фильтрации чанков по сохраненным метаданным. Можно использовать вместе с until_date/since_date

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Информация об ошибке
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — Данные ответа
  - **`deleted_chunks_count`** (`integer`) — Количество удаленных чанков

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

**Description:** Получение последних N чанков по дате created_at (не векторный поиск, просто выборка по дате, сортировка по created_at для правильного порядка истории)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`limit_chunks`** (`integer`, optional, range: 1-200) — Количество чанков (по умолчанию 10 из настроек search_limit_chunks). Работает вместе с limit_chars - сначала выбирается limit_chunks чанков, затем фильтруются по limit_chars
- **`limit_chars`** (`integer`, optional, min: 1) — Лимит по символам (опционально, без ограничения по умолчанию). Работает поверх limit_chunks - после получения limit_chunks чанков они отбираются по порядку (от новых к старым), пока сумма символов не превысит limit_chars. Возвращается столько чанков, сколько влезает в лимит
- **`document_type`** (`string|array`, optional) — Фильтр по типу документа. Строка для одного типа или массив для нескольких типов (например, ['message', 'document'])
- **`document_id`** (`string|array`, optional) — Фильтр по document_id. Строка для одного документа или массив для нескольких (например, ['doc_123', 'doc_456'])
- **`until_date`** (`string`, optional) — Фильтр: искать только чанки с processed_at <= until_date включительно (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'). Можно использовать вместе с since_date
- **`since_date`** (`string`, optional) — Фильтр: искать только чанки с processed_at >= since_date включительно (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'). Можно использовать вместе с until_date
- **`metadata_filter`** (`object`, optional) — Фильтр по метаданным (JSON объект): например, {'chat_id': 123, 'username': 'user1'}. Используется для фильтрации чанков по сохраненным метаданным. Можно комбинировать с другими фильтрами

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Информация об ошибке
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — Данные ответа
  - **`chunks`** (`array`) — Массив найденных чанков (отсортированы по created_at DESC - новые первыми)
  - **`chunks_count`** (`integer`) — Количество найденных чанков

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

**Description:** Сохранение текста в vector_storage с автоматическим разбиением на чанки и генерацией embeddings. Поддерживает сохранение только текста без эмбеддинга через параметр generate_embedding=false

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`text`** (`string`) — Текст для сохранения (будет очищен и разбит на чанки)
- **`document_id`** (`string`, optional) — Уникальный ID документа. Если не указан - будет сгенерирован автоматически через IdSequence (детерминированный по seed)
- **`document_type`** (`string`, required, values: [`knowledge`, `chat_history`, `other`]) — Тип документа: knowledge (база знаний), chat_history (история диалога), other (другое - добавляется в ДОП. КОНТЕКСТ)
- **`role`** (`string`, optional, values: [`system`, `user`, `assistant`]) — Роль для OpenAI messages (по умолчанию 'user'). Используется при формировании контекста в completion
- **`chunk_metadata`** (`object`, optional) — Метаданные чанка (JSON объект): chat_id, username и др. Сохраняется в chunk_metadata и используется для фильтрации при поиске и удалении. Может быть использовано в chunk_format для отображения в контексте AI
- **`model`** (`string`, optional) — Модель для генерации embedding (по умолчанию из настроек ai_client.default_embedding_model)
- **`dimensions`** (`integer`, optional) — Размерность embedding (по умолчанию 1024)
- **`chunk_size`** (`integer`, optional, range: 100-8000) — Размер чанка в символах (по умолчанию 512)
- **`chunk_overlap`** (`integer`, optional, range: 0-500) — Перекрытие между чанками в символах (по умолчанию 100, ~20% от chunk_size). Сохраняет контекст на границах чанков для лучшего поиска
- **`replace_existing`** (`boolean`, optional) — Заменить существующий документ (по умолчанию false - добавить). Если документ существует и replace_existing=false - вернется ошибка ALREADY_EXISTS
- **`generate_embedding`** (`boolean`, optional) — Генерировать ли embedding для чанков (по умолчанию true). Если false - сохраняется только текст без эмбеддинга (полезно для истории без векторного поиска)
- **`created_at`** (`string`, optional) — Реальная дата создания (для правильной сортировки истории). Поддерживает форматы: ISO, YYYY-MM-DD, YYYY-MM-DD HH:MM:SS. Если не указано - используется текущее локальное время
- 🔑 **`ai_token`** (`string`) — AI API ключ из конфига тенанта (_config.ai_token). Требуется только если generate_embedding=true

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки: ALREADY_EXISTS (документ существует), INTERNAL_ERROR, VALIDATION_ERROR
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`document_id`** (`string`) — ID сохраненного документа (переданный или сгенерированный)
  - **`document_type`** (`string`) — Тип документа
  - **`chunks_count`** (`integer`) — Количество созданных чанков
  - **`model`** (`string`) (optional) — Использованная модель embedding (только если generate_embedding=true)
  - **`dimensions`** (`integer`) (optional) — Размерность embedding (только если generate_embedding=true)
  - **`total_tokens`** (`integer`) (optional) — Общее количество токенов во всех чанках (только если generate_embedding=true)
  - **`text_length`** (`integer`) — Длина исходного текста (после очистки)

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
    ai_token: "example"
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

**Description:** Поиск похожих чанков по тексту или вектору (semantic search) через cosine similarity

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`query_text`** (`string`, optional) — Текст запроса для поиска (будет преобразован в embedding). Необходимо указать либо query_text, либо query_vector
- **`query_vector`** (`array`, optional) — Готовый вектор для поиска (массив чисел). Размерность должна совпадать с сохраненными embeddings. Необходимо указать либо query_text, либо query_vector
- **`limit_chunks`** (`integer`, optional, range: 1-200) — Количество результатов (top-k, по умолчанию 10). Работает вместе с limit_chars - сначала выбирается limit_chunks чанков, затем фильтруются по limit_chars
- **`limit_chars`** (`integer`, optional, min: 1) — Лимит по символам (опционально, без ограничения по умолчанию). Работает поверх limit_chunks - после получения limit_chunks чанков они отбираются по порядку (от большего similarity), пока сумма символов не превысит limit_chars. Возвращается столько чанков, сколько влезает в лимит
- **`min_similarity`** (`number`, optional, range: 0.0-1.0) — Минимальный порог схожести (cosine similarity, по умолчанию из настроек search_min_similarity)
- **`document_id`** (`string|array`, optional) — Фильтр по document_id. Строка для одного документа или массив для нескольких (например, ['doc_123', 'doc_456'])
- **`document_type`** (`string|array`, optional) — Фильтр по типу документа. Строка для одного типа или массив для нескольких типов (например, ['message', 'document'])
- **`until_date`** (`string`, optional) — Фильтр: искать только чанки с processed_at <= until_date включительно (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'). Можно использовать вместе с since_date
- **`since_date`** (`string`, optional) — Фильтр: искать только чанки с processed_at >= since_date включительно (формат: 'YYYY-MM-DD' или 'YYYY-MM-DD HH:MM:SS'). Можно использовать вместе с until_date
- **`metadata_filter`** (`object`, optional) — Фильтр по метаданным (JSON объект): например, {'chat_id': 123, 'username': 'user1'}. Используется для фильтрации чанков по сохраненным метаданным. Можно комбинировать с другими фильтрами
- **`model`** (`string`, optional) — Модель для генерации embedding (используется только если указан query_text, по умолчанию из настроек ai_client.default_embedding_model)
- **`dimensions`** (`integer`, optional) — Размерность embedding (используется только если указан query_text, по умолчанию 1024)
- 🔑 **`ai_token`** (`string`) — AI API ключ из конфига тенанта (_config.ai_token). Требуется только если указан query_text

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Информация об ошибке
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
- **`response_data`** (`object`) — Данные ответа
  - **`chunks`** (`array`) — Массив найденных чанков
  - **`chunks_count`** (`integer`) — Количество найденных чанков

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
    ai_token: "example"
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


## ai_service

**Description:** Сервис для интеграции ИИ в сценарии

<a id="completion"></a>
### completion

**Description:** AI completion через ИИ

**Input Parameters:**

- **`prompt`** (`string`) — Текст запроса пользователя
- **`system_prompt`** (`string`, optional) — Системный промпт для контекста
- **`model`** (`string`, optional) — Модель AI (по умолчанию из настроек)
- **`max_tokens`** (`integer`, optional) — Максимальное количество токенов (по умолчанию из настроек)
- **`temperature`** (`float`, optional, range: 0.0-2.0) — Температура генерации (по умолчанию из настроек)
- **`context`** (`string`, optional) — Кастомный контекст (добавляется в финальное user сообщение в блок ДОП. КОНТЕКСТ вместе с other чанками из rag_chunks)
- **`rag_chunks`** (`array`, optional) — Массив чанков из RAG поиска для автоматического формирования messages. Чанки группируются по типам: chat_history (диалог), knowledge (база знаний), other (другое - добавляется в ДОП. КОНТЕКСТ). Формат: [{content, document_type, role, processed_at, ...}]
- **`json_mode`** (`string`, optional, values: [`json_object`, `json_schema`]) — Режим JSON для структурированного ответа: 'json_object' или 'json_schema'
- **`json_schema`** (`object`, optional) — JSON схема для режима json_schema (обязательна при json_mode='json_schema')
- **`tools`** (`array`, optional) — Список доступных функций для вызова моделью (tool calling)
- **`tool_choice`** (`string`, optional) — Управление выбором инструментов: 'none', 'auto', 'required' или объект с конкретной функцией
- **`chunk_format`** (`object`, optional) — Формат отображения чанков в контексте. Шаблоны используют маркеры $ для подстановки значений: $content (обязательно) + любые поля из chunk_metadata. Поддерживается модификатор fallback: $field|fallback:значение. Маркеры работают только с данными чанка (content + chunk_metadata), не затрагивая общий контекст.
- 🔑 **`ai_token`** (`string`) — AI API ключ из конфига тенанта (_config.ai_token)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error, timeout
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`response_completion`** (`string`) — Completion ответ от ИИ
  - **`prompt_tokens`** (`integer`) — Токены на вход (prompt + context)
  - **`completion_tokens`** (`integer`) — Токены на выход (сгенерированный ответ)
  - **`total_tokens`** (`integer`) — Общее количество токенов (prompt + completion)
  - **`model`** (`string`) — Использованная модель
  - **`response_dict`** (`object`) (optional) — Распарсенный словарь из JSON ответа (только при использовании json_mode)
  - **`tool_calls`** (`array`) (optional) — Список вызовов функций, которые модель решила выполнить (только при использовании tools)

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
- Параметр `tools` позволяет модели вызывать функции
- Модель решает, какие функции вызвать и с какими параметрами
- Результаты вызовов в `response_data.tool_calls`
- `tool_choice`: управление выбором ('none', 'auto', 'required', или конкретная функция)

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

**Description:** Генерация embedding для текста через ИИ

**Input Parameters:**

- **`text`** (`string`) — Текст для генерации embedding
- **`model`** (`string`, optional) — Модель для генерации embedding (по умолчанию из настроек ai_client.default_embedding_model)
- **`dimensions`** (`integer`, optional) — Размерность embedding (по умолчанию из настроек ai_client.default_embedding_dimensions). Поддерживается только для OpenAI text-embedding-3-small и text-embedding-3-large
- 🔑 **`ai_token`** (`string`) — AI API ключ из конфига тенанта (_config.ai_token)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`embedding`** (`array`) — Вектор embedding (список чисел)
  - **`model`** (`string`) — Использованная модель
  - **`dimensions`** (`integer`) — Размерность embedding
  - **`total_tokens`** (`integer`) — Общее количество токенов

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


## bot_hub

**Description:** Центральный сервис для управления всеми ботами

<a id="answer_callback_query"></a>
### answer_callback_query

**Description:** Ответ на callback query (всплывающее уведомление или простое уведомление при нажатии на inline-кнопку)

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`callback_query_id`** (`string`, required, min length: 1) — ID callback query (можно использовать плейсхолдер {callback_id} из события)
- **`text`** (`string`, optional, max length: 200) — Текст уведомления (до 200 символов). Если не указан, показывается простое уведомление без текста
- **`show_alert`** (`boolean`, optional) — Показать всплывающее окно (alert). По умолчанию false - простое уведомление вверху экрана. true - модальное окно с текстом
- **`cache_time`** (`integer`, optional, range: 0-3600) — Время кэширования ответа в секундах (0-3600). По умолчанию 0

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

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

**Description:** Построение клавиатуры из массива ID с использованием шаблонов

**Input Parameters:**

- **`items`** (`array`) — Массив ID для генерации кнопок (например, [1, 2, 3] или tenant_ids из get_tenants_list)
- **`keyboard_type`** (`string`, required, values: [`inline`, `reply`]) — Тип клавиатуры: 'inline' или 'reply'
- **`text_template`** (`string`, required, min length: 1) — Шаблон текста кнопки с плейсхолдером $value$ (например, 'Tenant $value$' или 'Пользователь #$value$'). Используется синтаксис $value$ вместо {value} чтобы избежать конфликта с системой плейсхолдеров
- **`callback_template`** (`string`, optional, min length: 1) — Шаблон callback_data для inline клавиатуры с плейсхолдером $value$ (обязателен для inline, например, 'select_tenant_$value$'). Используется синтаксис $value$ вместо {value} чтобы избежать конфликта с системой плейсхолдеров
- **`buttons_per_row`** (`integer`, optional, range: 1-8) — Количество кнопок в строке (по умолчанию 1, например, 2 для двух кнопок в ряд)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`keyboard`** (`array`) — Готовая клавиатура в формате массива строк (можно использовать напрямую в параметре inline или reply действия send_message)
  - **`keyboard_type`** (`string`) — Тип клавиатуры: 'inline' или 'reply'
  - **`rows_count`** (`integer`) — Количество строк в клавиатуре
  - **`buttons_count`** (`integer`) — Общее количество кнопок в клавиатуре

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

**Description:** Удаление сообщения ботом

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`delete_message_id`** (`integer`, optional, min: 1) — ID сообщения для удаления. Если не указан, используется message_id из контекста события. Chat ID по умолчанию берется из события (chat_id), если не указан явно

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

**Usage Example:**

```yaml
# In scenario
- action: "delete_message"
  params:
    bot_id: 123
    # delete_message_id: integer (optional)
```


<a id="send_message"></a>
### send_message

**Description:** Отправка сообщения ботом

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`target_chat_id`** (`integer|array|string`, optional) — ID чата или массив ID чатов для отправки (по умолчанию берется chat_id из события)
- **`text`** (`string`, optional) — Текст сообщения (может быть пустым, если есть вложение)
- **`parse_mode`** (`string`, optional, values: [`HTML`, `Markdown`, `MarkdownV2`]) — Режим парсинга (HTML, Markdown, MarkdownV2)
- **`message_edit`** (`integer|boolean|string`, optional) — Редактирование сообщения: integer (ID сообщения) или true/false. При редактировании работа происходит только с первым чатом из списка (по умолчанию редактирует текущее сообщение из события)
- **`message_reply`** (`integer`, optional, min: 1) — ID сообщения для ответа
- **`inline`** (`array`, optional) — Inline клавиатура (массив строк с кнопками). Можно указать только одну клавиатуру (inline или reply) - это ограничение Telegram API. Если указаны обе клавиатуры, используется inline (имеет приоритет)
- **`reply`** (`array`, optional) — Reply клавиатура (массив строк с кнопками). Можно указать только одну клавиатуру (inline или reply) - это ограничение Telegram API. Если указаны обе клавиатуры, используется inline (имеет приоритет)
- **`attachment`** (`array`, optional) — Вложения (файлы, фото, видео и т.д.)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - 🔀 **`last_message_id`** (`integer`) — ID последнего отправленного сообщения (при отправке в несколько чатов возвращается ID первого отправленного)

**Note:**
- 🔀 — field that can be renamed via `_response_key` parameter for convenient data access

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
    # message_reply: integer (optional)
    # inline: array (optional)
    # reply: array (optional)
    # attachment: array (optional)
```


## invoice_service

**Description:** Сервис для работы с инвойсами (создание, управление, обработка платежей)

<a id="cancel_invoice"></a>
### cancel_invoice

**Description:** Отмена инвойса (установка флага is_cancelled)

**Input Parameters:**

- **`invoice_id`** (`integer`, required, min: 1) — ID инвойса (обязательно)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "cancel_invoice"
  params:
    invoice_id: 123
```


<a id="confirm_payment"></a>
### confirm_payment

**Description:** Подтверждение платежа (ответ на pre_checkout_query с подтверждением)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`pre_checkout_query_id`** (`string`, required, min length: 1) — ID запроса на подтверждение (обязательно)
- **`invoice_payload`** (`string`, optional, min length: 1) — ID инвойса из payload (опционально, для проверки статуса инвойса перед подтверждением)
- **`error_message`** (`string`, optional) — Сообщение об ошибке при отклонении платежа (опционально, используется если инвойс отменен или уже оплачен)

**Output Parameters:**

- **`result`** (`string`) — Результат: success (платеж подтвержден), failed (платеж отклонен по бизнес-логике), error (техническая ошибка)
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки. Возможные значения: INVOICE_CANCELLED (при result=failed - инвойс отменен), INVOICE_ALREADY_PAID (при result=failed - инвойс уже оплачен)
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

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

**Description:** Создание инвойса в БД и отправка/создание ссылки

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`target_user_id`** (`integer`, optional, min: 1) — ID пользователя для создания инвойса (опционально, по умолчанию user_id из события)
- **`chat_id`** (`integer`, optional) — ID чата для отправки (обязательно для отправки, не нужен для ссылки)
- **`title`** (`string`, required, min length: 1) — Название товара/услуги (обязательно)
- **`description`** (`string`, optional) — Описание товара/услуги
- **`amount`** (`integer`, required, min: 1) — Количество звезд (обязательно, целое число)
- **`currency`** (`string`, optional) — Валюта (по умолчанию XTR для звезд)
- **`as_link`** (`boolean`, optional) — Создать как ссылку вместо отправки (по умолчанию false - отправка)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа
  - **`invoice_id`** (`integer`) — ID созданного инвойса
  - **`invoice_message_id`** (`integer`) (optional) — ID отправленного сообщения с инвойсом (если as_link=false)
  - **`invoice_link`** (`string`) (optional) — Ссылка на инвойс (если as_link=true)

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
    # description: string (optional)
    amount: 123
    # currency: string (optional)
    # as_link: boolean (optional)
```


<a id="get_invoice"></a>
### get_invoice

**Description:** Получение информации об инвойсе

**Input Parameters:**

- **`invoice_id`** (`integer`, required, min: 1) — ID инвойса (обязательно)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа
  - **`invoice`** (`object`) — Данные инвойса

**Usage Example:**

```yaml
# In scenario
- action: "get_invoice"
  params:
    invoice_id: 123
```


<a id="get_user_invoices"></a>
### get_user_invoices

**Description:** Получение всех инвойсов пользователя

**Input Parameters:**

- **`target_user_id`** (`integer`, optional, min: 1) — ID пользователя для получения инвойсов (опционально, по умолчанию user_id из события)
- **`include_cancelled`** (`boolean`, optional) — Включать отмененные инвойсы (по умолчанию false)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа
  - **`invoices`** (`array`) — Массив инвойсов пользователя

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

**Description:** Отметить инвойс как оплаченный (обработка события payment_successful)

**Input Parameters:**

- **`invoice_payload`** (`string`, required, min length: 1) — ID инвойса из payload события (обязательно)
- **`telegram_payment_charge_id`** (`string`, required, min length: 1) — ID платежа в Telegram (обязательно)
- **`paid_at`** (`string`, optional) — Дата оплаты (опционально, по умолчанию текущая дата)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

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

**Description:** Отклонение платежа (ответ на pre_checkout_query с отклонением)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`pre_checkout_query_id`** (`string`, required, min length: 1) — ID запроса на подтверждение (обязательно)
- **`error_message`** (`string`, optional) — Сообщение об ошибке (опционально)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

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


## scenario_helper

**Description:** Вспомогательные утилиты для управления выполнением сценариев

<a id="check_value_in_array"></a>
### check_value_in_array

**Description:** Проверка наличия значения в массиве

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
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
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

**Description:** Выбор случайных элементов из массива без повторений

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

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
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

**Description:** Форматирование структурированных данных (JSON/YAML) в текстовый формат для промптов и сообщений

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

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
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

**Description:** Генерация массива случайных чисел в заданном диапазоне (по умолчанию без повторений)

**Input Parameters:**

- **`min`** (`integer`) — Минимальное значение (включительно)
- **`max`** (`integer`) — Максимальное значение (включительно)
- **`count`** (`integer`, required, min: 1) — Количество чисел для генерации
- **`seed`** (`any`, optional) — Seed для детерминированной генерации (опционально, может быть числом, строкой или другим типом)
- **`allow_duplicates`** (`boolean`, optional) — Разрешить повторения в массиве (по умолчанию false - без повторений)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`random_list`** (`array`) — Массив сгенерированных чисел
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

**Description:** Генерация случайного целого числа в заданном диапазоне

**Input Parameters:**

- **`min`** (`integer`) — Минимальное значение (включительно)
- **`max`** (`integer`) — Максимальное значение (включительно)
- **`seed`** (`any`, optional) — Seed для детерминированной генерации (опционально, может быть числом, строкой или другим типом)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`random_value`** (`integer`) — Сгенерированное случайное число
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

**Description:** Генерация уникального ID через автоинкремент в БД (детерминированная генерация - при одинаковых seed возвращает тот же ID). Если seed не указан, генерируется случайный UUID

**Input Parameters:**

- **`seed`** (`string`, optional, min length: 1) — Seed для генерации ID. При повторном запросе с тем же seed вернется тот же ID. Если не указан, генерируется случайный UUID

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
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

**Description:** Модификация массива: добавление, удаление элементов или очистка

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
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
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

**Description:** Установка временных данных в кэш сценария. Все переданные параметры возвращаются в response_data и автоматически попадают в плоский _cache по умолчанию.

**Input Parameters:**

- **`cache`** (`object`) — Объект с данными для установки в кэш. Все переданные параметры будут доступны в последующих шагах сценария через {_cache.ключ} (плоский доступ по умолчанию)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
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

**Description:** Задержка выполнения на указанное количество секунд

**Input Parameters:**

- **`seconds`** (`float`, required, min: 0.0) — Количество секунд задержки (можно использовать дробные значения, например 0.5 или 22.5)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sleep"
  params:
    seconds: "value"
```


## scenario_processor

**Description:** Сервис для обработки событий по сценариям

<a id="execute_scenario"></a>
### execute_scenario

**Description:** Выполнение сценария или массива сценариев по имени

**Input Parameters:**

- **`scenario`** (`string|array`) — Название сценария (строка) или массив названий сценариев
- **`tenant_id`** (`integer`, required, min: 1) — ID tenant'а (передается автоматически из контекста)
- **`return_cache`** (`boolean`, optional) — Возвращать ли _cache из выполненного сценария (по умолчанию true). ВАЖНО: работает только для одиночных сценариев (строка), для массива сценариев игнорируется и кэш не возвращается

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа с результатом выполнения сценария
  - **`scenario_result`** (`string`) — Результат выполнения сценария: success, error, abort, break, stop
  - **`_cache`** (`object`) (optional) — Кэш из выполненного сценария, возвращается только для одиночных сценариев (не для массива), если return_cache=true и в сценарии был установлен _cache через set_cache. Данные попадают в _cache[action_name] автоматически

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

**Description:** Ожидание завершения асинхронного действия по action_id. Возвращает результат основного действия AS IS (как будто оно выполнилось напрямую)

**Input Parameters:**

- **`action_id`** (`string`, required, min length: 1) — Уникальный ID асинхронного действия для ожидания
- **`timeout`** (`integer`, optional, min: 0.0) — Таймаут ожидания в секундах (опционально). При истечении таймаута wait_for_action возвращает ошибку timeout, но выполнение сценария продолжается. Основное асинхронное действие продолжает выполняться в фоне даже после таймаута.

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат зависит от основного действия: если основное действие завершилось успешно - возвращается его результат (success/error и т.д.), если ошибка ожидания (таймаут, Future не найден) - возвращается ошибка wait_for_action (timeout/error)
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа. Если основное действие завершилось успешно - возвращаются данные основного действия (полностью подменяются), если ошибка ожидания - отсутствует

**Usage Example:**

```yaml
# In scenario
- action: "wait_for_action"
  params:
    action_id: "example"
    # timeout: integer (optional)
```


## tenant_hub

**Description:** Сервис для управления конфигурациями тенантов - координатор загрузки данных

<a id="delete_storage"></a>
### delete_storage

**Description:** Удаление значений или групп из storage. Если указан key или key_pattern - удаляется значение, иначе удаляется группа

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`group_key`** (`string`, optional) — Ключ группы (точное совпадение, приоритет над group_key_pattern)
- **`group_key_pattern`** (`string`, optional, min length: 1) — Паттерн для поиска группы (ILIKE, используется если group_key не указан)
- **`key`** (`string`, optional) — Ключ атрибута (точное совпадение, приоритет над key_pattern). Если указан - удаляется значение, иначе удаляется группа
- **`key_pattern`** (`string`, optional, min length: 1) — Паттерн для поиска ключа (ILIKE, используется если key не указан). Если указан - удаляется значение, иначе удаляется группа

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error, not_found
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

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

**Description:** Получение значений storage для тенанта. Поддерживает получение всех значений, группы, конкретного значения, а также поиск по паттернам

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`group_key`** (`string`, optional) — Ключ группы (точное совпадение, приоритет над group_key_pattern)
- **`group_key_pattern`** (`string`, optional, min length: 1) — Паттерн для поиска группы (ILIKE, используется если group_key не указан)
- **`key`** (`string`, optional) — Ключ атрибута (точное совпадение, приоритет над key_pattern). Используется только если указан group_key или group_key_pattern
- **`key_pattern`** (`string`, optional, min length: 1) — Паттерн для поиска ключа (ILIKE, используется если key не указан). Используется только если указан group_key или group_key_pattern
- **`format`** (`boolean`, optional) — Если true, возвращает дополнительное поле formatted_text с данными в формате YAML

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error, not_found
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`storage_values`** (`any`) — Запрошенные данные. Если указаны group_key и key - возвращается прямое значение (примитив или объект как есть). Если указан только group_key - возвращается структура группы {key: value}. Если ничего не указано - возвращается полная структура {group_key: {key: value}}
  - **`formatted_text`** (`string`) (optional) — Отформатированный текст в формате YAML (возвращается только если format=true)

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

**Description:** Получение списка уникальных ключей групп для тенанта. Возвращает только список group_key без значений (с ограничением на количество групп)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`group_keys`** (`array`) — Список уникальных ключей групп (ограничен настройкой storage_groups_max_limit)
  - **`is_truncated`** (`boolean`) (optional) — Флаг, указывающий что список был обрезан (true если групп больше лимита, иначе поле отсутствует)

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

**Description:** Установка значений storage для тенанта. Поддерживает смешанный подход: полная структура через values или частичная через group_key/key/value

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта (обязательно)
- **`group_key`** (`string`, optional) — Ключ группы (с поддержкой плейсхолдеров). Если указан, используется смешанный подход
- **`key`** (`string`, optional) — Ключ значения (с поддержкой плейсхолдеров). Используется вместе с group_key
- **`value`** (`any`, optional) — Значение для установки. Используется вместе с group_key и key
- **`values`** (`object`, optional) — Структура для установки. Если указан group_key - структура для группы {key: value}, иначе полная структура {group_key: {key: value}}
- **`format`** (`boolean`, optional) — Если true, возвращает дополнительное поле formatted_text с данными в формате YAML

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`storage_values`** (`any`) — Установленные данные. Если установлено одно значение (group_key + key + value) - возвращается прямое значение (примитив или объект как есть). Если установлена группа (group_key + values) - возвращается структура группы {key: value}. Если установлена полная структура (values) - возвращается полная структура {group_key: {key: value}}
  - **`formatted_text`** (`string`) (optional) — Отформатированный текст в формате YAML (возвращается только если format=true)

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


## user_hub

**Description:** Центральный сервис для управления состояниями пользователей

<a id="clear_user_state"></a>
### clear_user_state

**Description:** Очистка состояния пользователя

**Input Parameters:**

- **`user_id`** (`integer`, required, min: 1) — ID пользователя Telegram
- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

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

**Description:** Удаление значений из storage пользователя

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`user_id`** (`integer`, required, min: 1) — ID пользователя Telegram
- **`key`** (`string`, optional) — Ключ для удаления конкретного значения (точное совпадение, приоритет над key_pattern). Если не указаны key и key_pattern - удаляются все записи пользователя
- **`key_pattern`** (`string`, optional, min length: 1) — Паттерн для поиска ключей для удаления (ILIKE, используется если key не указан). Если не указаны key и key_pattern - удаляются все записи пользователя

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error, not_found
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

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

**Description:** Получение списка всех user_id для указанного тенанта

**Input Parameters:**

- **`tenant_id`** (`integer`) — ID тенанта

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`user_ids`** (`array`) — Массив ID пользователей Telegram
  - **`user_count`** (`integer`) — Количество пользователей

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

**Description:** Получение состояния пользователя с проверкой истечения

**Input Parameters:**

- **`user_id`** (`integer`, required, min: 1) — ID пользователя Telegram
- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа
  - 🔀 **`user_state`** (`string`) (optional) — Состояние пользователя или None если истекло/не установлено
  - **`user_state_expired_at`** (`string`) (optional) — Время истечения состояния (ISO) или None если не установлено

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

**Description:** Получение значений storage для пользователя. Поддерживает получение всех значений, конкретного значения (key) или поиск по паттерну (key_pattern)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`user_id`** (`integer`, required, min: 1) — ID пользователя Telegram
- **`key`** (`string`, optional) — Ключ для получения конкретного значения (точное совпадение, приоритет над key_pattern)
- **`key_pattern`** (`string`, optional, min length: 1) — Паттерн для поиска ключей (ILIKE, используется если key не указан)
- **`format`** (`boolean`, optional) — Если true, возвращает дополнительное поле formatted_text с данными в формате YAML

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error, not_found
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`user_storage_values`** (`any`) — Запрошенные данные. Если указан key - возвращается прямое значение (примитив или объект как есть). Если ничего не указано - возвращается полная структура {key: value}
  - **`formatted_text`** (`string`) (optional) — Отформатированный текст в формате YAML (возвращается только если format=true)

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

**Description:** Поиск пользователей по ключу и значению в storage. Позволяет найти всех пользователей, у которых в storage есть определенный ключ с определенным значением (например, найти всех пользователей с подключенной подпиской)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`key`** (`string`, required, min length: 1) — Ключ для поиска в storage
- **`value`** (`string|integer|float|boolean|array|object`) — Значение для поиска (может быть простым типом или JSON объектом)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`user_ids`** (`array`) — Массив ID пользователей Telegram, у которых storage[key] == value
  - **`user_count`** (`integer`) — Количество найденных пользователей

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

**Description:** Установка состояния пользователя

**Input Parameters:**

- **`user_id`** (`integer`, required, min: 1) — ID пользователя Telegram
- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`state`** (`string`, optional) — Состояние пользователя (None или пустая строка для сброса)
- **`expires_in_seconds`** (`integer`, optional, min: 0) — Время истечения в секундах (None или 0 = навсегда, устанавливается 3000 год)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа
  - **`user_state`** (`string`) (optional) — Состояние пользователя или None если истекло/не установлено
  - **`user_state_expired_at`** (`string`) (optional) — Время истечения состояния (ISO) или None если не установлено

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

**Description:** Установка значений storage для пользователя. Поддерживает смешанный подход: полная структура через values или частичная через key/value

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`user_id`** (`integer`, required, min: 1) — ID пользователя Telegram
- **`key`** (`string`, optional) — Ключ значения (с поддержкой плейсхолдеров). Если указан, используется смешанный подход
- **`value`** (`any`, optional) — Значение для установки. Используется вместе с key
- **`values`** (`object`, optional) — Полная структура для установки {key: value}. Используется только если не указан key
- **`format`** (`boolean`, optional) — Если true, возвращает дополнительное поле formatted_text с данными в формате YAML

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

- **`_response_key`** (`string`) (optional) — Custom name for main result field (marked 🔀). If specified, main field will be saved in `_cache` under specified name instead of standard. Access via `{_cache.{_response_key}}`. Works only for actions that support renaming main field.

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - 🔀 **`user_storage_values`** (`any`) — Установленные данные. Если установлено одно значение (key + value) - возвращается прямое значение (примитив или объект как есть). Если установлена структура (values без key) - возвращается структура {key: value}
  - **`formatted_text`** (`string`) (optional) — Отформатированный текст в формате YAML (возвращается только если format=true)

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


## validator

**Description:** Сервис для валидации условий в сценариях

<a id="validate"></a>
### validate

**Description:** Валидация условия с возвратом результата

**Input Parameters:**

- **`condition`** (`string`, required, min length: 1) — Условие для валидации (поддерживает все операторы condition_parser)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, failed, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

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

