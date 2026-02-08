---
title: Practical Scenario Examples
description: Step-by-step guide to building Telegram bots with Coreness. Quick start, examples with payments, RAG storage and AI models.
keywords: telegram bot examples, coreness quick start, RAG examples, bot payments, AI agents examples
---

# 📚 Practical Scenario Examples

> **📖 Collection of practical examples** — from quick start to advanced scenarios with payments, RAG storage, and complex logic.

## 🚀 Quick Start

Welcome to Coreness! This section will help you quickly create your first bot and configure your first scenario.

### Basic Concepts

**Tenants** — your bots and their configuration. Each tenant has its own ID, bot token, set of scenarios, and attribute storage.

**Scenarios** — bot logic: commands, menus, message handling. Consist of triggers (when to launch) and steps (what to do). Can be launched by events (commands, messages) or by schedule (scheduled scenarios).

**Scenario Organization** — scenarios can be organized in folders and subfolders for convenience. All YAML files from `scenarios/` folder (including subfolders) are automatically loaded. Scenario names must be unique within the tenant.

**Storage** — tenant attribute storage in key-value format. Allows flexible storage of settings, limits, features, and other data without changing DB schema.

**Placeholders** — dynamic data substitution from event or previous actions. For example: `{username}`, `{user_id}`, `{event_text}`.

**System and public tenants:** By default you can work with the platform using **system tenants** (ID < 100): configuration lives in the project folder `config/tenant/`, no GitHub required. **Public tenants** (ID ≥ 100) use an external repository and require separate setup — see [Public Tenants (Optional)](#public-tenants-optional).

### Creating First Scenario (System Tenant)

Use a system tenant to get started immediately without configuring a repository. Folder structure and scenario format are the same for all tenant types; only the ID range and configuration source differ.

#### 1. Configure Tenant

Create a folder under `config/tenant/` using format `tenant_<ID>` with **ID < 100** (e.g. `tenant_10/`). The project already includes a system tenant `tenant_1/` (master bot) by default — you can use it or take it as a reference.

#### 2. Configure Bot

Inside the tenant folder create `bots/telegram.yaml` (folder `bots/` can contain configs for different bots):

```yaml
# bots/telegram.yaml
bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
is_active: true
```

#### 3. Create Scenarios

Create a `scenarios/` folder inside the tenant folder and add scenario files (subfolders are allowed for organization).

#### 4. Write Scenario

For example in `scenarios/start.yaml`:

```yaml
start:
  trigger:
    - event_type: "message"
      event_text: "/start"
  
  step:
    - action: "send_message"
      params:
        text: |
          👋 Hello, {first_name|fallback:friend}!
          
          Welcome to the bot!
        inline:
          - [{"📋 Menu": "menu"}, {"📚 Help": "help"}]
        
        # Attach file (optional)
        # Can use file_id from event: {event_attachment[0].file_id}
        attachment:
          - file_id: "AgACAgIAAxkBAAIUJWjyLorr_d8Jwof3V_gVjVNdGHyXAAJ--zEb4vGQS-a9UiGzpkTNAQADAgADeQADNgW"
            type: "photo"
```

**What happens in this example:**
- **`trigger`** — launch condition (command `/start`)
- **`step`** — action sequence
- **`{first_name|fallback:friend}`** — placeholder with modifier
- **`inline`** — buttons under message
- **`attachment`** — forwarding files (photos, documents, videos) from events or by file_id

📖 More about actions, parameters and placeholders: [Scenario guide](../guides/SCENARIO_CONFIG_GUIDE), [Actions guide](../reference/ACTION_GUIDE)

### Applying Changes (System Tenant)

System tenant configuration is read from the local `config/tenant/` folder. After editing scenarios or `bots/telegram.yaml`:

1. Open **master bot**
2. Send command `/tenant`
3. Enter your tenant ID (if not already selected)
4. Click **"Synchronize"**

The system will pick up changes from local files and update data. No GitHub repository is used for system tenants.

### Public Tenants (Optional)

If you need a **public tenant** (ID ≥ 100) — e.g. for a client bot whose config lives in an external repository — folder structure and scenario format are the same: `tenant_<ID>/`, `bots/telegram.yaml`, `scenarios/`, etc. The only difference is system setup:

- Configuration is stored in an **external repository** (Repository-Tenant), not in the project folder.
- Syncing changes: **polling** (periodic repository check) or **webhooks** (extension). After pushing to the repository, tenants are picked up on the next check or manually via master bot (command `/tenant` → "Synchronize").

📖 Tenant types and synchronization: [Tenant configuration guide](../guides/TENANT_CONFIG_GUIDE).

## 💳 Advanced Examples

### Working with Payments (Invoices)

System supports working with payments through Telegram Stars (invoices). Mechanism requires handling two events: `pre_checkout_query` (confirmation request) and `payment_successful` (successful payment).

#### Payment Mechanism Overview

**How payment works in Telegram:**

1. **Invoice creation** — bot creates invoice via `create_invoice` and sends it to user
2. **User clicks "Pay"** → Telegram sends `pre_checkout_query` event
3. **Bot must respond within 10 seconds** — confirm or reject payment via `confirm_payment` or `reject_payment`
4. **After confirmation** → Telegram processes payment and sends `payment_successful` event
5. **Handling successful payment** — bot processes `payment_successful` event via `mark_invoice_as_paid`

**⚠️ Critical:**
- Must respond to `pre_checkout_query` event within **10 seconds**, otherwise payment will be automatically rejected
- `invoice_payload` in events — string with `invoice_id` that was passed when creating invoice
- Need to handle both events: `pre_checkout_query` (confirmation) and `payment_successful` (final processing)

#### Creating Invoice

**Action:** `create_invoice`

**What it does:**
- Creates invoice in DB
- Sends invoice to chat (or creates link if `as_link=true`)
- Returns `invoice_id` used as `payload` in events

**Example:**

```yaml
create_payment:
  description: "Creating invoice for payment"
  trigger:
    - event_type: "message"
      event_text: "/buy"
  
  step:
    - action: "create_invoice"
      params:
        title: "Premium Subscription"
        description: "Access to premium features for 1 month"
        amount: 100  # 100 stars
        currency: "XTR"  # Default XTR, can omit
        # as_link: false  # Default false - send to chat
        # chat_id: "{chat_id}"  # Optional, if need to send to another chat
```

**Result:**
- `invoice_id` — created invoice ID (used for further work with invoice)
- `invoice_message_id` — sent message ID with invoice (if sent to chat, optional)
- `invoice_link` — invoice link (if `as_link=true`, optional)

**Important:** `invoice_id` automatically passed to Telegram as `payload` (string). This `payload` will come in `pre_checkout_query` and `payment_successful` events as `invoice_payload`.

#### Handling pre_checkout_query

**Event:** `pre_checkout_query`

**When occurs:** User clicks "Pay" in invoice, but before payment processing.

**⚠️ Critical:** Must respond within **10 seconds**, otherwise payment will be automatically rejected.

**Available event fields:**
- `pre_checkout_query_id` — confirmation request ID (required for response)
- `invoice_payload` — invoice ID (string)
- `currency` — payment currency (usually `"XTR"`)
- `total_amount` — payment amount in minimal currency units

**Response actions:**
- `confirm_payment` — confirm payment
- `reject_payment` — reject payment

**Handling example (recommended):**

```yaml
handle_pre_checkout:
  description: "Handling payment confirmation request"
  trigger:
    - event_type: "pre_checkout_query"
  
  step:
    # FIRST confirm payment (critical for Telegram - ~10 sec timeout)
    # Pass invoice_payload for automatic invoice status check
    # confirm_payment automatically checks if invoice cancelled or already paid
    - action: "confirm_payment"
      params:
        pre_checkout_query_id: "{pre_checkout_query_id}"
        invoice_payload: "{invoice_payload}"  # Automatic status check
    
    # THEN send informational message (don't block confirmation)
    - action: "send_message"
      params:
        text: |
          ✅ Payment confirmed!
          
          Request ID: {pre_checkout_query_id}
          Invoice ID: {invoice_payload}
          Amount: {total_amount} {currency}
```

**⚠️ Important:** If invoice cancelled or already paid, `confirm_payment` automatically rejects payment and returns `result: "failed"` with error code:
- `INVOICE_CANCELLED` — invoice cancelled
- `INVOICE_ALREADY_PAID` — invoice already paid

These codes can be used for handling in scenarios via `validate` and `transitions`.

#### Handling payment_successful

**Event:** `payment_successful`

**When occurs:** After successful payment processing via invoice.

**Available event fields:**
- `invoice_payload` — invoice ID (string)
- `telegram_payment_charge_id` — Telegram payment ID (required for `mark_invoice_as_paid`)
- `currency` — payment currency
- `total_amount` — payment amount

**Action:** `mark_invoice_as_paid`

**What it does:**
- Marks invoice as paid in DB
- Saves `telegram_payment_charge_id` and payment date

**Handling example:**

```yaml
handle_payment_successful:
  description: "Handling successful payment"
  trigger:
    - event_type: "payment_successful"
  
  step:
    # Step 1: Mark invoice as paid
    - action: "mark_invoice_as_paid"
      params:
        invoice_payload: "{invoice_payload}"
        telegram_payment_charge_id: "{telegram_payment_charge_id}"
        paid_at: "{event_date}"  # Optional, default current date
    
    # Step 2: Send confirmation to user
    - action: "send_message"
      params:
        text: |
          ✅ Payment successfully processed!
          
          Invoice ID: {invoice_payload}
          Payment ID: {telegram_payment_charge_id}
          Amount: {total_amount} {currency}
    
    # Step 3: Can perform additional actions
    # E.g., activate subscription, grant access, etc.
    - action: "set_user_storage"
      params:
        key: "premium_active"
        value: true
```

#### Complete Example: Payment Flow

**Complete flow from invoice creation to payment processing:**

```yaml
# 1. Invoice creation
create_payment:
  description: "Creating invoice for payment"
  trigger:
    - event_type: "message"
      event_text: "/buy"
  
  step:
    - action: "create_invoice"
      params:
        title: "Premium Subscription"
        description: "Access to premium features for 1 month"
        amount: 100
        currency: "XTR"

# 2. Handling pre_checkout_query (payment confirmation)
handle_pre_checkout:
  description: "Handling payment confirmation request"
  trigger:
    - event_type: "pre_checkout_query"
  
  step:
    # Confirm payment (with automatic status check)
    - action: "confirm_payment"
      params:
        pre_checkout_query_id: "{pre_checkout_query_id}"
        invoice_payload: "{invoice_payload}"  # Automatic status check

# 3. Handling payment_successful (final processing)
handle_payment_successful:
  description: "Handling successful payment"
  trigger:
    - event_type: "payment_successful"
  
  step:
    # Mark invoice as paid
    - action: "mark_invoice_as_paid"
      params:
        invoice_payload: "{invoice_payload}"
        telegram_payment_charge_id: "{telegram_payment_charge_id}"
    
    # Send confirmation
    - action: "send_message"
      params:
        text: |
          ✅ Payment successfully processed!
          
          Thank you for your purchase!
    
    # Activate subscription (example)
    - action: "set_user_storage"
      params:
        key: "premium_active"
        value: true
```

**What happens in this flow:**

1. **User sends `/buy`** → `create_payment` launches
2. **Invoice created** → sent to user in chat
3. **User clicks "Pay"** → Telegram sends `pre_checkout_query`
4. **Bot confirms payment** → `handle_pre_checkout` responds via `confirm_payment` (within 10 seconds)
5. **Telegram processes payment** → sends `payment_successful`
6. **Bot processes successful payment** → `handle_payment_successful` marks invoice as paid and executes business logic

#### Recommendations and Best Practices

**1. Always handle both events:**
- `pre_checkout_query` — for payment confirmation/rejection
- `payment_successful` — for final processing and business logic

**2. Use `invoice_payload` in `confirm_payment`:**
- If pass `invoice_payload` to `confirm_payment`, system automatically checks invoice status
- If invoice cancelled or already paid, payment will be automatically rejected

**3. 10 second timeout for `pre_checkout_query`:**
- Processing must be fast
- If need long check (e.g., external API request), use async actions, but respond quickly
- Can confirm payment immediately and do check in `payment_successful`

**4. Error handling:**
- Always handle `result: "failed"` in `confirm_payment` (invoice cancelled/already paid)
- Use error codes to distinguish situations:
  - `INVOICE_CANCELLED` — invoice cancelled
  - `INVOICE_ALREADY_PAID` — invoice already paid
- Handle `result: "error"` in `mark_invoice_as_paid` (technical errors)
- Handling example via `validate` and `transitions`:
```yaml
- action: "confirm_payment"
  params:
    pre_checkout_query_id: "{pre_checkout_query_id}"
    invoice_payload: "{invoice_payload}"
  transition:
    - action_result: "failed"
      transition_action: "jump_to_step"
      transition_value: 2  # Jump to error handling

- action: "validate"
  params:
    condition: "{last_error.code} == 'INVOICE_CANCELLED'"
  transition:
    - action_result: "success"
      transition_action: "jump_to_scenario"
      transition_value: "handle_cancelled_invoice"
```

**5. Using `as_link=true`:**
- If need to create invoice link instead of sending to chat, use `as_link: true`
- Link will be saved to `_cache.invoice_link` and can send it to user manually

**6. Invoice cancellation:**
- Use `cancel_invoice` to cancel unpaid invoices
- **Important:** Invoice cancellation works only at platform level — Telegram continues storing invoice and may send confirmation request for cancelled invoice
- If `invoice_payload` passed to `confirm_payment`, system automatically checks invoice status and rejects payment if invoice cancelled (returns `result: "failed"`)

**7. Getting invoice information:**
- Use `get_invoice` to check invoice status
- Use `get_user_invoices` to get all user invoices

---

### Working with RAG Storage

RAG (Retrieval-Augmented Generation) — system for storing and searching text data using vector embeddings. Allows finding relevant text fragments by meaning and using them as context for AI.

#### RAG System Overview

**How RAG works:**

1. **Saving** — text split into chunks, for each generates vector representation (embedding) and saves to DB
2. **Search** — by query finds similar text via vector search (cosine similarity)
3. **Usage** — found chunks passed to AI completion as context for more accurate answers

**Document types:**
- `knowledge` — knowledge base (documentation, reference information)
- `chat_history` — dialogue history (user and bot messages)
- `other` — other (added to ADDITIONAL CONTEXT block along with custom context)

**Roles for OpenAI messages:**
- `system` — system instructions
- `user` — user messages
- `assistant` — assistant responses

**Metadata (chunk_metadata)** — JSON object for filtering (e.g., `chat_id`, `username`). Used for filtering in search and deletion. Can be used in `chunk_format` for display in AI context.

#### Saving Data to Vector Storage

**Action:** `save_embedding`

**What it does:**
- Cleans text from HTML, markdown and extra characters
- Splits into chunks with overlap for context preservation
- Generates embeddings for each chunk
- Saves to `vector_storage` table

**Example: Saving knowledge base**

```yaml
save_knowledge:
  description: "Saving documentation to knowledge base"
  trigger:
    - event_type: "message"
      event_text: "/save_knowledge"
  
  step:
    - action: "save_embedding"
      params:
        text: |
          Coreness — platform for creating Telegram bots.
          
          Main features:
          - YAML scenarios
          - Data storage
          - Payment processing
          - RAG for contextual answers
        document_type: "knowledge"
        role: "user"
        # Optional: metadata for filtering
        metadata:
          category: "documentation"
          version: "0.21.0"
```

**Example: Saving dialogue history**

```yaml
save_user_message:
  description: "Saving user message to history"
  trigger:
    - event_type: "message"
  
  step:
    # Save user message
    - action: "save_embedding"
      params:
        text: "{event_text}"
        document_type: "chat_history"
        role: "user"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"
          message_id: "{message_id}"
```

**Example: Saving history with AI response**

```yaml
ai_chat_with_history:
  description: "AI chat with history saving"
  trigger:
    - event_type: "message"
  
  step:
    # Step 1: Save user message
    - action: "save_embedding"
      params:
        text: "{event_text}"
        document_type: "chat_history"
        role: "user"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"
    
    # Step 2: Get history for context
    - action: "get_recent_chunks"
      params:
        limit_chunks: 10
        document_type: "chat_history"
        metadata_filter:
          chat_id: "{chat_id}"
    
    # Step 3: AI request with history
    - action: "completion"
      params:
        prompt: "{event_text}"
        rag_chunks: "{_cache.chunks}"
    
    # Step 4: Save AI model response
    - action: "save_embedding"
      params:
        text: "{_cache.response}"
        document_type: "chat_history"
        role: "assistant"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"
    
    # Step 5: Send response to user
    - action: "send_message"
      params:
        text: "{_cache.response}"
```

**Parameters:**
- `text` — text to save (required)
- `document_type` — document type: `knowledge`, `chat_history`, `other` (required)
- `role` — role for OpenAI: `system`, `user`, `assistant` (default `user`)
- `metadata` — metadata for filtering (JSON object, optional)
- `document_id` — document ID (optional, generated automatically)
- `chunk_size` — chunk size in characters (default 1000)
- `chunk_overlap` — overlap between chunks (default 200)

#### Semantic Search

**Action:** `search_embedding`

**What it does:**
- Converts query to vector (if `query_text` passed)
- Finds similar chunks by cosine similarity
- Returns sorted results with similarity score

**Example: Text search**

```yaml
search_knowledge:
  description: "Search in knowledge base"
  trigger:
    - event_type: "message"
      event_text: "/search"
  
  step:
    # Step 1: Search relevant chunks
    - action: "search_embedding"
      params:
        query_text: "{event_text}"
        document_type: "knowledge"
        limit_chunks: 5
        min_similarity: 0.7
        limit_chars: 2000  # Character limit on top of limit_chunks
    
    # Step 2: Send results to user
    - action: "send_message"
      params:
        text: |
          Found {_cache.chunks_count} relevant fragments:
          
          [1] (similarity: {_cache.chunks[0].similarity})
          {_cache.chunks[0].content}
          
          [2] (similarity: {_cache.chunks[1].similarity})
          {_cache.chunks[1].content}
          
          [3] (similarity: {_cache.chunks[2].similarity})
          {_cache.chunks[2].content}
```

**Example: Search with metadata filtering**

```yaml
search_user_history:
  description: "Search in specific user history"
  trigger:
    - event_type: "message"
      event_text: "/my_history"
  
  step:
    - action: "search_embedding"
      params:
        query_text: "{event_text}"
        document_type: "chat_history"
        metadata_filter:
          chat_id: "{chat_id}"
          username: "{username}"
        limit_chunks: 10
```

**Parameters:**
- `query_text` or `query_vector` — search query (required one of them)
- `document_type` — filter by document type (string or array)
- `document_id` — filter by document ID (string or array)
- `limit_chunks` — number of results (default 10)
- `limit_chars` — character limit on top of limit_chunks (optional)
- `min_similarity` — minimum similarity threshold (default 0.7)
- `until_date` / `since_date` — filter by date (format: `YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`)
- `metadata_filter` — filter by metadata (JSON object)

**Result:**
- `chunks` — array of found chunks with fields: `content`, `document_id`, `chunk_index`, `document_type`, `role`, `similarity`, `created_at`, `chunk_metadata`
- `chunks_count` — number of found chunks

#### Getting Recent Chunks

**Action:** `get_recent_chunks`

**What it does:**
- Gets last N chunks by `created_at` date (not vector search)
- Useful for getting dialogue history or recent messages

**Example: Getting recent messages from chat**

```yaml
get_recent_messages:
  description: "Getting recent messages from chat"
  trigger:
    - event_type: "message"
      event_text: "/recent"
  
  step:
    - action: "get_recent_chunks"
      params:
        limit_chunks: 20
        limit_chars: 3000  # Character limit on top of limit_chunks
        document_type: "chat_history"
        metadata_filter:
          chat_id: "{chat_id}"
    
    - action: "send_message"
      params:
        text: |
          Last {_cache.chunks_count} messages:
          
          [{_cache.chunks[0].created_at}] {_cache.chunks[0].role}: {_cache.chunks[0].content}
          
          [{_cache.chunks[1].created_at}] {_cache.chunks[1].role}: {_cache.chunks[1].content}
          
          [{_cache.chunks[2].created_at}] {_cache.chunks[2].role}: {_cache.chunks[2].content}
```

**Parameters:**
- `limit_chunks` — number of chunks (default 10). Works with limit_chars - first selects limit_chunks chunks, then filters by limit_chars
- `limit_chars` — character limit on top of limit_chunks (optional). After getting limit_chunks chunks they are selected in order (from new to old) until character sum exceeds limit_chars
- `document_type` — filter by document type
- `document_id` — filter by document ID
- `until_date` / `since_date` — filter by date
- `metadata_filter` — filter by metadata

#### Using RAG in AI Completion

**Parameter:** `rag_chunks` in `completion` action

**What it does:**
- Automatically forms correct messages structure for AI
- Groups chunks by types: `chat_history` → dialogue, `knowledge` → context, `other` → additional context
- Adds average similarity for context quality assessment

**Example: AI response with context from knowledge base**

```yaml
ai_answer_with_context:
  description: "AI response using RAG context"
  trigger:
    - event_type: "message"
  
  step:
    # Step 1: Search relevant context
    - action: "search_embedding"
      params:
        query_text: "{event_text}"
        document_type: "knowledge"
        limit_chunks: 5
        limit_chars: 2000
    
    # Step 2: Get recent messages for dialogue context
    - action: "get_recent_chunks"
      params:
        limit_chunks: 10
        document_type: "chat_history"
        metadata_filter:
          chat_id: "{chat_id}"
    
    # Step 3: Combine results and AI request
    - action: "completion"
      params:
        prompt: "{event_text}"
        system_prompt: |
          You are an assistant who answers user questions.
          Use provided context for accurate answers.
        rag_chunks: "{_cache.chunks}"  # Chunks from search_embedding and get_recent_chunks
        model: "gpt-4o-mini"
    
    # Step 4: Send response
    - action: "send_message"
      params:
        text: "{_cache.response}"
    
    # Step 5: Save dialogue to history
    - action: "save_embedding"
      params:
        text: "{event_text}"
        document_type: "chat_history"
        role: "user"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"
    
    - action: "save_embedding"
      params:
        text: "{_cache.response}"
        document_type: "chat_history"
        role: "assistant"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"
```

**Messages format formed automatically:**

```
1. System message (from system_prompt)
2. Dialogue from chat_history (sorted by created_at)
3. Final user with:
   - KNOWLEDGE (3, avg: 0.85):
     [1] 0.90 ...
     [2] 0.82 ...
   - ADDITIONAL CONTEXT:
     [1] [other chunks from rag_chunks]
     [custom context]
   - QUESTION: [prompt]
```

#### Complete Example: RAG Flow

**Complete flow from saving to using RAG:**

```yaml
# 1. Save knowledge base (once)
save_documentation:
  description: "Saving documentation to knowledge base"
  trigger:
    - event_type: "message"
      event_text: "/admin_save_docs"
  
  step:
    - action: "save_embedding"
      params:
        text: |
          [Your documentation here]
        document_type: "knowledge"
        metadata:
          category: "docs"
          updated_at: "{event_date}"

# 2. Handle user question with RAG
handle_question:
  description: "Answer question using RAG"
  trigger:
    - event_type: "message"
  
  step:
    # Search relevant context
    - action: "search_embedding"
      params:
        query_text: "{event_text}"
        document_type: "knowledge"
        limit_chunks: 5
        limit_chars: 2000
    
    # Get dialogue history
    - action: "get_recent_chunks"
      params:
        limit_chunks: 10
        document_type: "chat_history"
        metadata_filter:
          chat_id: "{chat_id}"
    
    # AI response with context
    - action: "completion"
      params:
        prompt: "{event_text}"
        system_prompt: "You are an assistant. Use context for accurate answers."
        rag_chunks: "{_cache.chunks}"
    
    # Send response
    - action: "send_message"
      params:
        text: "{_cache.response}"
    
    # Save to history
    - action: "save_embedding"
      params:
        text: "{event_text}"
        document_type: "chat_history"
        role: "user"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"
    
    - action: "save_embedding"
      params:
        text: "{_cache.response}"
        document_type: "chat_history"
        role: "assistant"
        chunk_metadata:
          chat_id: "{chat_id}"
          username: "{username}"

# 3. Delete old data (optional)
cleanup_old_data:
  description: "Delete old data from history"
  trigger:
    - event_type: "scheduled"
      schedule: "0 0 * * *"  # Every day at midnight
  
  step:
    - action: "delete_embedding"
      params:
        document_type: "chat_history"
        until_date: "{date_sub_days(event_date, 30)}"  # Older than 30 days
        metadata_filter:
          chat_id: "{chat_id}"
```

#### Recommendations and Best Practices

**1. Document types:**
- Use `knowledge` for static information (documentation, references)
- Use `chat_history` for dialogues (user and bot messages)
- Use `other` for miscellaneous (added to ADDITIONAL CONTEXT block along with custom context)

**2. Metadata for filtering:**
- Always save `chat_id` and `username` in metadata for dialogue history
- Use metadata for filtering by chats, users, categories
- Metadata not passed to AI context, used only for search

**3. Chunk size:**
- Optimal size: 500-1500 characters
- Overlap: 10-20% of chunk size
- Too small chunks lose context, too large — search accuracy

**4. Search and limits:**
- Use `limit_chunks` to limit number of results
- Use `limit_chars` for more flexible context size control
- Recommended `min_similarity`: 0.7-0.8 (depends on embeddings quality)

**5. Using in AI completion:**
- Always pass `rag_chunks` to `completion` for automatic messages formation
- System automatically groups chunks by types and roles
- `chat_history` sorted by `created_at` to preserve dialogue order
- Chunks of type `other` combined with custom `context` in ADDITIONAL CONTEXT block

**6. Chunk format (chunk_format):**
- `chunk_format` parameter allows customizing chunk display in AI context
- Templates use `$` markers for value substitution: `$content` (required) + any fields from `chunk_metadata`
- Supports fallback: `$field|fallback:value`
- Example for group chat: `chunk_format: {chat_history: "[$username|fallback:User]: $content"}`
- Example for knowledge base: `chunk_format: {knowledge: "[$category|fallback:Knowledge base] $content"}`

**7. Performance:**
- Save data asynchronously (don't block user response)
- Use metadata filters to speed up search
- Clean old data periodically via `delete_embedding`

**8. Error handling:**
- Always check `result: "success"` before using results
- Handle cases when search found no results (`chunks_count: 0`)
- Use fallback logic if context not found
