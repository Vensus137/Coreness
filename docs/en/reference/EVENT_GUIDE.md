---
title: System Events Guide
description: Reference of all fields available in Coreness events. Message fields, callbacks, attachments and other data for use in placeholders.
keywords: coreness events, placeholders, event fields, telegram events, user_id, chat_id
---

# 📡 System Events Guide

Complete description of all fields available in events after parsing through EventParser.

## Event Types

System supports following event types:

| Event Type | Description | When Occurs |
|------------|-------------|-------------|
| `message` | Regular message from user | User sends text message or media |
| `callback` | Inline button click | User clicks button in message |
| `member_joined` | Member joined group | User joins group or supergroup |
| `member_left` | Member left group | User leaves group or supergroup |
| `pre_checkout_query` | Payment confirmation request | User clicks "Pay" in invoice, but before payment processing |
| `payment_successful` | Successful payment | Payment via invoice successfully processed |

## Common Fields

These fields available in all event types. **All these fields come initially when receiving event** and contain original data that formed the event.

**ℹ️ Important:** These attributes — original event information passed from source (e.g., Telegram). They used by system as default values for actions (e.g., `chat_id` and `message_id` taken from event if not specified explicitly in action parameters).

**⚠️ Limitation for scheduled scenarios:** In scenarios launched on schedule (with `schedule` field), most common fields unavailable, as event not associated with user or chat. Only system fields available (`bot_id`, `tenant_id`) and special scheduled scenario fields (see [Scheduled Scenario Fields](#scheduled-scenario-fields) section).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `event_source` | string | Event source | `"telegram"` |
| `event_type` | string | Event type | `"message"`, `"callback"`, `"member_joined"`, `"member_left"`, `"pre_checkout_query"`, `"payment_successful"` |
| `user_id` | integer | User ID who initiated event | `123456789` |
| `chat_id` | integer | Chat ID from which event came | `-1001234567890` |
| `chat_type` | string | Chat type | `"private"`, `"group"`, `"supergroup"`, `"channel"` |
| `is_group` | boolean | Whether chat is group or supergroup | `true` for `group` and `supergroup`, `false` for `private` and `channel` |
| `message_id` | integer | ID of original message that led to event. For `message` type events — text message ID, for `callback` — message ID with button that triggered callback | `1234` |
| `event_date` | string | Event date (ISO) | `"2024-01-15T10:30:45+03:00"` |
| `username` | string | User username | `"john_doe"` (can be null) |
| `first_name` | string | User first name | `"John"` |
| `last_name` | string | User last name | `"Doe"` (can be null) |
| `language_code` | string | User language code | `"ru"`, `"en"` (can be null) |
| `is_bot` | boolean | Whether user is bot | `false` |
| `is_premium` | boolean | Premium user | `true` |
| `chat_title` | string | Chat title | `"My Group"` (can be null) |
| `chat_username` | string | Chat username | `"my_group"` (can be null) |
| `user_state` | string | User state | `"feedback"`, `"onboarding"` (can be null) |
| `user_state_expired_at` | string | State expiration time (ISO) | `"3000-01-01T00:00:00+00:00"` (can be null) |

### 🔧 Service Fields

System automatically adds following service fields for correct action operation:

| Field | Type | Description | Purpose |
|-------|------|-------------|---------|
| `bot_id` | integer | Bot ID | **Required** for sending messages and executing actions |
| `tenant_id` | integer | Tenant ID | **Required** for loading scenarios and determining context |
| `polling_start_time` | string | Bot polling start time (ISO) | **Service** for filtering events by time |
| `last_error` | string | Last action error text | **Service** for passing errors between scenario steps |
| `last_result` | string | Last executed action result | **Service** for debugging and result checking between scenario steps |
| `scenario_chain` | array | Scenario chain in execution order | **Service** for debugging and logging, contains array of scenario names in execution order |

**⚠️ Important:** Following fields added automatically:

- **Required fields** (`bot_id`, `tenant_id`) — required for executing actions (sending messages, working with DB, managing states)
  - **ℹ️ In scheduled scenarios:** Fields `bot_id` and `tenant_id` available automatically and don't require explicit specification in action parameters. They automatically substituted from synthetic event context
- **Service fields** (`polling_start_time`, `last_error`, `last_result`, `scenario_chain`) — used by system for internal logic:
  - `polling_start_time` — filtering events by time
  - `last_error` — saving action error text for subsequent scenario steps
  - `last_result` — saving action execution result (e.g., `success`, `error`, `timeout`, `not_found`) for debugging and checking in subsequent scenario steps
  - `scenario_chain` — array of scenario names in call order, automatically updated when launching each scenario and on transitions (`jump_to_scenario`, `execute_scenario`). Current scenario available as `scenario_chain[-1]`, previous — as `scenario_chain[-2]` (if exists). Used for debugging and logging execution flow
- **State fields** (`user_state`, `user_state_expired_at`) — can be `null` if state not set or expired

## Scheduled Scenario Fields

Additional fields for scenarios launched on schedule:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `scheduled_at` | string | Scheduled scenario launch time (ISO) | `"2024-01-15T10:30:00+03:00"` |
| `scheduled_scenario_id` | integer | Scheduled scenario ID in database | `123` |
| `scheduled_scenario_name` | string | Scheduled scenario name | `"daily_report"` |

**ℹ️ Important:** These fields available only in scheduled scenarios (with `schedule` field in configuration). In regular event-triggered scenarios, these fields absent.

**⚠️ Limitation:** In scheduled scenarios most common fields (e.g., `user_id`, `chat_id`, `event_text`, `message_id`, etc.) unavailable, as event not associated with user or chat. For sending messages use `target_chat_id` parameter in actions.

## Message Fields

Additional fields for `message` type events:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `event_text` | string | Message text | `"Hello! How are you?"` |
| `media_group_id` | string | Media group ID | `"1234567890123456789"` (can be null) |
| `event_attachment` | array | Attachments | `[{"type": "photo", "file_id": "AgACAgIAAxkBAAIB..."}]` |
| `inline_keyboard` | array | Message inline keyboard | `[[{"Button 1": "action_1"}]]` (can be null) |
| `is_reply` | boolean | Reply to message | `true` |
| `is_forward` | boolean | Forwarded message | `false` |

### Reply Message Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `reply_message_id` | integer | Reply message ID | `1233` |
| `reply_message_text` | string | Reply message text | `"How are you?"` |
| `reply_user_id` | integer | Reply message author ID | `123456789` |
| `reply_username` | string | Reply message author username | `"jane_doe"` |
| `reply_first_name` | string | Reply message author first name | `"Jane"` |
| `reply_last_name` | string | Reply message author last name | `"Smith"` |
| `reply_date` | string | Reply message date (ISO) | `"2024-01-15T10:25:30+03:00"` |
| `reply_attachment` | array | Reply message attachments | `[{"type": "document", "file_id": "BQACAgIAAxkBAAIB..."}]` |

### Forwarded Message Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `forward_message_id` | integer | Forwarded message ID | `5678` |
| `forward_from_user_id` | integer | Forwarded message author ID | `987654321` |
| `forward_from_user_username` | string | Forwarded message author username | `"original_author"` |
| `forward_from_user_first_name` | string | Forwarded message author first name | `"Original"` |
| `forward_from_user_last_name` | string | Forwarded message author last name | `"Author"` |
| `forward_from_chat_id` | integer | Forwarded message chat ID | `-1009876543210` |
| `forward_from_chat_title` | string | Forwarded message chat title | `"Original Group"` |
| `forward_from_chat_type` | string | Forwarded message chat type | `"supergroup"` |
| `forward_date` | string | Forwarded message date (ISO) | `"2024-01-15T09:15:20+03:00"` |

## Callback Fields

Additional fields for `callback` type events:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `callback_id` | string | Callback ID | `"1234567890123456789"` |
| `callback_data` | string | Callback data | `"menu_main"` |
| `callback_message_text` | string | Original message text callback attached to (text or caption) | `"Choose action:"` (can be null) |
| `inline_keyboard` | array | Inline keyboard of message callback attached to | `[[{"Button 1": "action_1"}]]` (can be null) |

## Payment Events

Events related to payment via Telegram invoices.

### pre_checkout_query Fields

Event `pre_checkout_query` occurs when user clicks "Pay" button in invoice, but before payment processing. This is payment confirmation request from Telegram to bot.

**ℹ️ Important:** Must respond to this event via `answer_pre_checkout_query` action to confirm or reject payment. If don't respond within 10 seconds, payment will be automatically rejected.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `pre_checkout_query_id` | string | Payment confirmation request ID | `"1234567890123456789"` |
| `invoice_payload` | string | Invoice ID (payload passed during creation) | `"123"` |
| `currency` | string | Payment currency | `"XTR"` (Telegram Stars) |
| `total_amount` | integer | Total payment amount in minimal currency units | `100` (100 stars) |

**Additionally:** Event contains common fields (see [Common Fields](#common-fields) section).

### payment_successful Fields

Event `payment_successful` occurs after successful payment processing via invoice.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `invoice_payload` | string | Invoice ID (payload passed during creation) | `"123"` |
| `currency` | string | Payment currency | `"XTR"` (Telegram Stars) |
| `total_amount` | integer | Total payment amount in minimal currency units | `100` (100 stars) |
| `telegram_payment_charge_id` | string | Payment ID in Telegram | `"1234567890"` |

**Additionally:** Event contains common fields (see [Common Fields](#common-fields) section).

## Member Events

Events of type `member_joined` and `member_left` use standard common fields (see [Common Fields](#common-fields) section).

**ℹ️ Important:** 
- Event `member_joined` occurs when user joins group (transition from status `left`, `kicked` or first join)
- Event `member_left` occurs when user leaves group (transition to status `left` or `kicked`)
- These events available only for groups and supergroups

## Attachment Fields

Structure of objects in `event_attachment` and `reply_attachment` arrays:

### Attachment Types

| Type | Description | Note |
|------|-------------|------|
| `photo` | Photo | Largest available resolution |
| `document` | Document | Any file (PDF, DOC, ZIP, etc.) |
| `video` | Video | Video file |
| `audio` | Audio | Audio file |
| `voice` | Voice message | Voice message |
| `sticker` | Sticker | Telegram sticker |
| `animation` | Animation | GIF animation |
| `video_note` | Video note | Round video message |

### Attachment Object Structure

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `type` | string | Attachment type | `"photo"` |
| `file_id` | string | File ID | `"AgACAgIAAxkBAAIB..."` |

### Attachment Structure Example

```json
{
  "type": "photo",
  "file_id": "AgACAgIAAxkBAAIB..."
}
```

## Usage Examples

How to use event fields in scenarios:

### Simple Conditions

```yaml
# Check event type
trigger:
  - event_type: "message"

# Check message text
trigger:
  - event_type: "message"
    event_text: "/start"

# Check callback data
trigger:
  - event_type: "callback"
    callback_data: "menu_main"

# Check user state
trigger:
  - event_type: "message"
    user_state: "feedback"
```

### Complex Conditions

```yaml
# Check user and chat
trigger:
  - event_type: "message"
    condition: |
      $user_id == 123456789 and
      $chat_type == "private" and
      $event_text ~ "hello"

# Check attachments
trigger:
  - event_type: "message"
    condition: |
      $event_attachment[0].type == "photo"

# Check reply message
trigger:
  - event_type: "message"
    condition: |
      $is_reply == true and
      $reply_user_id == 987654321
```

### Usage in Action Parameters

```yaml
# Send message to same chat
- action: "send_message"
  params:
    bot_id: "{bot_id}"
    chat_id: "{chat_id}"
    text: "Hello, {first_name}!"

# Reply to message
- action: "send_message"
  params:
    bot_id: "{bot_id}"
    chat_id: "{chat_id}"
    text: "Received your message!"
    message_reply: "{message_id}"

# Manage user state
- action: "set_user_state"
  params:
    state: "feedback"
    expires_in_seconds: 3600
```
