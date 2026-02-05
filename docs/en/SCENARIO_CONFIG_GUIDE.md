---
title: Scenario Creation Guide
description: Complete guide to creating scenarios for Telegram bots. Triggers, actions, transitions, placeholders and async operations.
keywords: telegram bot scenarios, YAML configuration, triggers, placeholders, scenario transitions
---

# Scenario Creation Guide

> **📖 Complete guide** to creating and configuring scenarios for Telegram bots with support for placeholders, transitions, and dynamic logic.

## 📑 Table of Contents

- [Scenario Structure](#-scenario-structure)
- [Triggers (trigger)](#-triggers-trigger)
- [Scheduled Scenarios (Cron Execution)](#-scheduled-scenarios-cron-execution)
- [Actions (step)](#-actions-step)
  - [Data Caching in Scenarios](#data-caching-in-scenarios)
  - [Saving Context Between Scenarios](#saving-context-between-scenarios)
- [Transitions (transition)](#-transitions-transition)
- [Placeholders](#-placeholders)
  - [Placeholder Syntax](#placeholder-syntax)
  - [Available Data](#available-data)
  - [Accessing Nested Elements](#accessing-nested-elements)
  - [Getting File Information](#getting-file-information)
  - [Modifiers](#modifiers)
  - [Usage Examples](#usage-examples)
  - [Practical Examples](#practical-examples)
- [Async Actions](#-async-actions-async-actions)

---

## 📋 Scenario Structure

### Scenario Organization

**File Organization** — scenarios can be organized in folders and subfolders for convenience. All YAML files from `scenarios/` folder (including subfolders) are automatically loaded.

**Important Principles:**
- **Name Uniqueness:** Scenario name must be unique within the tenant
- **Flexible File Structure:** Can create files with any names and organize them in subfolders — all files will be loaded
- **Recursive Loading:** All YAML files from `scenarios/` and all subfolders are automatically parsed
- **Global Transitions:** Scenarios can transition to any other tenant scenarios through `jump_to_scenario`

**Example Structure:**
```
tenant_101/
  scenarios/
    commands.yaml           # Scenarios: start, menu, help
    settings.yaml           # Scenarios: settings, profile
    admin/                  # Subfolder for organization
      panel.yaml            # Scenarios: admin_panel, logs
      moderation.yaml       # Scenarios: ban, kick
    users/                  # Another subfolder
      profile.yaml          # Scenarios: user_profile, edit_profile
```

In this example:
- All files from `scenarios/` and subfolders are loaded automatically
- Scenarios can transition to each other regardless of folder location
- Subfolders are used only for logical file organization

**YAML File Structure:**
```yaml
# Scenario name
scenario_name:
  description: "Scenario description (optional)"

  # Scenario launch conditions (optional for scheduled scenarios)
  trigger:
    - event_type: "message"
      event_text: "/start"
    - event_type: "callback"
      callback_data: "start"

  # Launch schedule (optional, cron expression)
  schedule: "0 9 * * *"  # Every day at 9:00

  # Scenario actions
  step:
    - action: "send_message"
      params:
        text: "Hello!"
        inline:
          - [{"Button": "callback_data"}]
```

### Scenario Parameters:

- **`description`** — scenario description (optional)
- **`trigger`** — scenario launch conditions (optional for scheduled scenarios)
- **`schedule`** — cron expression for scheduled launch (optional)
- **`step`** — action sequence

### Practical Example:

```yaml
user_registration:
  description: "User registration process with validation and notifications"
  
  # TRIGGERS: Each works independently - any of them will launch scenario
  trigger:
    - event_type: "message"      # Command /register
      event_text: "/register"
    - event_type: "callback"     # Button "Start Registration"  
      callback_data: "start_registration"

  # STEPS: Executed sequentially one after another
  step:
    # Step 1: Send greeting
    - action: "send_message"
      params:
        text: |
          👋 Welcome, {username|fallback:Guest}!
          
          Let's register you in the system.
        inline:
          - [{"✅ Continue": "continue_registration"}]

    # Step 2: Check user permissions with transitions
    - action: "validate"
      params:
        condition: "$user_role == 'admin'"
      transition:
        - action_result: "success"
          transition_action: "jump_to_scenario"
          transition_value: "admin_welcome"        # Transition to admin welcome
        - action_result: "error"
          transition_action: "continue"            # Normal flow for users
    
    # Step 3: Request name
    - action: "send_message"
      params:
        text: |
          📝 Step 2 of 3
          
          Please enter your name:
        inline:
          - [{"❌ Cancel": "cancel_registration"}]
    
    # Step 4: Send confirmation with attachments
    - action: "send_message"
      params:
        text: |
          ✅ Registration started!
          
          We sent you instructions via email.
          📎 Also attaching useful materials:
        attachment:
          - file_id: "AgACAgIAAxkBAAIUJWjyLorr_d8Jwof3V_gVjVNdGHyXAAJ--zEb4vGQS-a9UiGzpkTNAQADAgADeQADNgW"
            type: "photo"
          - file_id: "AgACAgIAAxkBAAIUQWjyOH65wQYR4onkrrqM4J65yUD7AAM8-zEb4vGQS1mwvckFcZHlAQADAgADdwADNgQ"
            type: "photo"
        inline:
          - [{"🏠 Main Menu": "main_menu"}]
    
    # Step 5: Delete previous message
    - action: "delete_message"
      params:
        delete_message_id: "{last_message_id}"  # Use previous message ID

admin_welcome:
  description: "Admin welcome (transition scenario)"
  # NO TRIGGERS - called only programmatically
  
  step:
    - action: "send_message"
      params:
        text: |
          🔧 Welcome, administrator!
          
          You have additional permissions.
        inline:
          - [{"⚙️ Control Panel": "admin_panel"}]
```

**Key Points:**
- **Triggers** — OR logic: if at least one triggers, scenario launches
- **Steps** — executed strictly in order of appearance
- **Transitions** — control execution flow through `transition`:
  - `continue` — continue executing next actions
  - `break` — interrupt only current scenario execution
  - `abort` — interrupt entire current scenario chain (including nested)
  - `stop` — interrupt all event processing (all scenarios)
  - `move_steps` — move specified number of steps (positive = forward, negative = backward)
  - `jump_to_step` — jump to specific step by index (steps numbered from 0)
  - `jump_to_scenario` — transition to another scenario (to any tenant scenario)
- **Transition scenarios** — scenarios without triggers, called programmatically from other scenarios
- **Scheduled scenarios** — scenarios with `schedule` field (cron expression), launched automatically on schedule
- **Hybrid scenarios** — can have both `trigger` and `schedule` simultaneously (work on events AND on schedule)
- **Event data** — available in action parameters (user_id, chat_id, timestamp, etc.)
- **Attachments** — can forward files through `attachment[0].file_id` and `attachment[0].type`

---

## 🎯 Triggers (trigger)

**Purpose:** Conditions under which scenario is launched.

### Trigger Mechanics:

**Simple form** (attributes):
```yaml
trigger:
  - event_type: "message"
    event_text: "/start"
```

**Converts to condition:**
```python
$event_type == "message" and $event_text == "/start"
```

**Complex form** (with `condition`):
```yaml
trigger:
  - event_type: "message"
    condition: |
      $event_text == "test"
      and $user_id > 100
      or $username in ('@admin', '@moderator')
```

**Converts to condition:**
```python
$event_type == "message" and ($event_text == "test" and $user_id > 100 or $username in ('@admin', '@moderator'))
```

### Trigger Logic:

- **Between triggers** — **OR** logic: if at least one triggers, scenario launches
- **Within trigger** — **AND** logic: all conditions must be met
- **In condition** — full freedom: `and`, `or`, `not`, parentheses, operators

### ⚠️ Important: Placeholders in condition

**Problem:** When using placeholders in trigger `condition` for string comparison, you need to wrap placeholder in quotes. Otherwise placeholder will "expand" as attribute to search for data in `condition_parser`, not as string value.

**Solution:** Always wrap placeholders in quotes when comparing strings in conditions.

**Examples:**

```yaml
# ❌ ERROR - placeholder expands to random_user without quotes
# condition_parser tries to find variable random_user in data
trigger:
  - event_type: "message"
    condition: "{_cache.detected_intent} == 'random_user'"
    # After placeholder processing: random_user == 'random_user'
    # condition_parser looks for variable random_user in data, not comparing strings!

# ✅ CORRECT - placeholder wrapped in quotes
trigger:
  - event_type: "message"
    condition: "'{_cache.detected_intent}' == 'random_user'"
    # After placeholder processing: 'random_user' == 'random_user'
    # condition_parser correctly compares strings

# ✅ CORRECT - number comparison (quotes not needed)
trigger:
  - event_type: "message"
    condition: "{user_id} > 100"
    # After placeholder processing: 12345 > 100
    # Numeric comparison works correctly

# ✅ CORRECT - comparison with modifiers (quotes not needed for boolean)
trigger:
  - event_type: "message"
    condition: "{response_value.feedback|exists} == True"
    # exists modifier returns boolean, comparison works correctly
```

**Rule:** 
- **For string comparison** — always wrap placeholder in quotes: `'{_cache.field}' == 'value'`
- **For number comparison** — quotes not needed: `{user_id} > 100`
- **For boolean values** — quotes not needed: `{field|exists} == True`

### Available Fields for Conditions:

**⚠️ Important:** All fields in conditions must have `$name` marker (e.g., `$event_type`, `$user_id`, `$event_text`).

**Event data:**
- **`$event_text`** — message text
- **`$event_type`** — event type (message, callback)
- **`$user_id`** — user ID
- **`$username`** — username
- **`$chat_id`** — chat ID
- **`$callback_data`** — callback button data
- **`$event_date`** — event time
- **`$tenant_id`** — tenant ID
- **`$message_id`** — message ID
- **`$chat_type`** — chat type
- **`$is_group`** — whether chat is group
- And other event fields (see [EVENT_GUIDE.md](EVENT_GUIDE.md))

**Previous action data:**
- **`$last_message_id`** — last sent message ID
- **`$response_data`** — any data returned by previous actions
- **Other fields** — depending on actions in scenario

**Nested fields:**
- **`$message.text`** — access nested fields via dot
- **`$user.profile.name`** — multi-level nesting

### Operators in Conditions:

- **`==`** — equals
- **`!=`** — not equals
- **`>`**, **`<`**, **`>=`**, **`<=`** — number comparison
- **`in`**, **`not in`** — inclusion in list
- **`~`** — contains substring
- **`!~`** — doesn't contain substring
- **`regex`** — regular expression
- **`is_null`** — field is empty (None or empty string)
- **`not is_null`** — field is not empty (exists and has value)

---

## ⏰ Scheduled Scenarios (Cron Execution)

**Purpose:** Automatic scenario launch on schedule through cron expressions.

### Scheduled Scenario Structure:

```yaml
daily_report:
  description: "Daily report at 9:00"
  
  # Cron expression for launch every day at 9:00
  schedule: "0 9 * * *"
  
  # Triggers optional - scenario will work on schedule
  # Can add triggers for hybrid mode (on events AND on schedule)
  
  step:
    - action: "send_message"
      params:
        target_chat_id: 123456789
        text: |
          📊 Daily Report
          
          Launch time: {scheduled_at|format:datetime}
          Scenario: {scheduled_scenario_name}
```

### Cron Expressions:

**Format:** `minute hour day month day_of_week`

| Example | Description |
|---------|-------------|
| `* * * * *` | Every minute |
| `*/5 * * * *` | Every 5 minutes |
| `0 * * * *` | Every hour at start |
| `0 9 * * *` | Every day at 9:00 |
| `0 9 * * 1-5` | Every weekday at 9:00 |
| `0 0 1 * *` | First day of month at 00:00 |

**ℹ️ Important:** Cron expressions interpreted in **platform local time**.

### Available Fields in Scheduled Scenarios:

Scheduled scenarios have special event fields available. For detailed description of all fields see [Scheduled Scenario Fields](EVENT_GUIDE.md#scheduled-scenario-fields) section in EVENT_GUIDE.md.

**Usage Example:**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        ⏰ Scheduled scenario launched
        
        Time: {scheduled_at|format:datetime}
        Name: {scheduled_scenario_name}
        ID: {scheduled_scenario_id}
```

### Hybrid Mode (trigger + schedule):

Scenario can work on events and schedule simultaneously:

```yaml
hybrid_scenario:
  description: "Works on events AND on schedule"
  
  # Launch on events
  trigger:
    - event_type: "message"
      event_text: "/report"
  
  # Launch on schedule (every day at 9:00)
  schedule: "0 9 * * *"
  
  step:
    - action: "send_message"
      params:
        text: |
          📊 Report
          
          {scheduled_at|fallback:Launched manually|format:datetime}
```

### ⚠️ Important Limitations and Recommendations:

**1. Scenario Synchronization:**
- During scenario synchronization (deletion and recreation), last run information is lost (`last_scheduled_run`)
- After synchronization, scheduled scenarios recalculate next run time from current moment
- **Recommendation:** Synchronize scenarios during low scheduled task activity periods

**2. Missed Launch:**
- If synchronization happens at moment when scheduled scenario should launch, launch may be missed
- **Recommendation:** Avoid scenario synchronization few seconds before planned launch time

**3. Error Behavior:**
- Scheduled scenarios update next run time even on execution error
- This ensures predictable behavior and prevents repeated launches of problematic scenarios

**4. Execution Context:**
- Scheduled scenarios execute with system context (automatically get `bot_id`, `tenant_id`)
- **Common event fields unavailable:** Most common fields (`user_id`, `chat_id`, `event_text`, `message_id`, etc.) unavailable in scheduled scenarios, as event is not associated with user or chat
- **Passing parameters:** Must pass most parameters manually in actions or extract data from tenant or user storage (from database)
- Use `target_chat_id` in action parameters to specify concrete chat

---

## ⚡ Actions (step)

**Purpose:** Sequence of actions executed in scenario.

**Important:** 
- Step execution order determined by their position in `step` array (top to bottom). Steps executed sequentially in order specified in YAML. Step numbering starts from 0.
- **Sequential Execution:** By default scenario goes sequentially through steps regardless of action result. If step has no `transition` or no suitable transition for action result, execution automatically proceeds to next step.
- **Flow Changes:** Transitions (`transition`) allow changing execution sequence (jump to another step, scenario, interrupt execution, etc.).

### Sending Message:

**Inline buttons:**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        👋 Hello!
        
        📋 Choose action:
      inline:
        - [{"📋 Menu": "main_menu"}, {"📚 Help": "help"}]
        - [{"🌐 Website": "https://example.com"}, {"📞 Support": "tg://resolve?domain=support"}]
        - [{"🔙 Back": "start"}]
```

**Reply keyboard:**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        👋 Hello!
        
        📋 Choose action:
      reply:
        - ["📋 Menu", "📚 Help"]
        - ["🔙 Back"]
```

**Remove keyboard:**
```yaml
step:
  - action: "send_message"
    params:
      text: "Keyboard removed"
      reply: []  # Empty array removes keyboard
```

### Message Parameters:

- **`text`** — message text (supports multiline with `|`)
- **`inline`** — button array:
  - `[{"Button text": "callback_data"}]` — one button per row
  - `[{"Button 1": "data1"}, {"Button 2": "data2"}]` — multiple buttons per row
  - `[{"Link": "https://example.com"}]` — button with link
- **`reply`** — reply keyboard:
  - `[["Button 1", "Button 2"]]` — one row of buttons
  - `[["Button 1"], ["Button 2"]]` — each button in separate row
  - `[]` — remove keyboard
- **`attachment`** — attachment array (photos, documents, videos, audio):
  - `[{"file_id": "AgACAgI...", "type": "photo"}]` — forward file by file_id
  - `[{"file_id": "{event_attachment[0].file_id}", "type": "{event_attachment[0].type}"}]` — dynamic forwarding from event
  - `[{...}, {...}]` — multiple files at once

### Attaching Files:

**📎 Attaching files to messages:**

Can send photos, documents, videos, audio. Files can be taken from events or use saved file_id.

**Example: Forwarding file from event:**
```yaml
step:
  - action: "send_message"
    params:
      text: "Forwarding your file back"
      attachment:
        - file_id: "{event_attachment[0].file_id}"
          type: "{event_attachment[0].type}"
```

**Example: Sending file by known file_id:**
```yaml
step:
  - action: "send_message"
    params:
      text: "Instructions"
      attachment:
        - file_id: "AgACAgIAAxkBAAIUJWjyLorr_d8Jwof3V_gVjVNdGHyXAAJ--zEb4vGQS-a9UiGzpkTNAQADAgADeQADNgW"
          type: "photo"
```

**Example: Multiple files:**
```yaml
step:
  - action: "send_message"
    params:
      text: "Useful materials"
      attachment:
        - file_id: "{event_attachment[0].file_id}"
          type: "{event_attachment[0].type}"
        - file_id: "BQACAgIAAxkBAAI..."
          type: "document"
```

**📋 How to get file_id and type:** see [scenario example below](#getting-file-information) 👇

### Tenant Configuration in Actions:

**Purpose:** Automatic use of tenant configuration attributes in actions.

Some actions automatically use parameters from tenant configuration (`_config`). Such parameters don't need to be passed explicitly in `params` — they are automatically taken from `_config`.

**Usage Example:**

```yaml
step:
  - action: "completion"
    params:
      prompt: "Hello, how are you?"
      # ai_token automatically taken from _config.ai_token
      # No need to specify ai_token explicitly!
```

**Access through placeholders:**

Tenant configuration also directly accessible through placeholders:

```yaml
step:
  - action: "send_message"
    params:
      text: |
        Tenant configuration:
        Token: {_config.ai_token|fallback:Not set}
```

**Important:**
- `_config` available in all tenant scenarios automatically
- If attribute not set in tenant configuration, value will be `None`
- Use `fallback` in placeholders to handle missing values
- If parameter passed explicitly in `params`, explicit value has priority

📖 **More about tenant configuration:** See [config.yaml](TENANT_CONFIG_GUIDE.md#-configyaml) section in TENANT_CONFIG_GUIDE.md

### Data Caching in Scenarios:

**Purpose:** Automatic saving of action results to `_cache` for use in subsequent scenario steps.

**⚠️ Important: Cache Scope:**
- Cache `_cache` saved **only within one scenario execution chain** (one chain processing one event)
- Data available between scenarios within one execution chain (e.g., when transitioning via `jump_to_scenario` or `execute_scenario`)
- **Cache NOT saved** between different execution chains (even if triggered by one event — each scenario has its isolated cache)
- **Cache NOT saved** between different events (different messages, different callbacks)
- For long-term data storage use `set_storage` / `set_user_storage` instead of `set_cache`
- See more in [Saving Context Within Event Processing](#saving-context-within-event-processing) section

**General Mechanics:**
- Each action can return `response_data` with any fields
- Data automatically saved to `_cache` and available in subsequent actions through placeholders
- Caching system supports two system fields for data structure management:
  - **`_namespace`** — for overwrite control and organizing data into nested structures
  - **`_response_key`** — for substituting replaceable field key before saving to `_cache`
- All mechanisms work at scenario engine level and don't require service changes

#### Flat Caching (default):

By default flat caching is used — data merged directly into `_cache` without nesting. Data accessed through `{_cache.field}`:

```yaml
step:
  - action: "generate_int"
    params:
      min: 1
      max: 100
    # response_data: {"random_value": 42, "random_seed": 123}
    # Goes to: _cache.random_value = 42, _cache.random_seed = 123
  
  - action: "send_message"
    params:
      text: "Number: {_cache.random_value}"  # ✅ CORRECT
```

**Example with multiple actions:**

```yaml
step:
  - action: "generate_int"
    params:
      min: 1
      max: 100
    # _cache.random_value = 42, _cache.random_seed = 123
  
  - action: "generate_array"
    params:
      min: 1
      max: 10
      count: 5
    # _cache.random_list = [3, 7, 2, 9, 1], _cache.random_seed = 456
  
  - action: "send_message"
    params:
      text: |
        Number: {_cache.random_value}
        Array: {_cache.random_list|comma}
```

**⚠️ Flat Caching Problems:**

**1. Name conflicts between different actions:**
```yaml
step:
  - action: "get_storage_value"
    params:
      group_key: "settings"
      key: "api_key"
    # _cache.response_value = "key1"
  
  - action: "get_user_storage_value"
    params:
      key: "api_secret"
    # _cache.response_value = "secret1"  # ⚠️ Overwritten!
  
  - action: "send_message"
    params:
      text: "Key: {_cache.response_value}"  # Shows only "secret1"
```

**2. Overwrite on repeated calls of same action:**
```yaml
step:
  - action: "get_storage_value"
    params:
      group_key: "settings"
      key: "api_key"
    # _cache.response_value = "key1"
  
  - action: "get_storage_value"  # Same action!
    params:
      group_key: "settings"
      key: "api_secret"
    # _cache.response_value = "secret1"  # ⚠️ First result overwritten!
```

#### System Field `_namespace` (overwrite control):

**Purpose:** Saving data to nested structure `_cache[_namespace]` for overwrite control and avoiding name conflicts.

**Mechanics:**
- If `_namespace` specified, data saved to `_cache[_namespace]` instead of flat `_cache`
- Data access: `{_cache[_namespace].field}`
- Allows saving results of repeated calls of same action
- Allows avoiding name conflicts between different actions

**Usage Example:**

```yaml
step:
  - action: "generate_int"
    params:
      min: 1
      max: 100
      _namespace: "my_random"
    # Goes to: _cache.my_random = {random_value: 42, random_seed: 123}
  
  - action: "send_message"
    params:
      text: "Number: {_cache.my_random.random_value}"  # ✅ CORRECT
```

**Solving conflicts with `_namespace`:**

```yaml
step:
  - action: "get_storage_value"
    params:
      group_key: "settings"
      key: "api_key"
      _namespace: "first"
    # _cache.first.response_value = "key1"
  
  - action: "get_storage_value"
    params:
      group_key: "settings"
      key: "api_secret"
      _namespace: "second"
    # _cache.second.response_value = "secret1"
    # ✅ Both results saved!
  
  - action: "send_message"
    params:
      text: |
        First: {_cache.first.response_value}
        Second: {_cache.second.response_value}
```

#### System Field `_response_key` (renaming main field):

**Purpose:** Allows setting custom name for action result main field for convenient `_cache` data access.

**Mechanics:**
- Some actions return main value under specific key (e.g., `storage_values`, `user_storage_values`, `formatted_text`)
- By default data saved to `_cache` with original key from action result
- If `_response_key` specified, engine automatically renames main field before saving to `_cache`
- Works only for actions that support renaming main field

**Usage Example:**

```yaml
step:
  # Get storage value (by default will be in _cache.storage_values)
  - action: "get_storage"
    params:
      tenant_id: "{tenant_id}"
      group_key: "settings"
      key: "api_key"
      _response_key: "api_key"  # Rename storage_values to api_key
    # response_data: {"storage_values": "secret_key_123"}
    # Goes to: _cache.api_key = "secret_key_123" (instead of _cache.storage_values)
  
  # Use renamed value
  - action: "send_message"
    params:
      text: "API key: {_cache.api_key}"  # ✅ CORRECT - use custom key
```

**Example with multiple calls of same action:**

```yaml
step:
  # First call - save to api_key
  - action: "get_storage"
    params:
      tenant_id: "{tenant_id}"
      group_key: "settings"
      key: "api_key"
      _response_key: "api_key"
    # _cache.api_key = "secret_key_123"
  
  # Second call - save to api_secret
  - action: "get_storage"
    params:
      tenant_id: "{tenant_id}"
      group_key: "settings"
      key: "api_secret"
      _response_key: "api_secret"
    # _cache.api_secret = "secret_secret_456"
    # ✅ Both values saved under convenient keys!
  
  - action: "send_message"
    params:
      text: |
        API Key: {_cache.api_key}
        API Secret: {_cache.api_secret}
```

**Example with text formatting:**

```yaml
step:
  # Format data and save under custom key
  - action: "format_data_to_text"
    params:
      format_type: "list"
      title: "Available intents:"
      item_template: '- "$id" - $description'
      input_data: "{storage_values.ai_router.intents}"
      _response_key: "formatted_intents"
    # response_data: {"formatted_text": "• intent1\n• intent2"}
    # Goes to: _cache.formatted_intents = "• intent1\n• intent2"
    # (instead of _cache.format_data_to_text.formatted_text)
  
  - action: "send_message"
    params:
      text: "{_cache.formatted_intents}"  # ✅ Use convenient key
```

#### Combining `_namespace` and `_response_key`:

```yaml
step:
  # Use both _namespace and _response_key simultaneously
  - action: "get_storage"
    params:
      tenant_id: "{tenant_id}"
      group_key: "settings"
      key: "api_key"
      _namespace: "first"
      _response_key: "api_key"
    # _cache.first.api_key = "secret_key_123"
    # (instead of _cache.first.storage_values)
  
  - action: "get_storage"
    params:
      tenant_id: "{tenant_id}"
      group_key: "settings"
      key: "api_secret"
      _namespace: "second"
      _response_key: "api_secret"
    # _cache.second.api_secret = "secret_secret_456"
  
  - action: "send_message"
    params:
      text: |
        First: {_cache.first.api_key}
        Second: {_cache.second.api_secret}
```

#### Usage Recommendations:

**General Recommendations:**
- ✅ Flat caching by default — less nesting, simpler access
- ✅ Use `_namespace` for overwrite control on repeated calls of same action
- ✅ Use `_namespace` to avoid name conflicts between different actions
- ✅ Use `_response_key` for convenient access to action main values
- ✅ Combine `_namespace` and `_response_key` for full control over `_cache` data structure
- ✅ Use meaningful names for `_namespace` and `_response_key`
- ✅ Use `set_cache` to extract data from nesting to flat when needed

**⚠️ Important:**
- `_response_key` works only for actions that support substituting main value key
- If action doesn't support key substitution, `_response_key` ignored (without error)
- Substitution happens automatically before saving to `_cache`

### Saving Context Within Event Processing:

**⚠️ Important:** Cache `_cache` saved **only within one scenario execution chain**. This means data available between scenarios within one chain (when one scenario transitions to another via `jump_to_scenario` or `execute_scenario`), but **NOT saved** between different execution chains (even if triggered by one event) and between different events.

**What is "one execution chain":**
- One chain = sequence of scenarios linked by transitions (`jump_to_scenario`, `execute_scenario`)
- If scenario A transitions to scenario B via `jump_to_scenario` — this is one chain, cache saved
- If scenario A calls scenario B via `execute_scenario` — this is one chain, cache saved
- If event triggers multiple independent scenarios — these are different chains, each has its isolated cache

**What is "one event":**
- One event = one message from user, one callback from button, one scheduled launch, etc.
- If user sent message `/start` — this is one event
- If user clicked button with `callback_data: "menu"` — this is another, separate event
- Each event can trigger multiple scenarios, but each scenario executes independently with its cache

**What is saved within one event:**
- All event data (event data: `user_id`, `chat_id`, `event_text`, etc.)
- All action results (data from `response_data` automatically goes to flat `_cache` or `_cache[_namespace]` if `_namespace` specified, considering key substitution via `_response_key`)
- Temporary data from `_cache` (saved via `set_cache` action or other actions)
- Any other data accumulated in event processing context

**When cache saved (within one execution chain):**

**✅ When transitioning via `jump_to_scenario`:**
```yaml
# Scenario 1: main_scenario
step:
  - action: "set_cache"
    params:
      cache:
        selected_user: "@username"
  
  - action: "send_message"
    transition:
      - action_result: "success"
        transition_action: "jump_to_scenario"
        transition_value: "next_scenario"

# Scenario 2: next_scenario
# ✅ All data from main_scenario available (one execution chain):
step:
  - action: "send_message"
    params:
      text: "User: {_cache.set_cache.selected_user}"  # ✅ Available
```

**When cache NOT saved:**

**❌ Between different scenarios triggered by one event:**
```yaml
# Event: message "/start"

# Scenario 1: welcome_scenario (triggered by "/start")
step:
  - action: "set_cache"
    params:
      cache:
        welcome_sent: true

# Scenario 2: analytics_scenario (also triggered by "/start", but executes independently!)
step:
  - action: "send_message"
    params:
      text: "Welcome sent: {_cache.set_cache.welcome_sent}"  # ❌ NOT available! Different execution chains
```

**❌ Between different events:**
```yaml
# Event 1: User sent "/start"
step:
  - action: "set_cache"
    params:
      cache:
        step: 1

# Event 2: User sent "/menu" (different event!)
step:
  - action: "send_message"
    params:
      text: "Step: {_cache.set_cache.step}"  # ❌ NOT available! Different events
```

---

## 🔄 Transitions (transition)

**Purpose:** Managing scenario execution flow.

```yaml
step:
  - action: "validate"
    params:
      condition: "$user_role == 'admin'"
    transition:
      - action_result: "success"
        transition_action: "jump_to_scenario"
        transition_value: "admin_panel"      # Transition to admin scenario
      - action_result: "error"
        transition_action: "continue"         # Normal flow for users
      - action_result: "timeout"
        transition_action: "break"           # Interrupt only current scenario on timeout
      - action_result: "error"
        transition_action: "abort"           # Interrupt entire chain on critical error
      - action_result: "system_failure"
        transition_action: "stop"            # Interrupt all event processing on system error
```

### Transition Types:

- **`continue`** — continue executing next actions
- **`break`** — interrupt only current scenario execution
- **`abort`** — interrupt entire current scenario chain (including nested)
- **`stop`** — interrupt all event processing (all scenarios)
- **`move_steps`** — move specified number of steps (positive number = forward, negative = backward). E.g., `move_step: 1` jumps to next step, `move_step: 2` skips 1 step and jumps to next
- **`jump_to_step`** — jump to specific step by index (steps numbered from 0, e.g., `jump_to_step: 5` jumps to step with index 5)
- **`jump_to_scenario`** — transition to another scenario (similar to break + jump, current scenario doesn't continue executing)
- **`any`** — universal transition processed first regardless of action result

**Transition Features:**
- **`transition_value`** — required for `move_steps` (number of steps), `jump_to_step` (step index, starting from 0) and `jump_to_scenario` (scenario name)
- **Scenario search** — system looks for scenario in same tenant
- **Transition priority** — `any` transition processed first, regardless of action result
- **Single transition** — always only one transition executed from all possible
- **Blocking other transitions** — if `any` transition exists, other transitions (`success`, `error`, `timeout`, etc.) won't be processed
- **Difference between transitions**:
  - **`break`** — interrupts only current scenario, other scenarios (if any) continue event processing
  - **`abort`** — interrupts entire current scenario chain (including all nested scenarios), but allows other scenarios (from other triggers) to continue working
  - **`stop`** — completely stops event processing in all scenarios, returns control to system
  - **`jump_to_scenario`** — interrupts current scenario execution and transitions to another (similar to break + jump)

---

## 🔧 Placeholders

**Purpose:** Dynamic value substitution in scenario action parameters.

### Mechanics:

**All attributes in `params` automatically processed by placeholders** before action execution. This means:

- **All values in `params`** — strings, numbers, arrays, objects — go through placeholder processing
- **All nesting levels** — placeholders work at any level of `params` structure (in strings, array elements, object values)
- **Automatic processing** — happens for each scenario step before action execution
- **Data source** — system uses accumulated event data and previous action results as value source for substitution

### Placeholder Syntax:

**Simple replacement:**
```yaml
params:
  text: "Hello, {username}!"
  chat_id: "{user_id}"
```

**With modifiers:**
```yaml
params:
  text: "Hello, {username|fallback:Guest}!"
  price: "{amount|*0.9|format:currency}"
```

**Literal values in quotes:**
```yaml
params:
  text: "{'hello'|upper}"                      # HELLO (without passing through dictionary)
  duration: "{'1d 2w'|seconds}"                # 1296000 (literal time)
  calculation: "{'100'|+50}"                   # 150 (literal arithmetic)
  date_shift: "{'2024-12-25'|shift:+1 day}"   # 2024-12-26 (literal date)
  # Double quotes for strings with single quotes
  text: "{"it's working"}"                     # it's working
  # Escaped quotes
  text: "{'it\'s working'}"                    # it's working
```

**Nested placeholders:**
```yaml
params:
  text: "Answer: {status|equals:{expected}|value:OK|fallback:BAD}"
```

### ⚠️ Important: YAML Quotes for Placeholders with regex

**Problem:** YAML processes escape sequences differently in single and double quotes, which is critical for regex patterns with backslashes.

**Solution:** Use **double quotes** for regex patterns with backslashes (`\s`, `\d`, `\w`, etc.).

**Examples:**

```yaml
# ❌ ERROR - in single quotes \\s doesn't escape correctly
params:
  value: '{event_text|regex:^([^\\s]+)|lower}'  # \\s becomes \s (backslash + s), not space!

# ✅ CORRECT - double quotes correctly escape backslashes
params:
  value: "{event_text|regex:^([^\\s]+)|lower}"  # \\s becomes \s (space in regex)

# ✅ CORRECT - for regex without backslashes can use single quotes
params:
  tenant_id: '{user_state|regex:tenant_(\d+)}'  # Works, as \d doesn't require double escaping

# ✅ CORRECT - for simple regex with one backslash also use double quotes
params:
  value: "{event_text|regex:\\s+([^\\s]+)$|lower}"  # \\s for space, \\s for space

# ✅ REGULAR PLACEHOLDERS - no difference
params:
  text: "Hello, {username}!"     # Works
  text: 'Hello, {username}!'    # Also works
```

**When to use double quotes:**
- **Regex patterns with backslashes** — `{field|regex:pattern}` where pattern contains `\s`, `\d`, `\w`, `\n`, `\t`, etc.
- **Important:** In double quotes need to use double escaping: `\\s` for space, `\\d` for digit
- **Example:** `"{event_text|regex:^([^\\s]+)|lower}"` — `\\s` becomes `\s` (space in regex)

**When can use single quotes:**
- **Regex patterns without backslashes** — simple patterns without `\s`, `\d`, `\w`, etc.
- **Regular placeholders** — `{username}`, `{user_id}`
- **Simple modifiers** — `{name|upper}`, `{price|format:currency}`
- **Text values** — without special characters

**Rule:** If regex pattern has backslashes (`\s`, `\d`, `\w`, etc.) — **always use double quotes** with double escaping (`\\s`, `\\d`, `\\w`).

**Access to nested data:**
```yaml
params:
  # Dot notation for objects
  text: "User: {user.profile.name|fallback:Unknown}"
  text: "Message: {message.text}"
  
  # Indexes for arrays
  text: "First file: {attachment[0].file_id}"
  text: "Last user: {users[-1].name}"
  
  # Combined access
  text: "Event: {event.attachment[0].type}"
  text: "Data: {response.data.items[0].value}"
```

### Available Data:

**All event and previous action data available for use in placeholders:**

**Event data:**
- **`user_id`** — user ID
- **`username`** — username  
- **`chat_id`** — chat ID
- **`event_text`** — message text
- **`callback_data`** — callback button data
- **`event_date`** — event time
- **`tenant_id`** — tenant ID
- **`message_id`** — message ID
- **`reply_to_message_id`** — ID of message being replied to
- **`forward_from`** — forwarding data
- **And any other fields** — depending on event type

**Tenant configuration:**
- **`_config`** — dictionary with tenant configuration (attributes from `config.yaml`)
  - **`_config.ai_token`** — AI API key for tenant (if set)
  - **Other attributes** — depending on tenant configuration
  - Automatically available in all tenant scenarios

**Previous action data:**
- **`last_message_id`** — last sent message ID
- **`response_data`** — any data returned by previous actions
- **Other fields** — depending on actions in scenario

### Accessing Nested Elements:

> **Universal data access!** Support for dot notation for objects and indexes for arrays.

<table>
<tr><th>Syntax</th><th>Description</th><th>Example</th><th>Result</th></tr>
<tr><td colspan="4"><strong>Objects</strong></td></tr>
<tr><td><code>object.field</code></td><td>Access object field</td><td><code>{message.text}</code></td><td><code>Hello world</code></td></tr>
<tr><td><code>object.field.subfield</code></td><td>Nested fields</td><td><code>{user.profile.name}</code></td><td><code>John Doe</code></td></tr>
<tr><td colspan="4"><strong>Arrays</strong></td></tr>
<tr><td><code>array[index]</code></td><td>Access array element</td><td><code>{attachment[0].file_id}</code></td><td><code>file_1</code> (first file)</td></tr>
<tr><td><code>array[-index]</code></td><td>Negative index</td><td><code>{attachment[-1].file_id}</code></td><td><code>file_3</code> (last file)</td></tr>
<tr><td><code>array[index].field</code></td><td>Array element field</td><td><code>{users[1].name}</code></td><td><code>Bob</code> (second user name)</td></tr>
<tr><td><code>array[index][index]</code></td><td>Nested arrays</td><td><code>{matrix[0][1]}</code></td><td><code>2</code> (matrix element)</td></tr>
<tr><td colspan="4"><strong>Combined</strong></td></tr>
<tr><td><code>object.array[index].field</code></td><td>Mixed access</td><td><code>{event.attachment[0].file_id}</code></td><td><code>file_1</code></td></tr>
</table>

**Usage Examples:**
```yaml
params:
  # Objects
  text: "Message: {message.text}"
  text: "User: {user.profile.name|fallback:Unknown}"
  
  # Arrays
  text: "First file: {attachment[0].file_id}"
  text: "Last user: {users[-1].name|upper}"
  text: "File: {attachment[0].file_id}, size: {attachment[0].size}"
  
  # Combined access
  text: "Event: {event.attachment[0].type}"
  text: "Data: {response.data.items[0].value}"
  
  # Tenant configuration
  text: "Token: {_config.ai_token|fallback:Not set}"
  
  # Safe access
  text: "{attachment[10].file_id|fallback:File not found}"
```

### Getting File Information

**Practical example: Getting file_id and type for forwarding files**

Create scenario that shows file_id and type of all event attachments:

```yaml
file_info:
  description: "Getting file_id and type of attachments for subsequent forwarding"
  trigger:
    - event_type: "message"
      event_text: "/file"

  step:
    - action: "send_message"
      params:
        text: |
          📎 File information:
          
          file_id: <code>{event_attachment[0].file_id|fallback:{reply_attachment[0].file_id|fallback:File not found}}</code>
          type: <code>{event_attachment[0].type|fallback:{reply_attachment[0].type|fallback:Type not found}}</code>
```

**Error handling:**
- When accessing non-existent field/index returns `None`
- Can use `fallback` modifier for default value
- Negative indexes work like in Python: `-1` = last element
- Unlimited nesting depth supported

### Modifiers:

<table>
<tr><th>Modifier</th><th>Description</th><th>Example</th><th>Result</th></tr>
<tr><td colspan="4"><strong>Arithmetic Operations</strong></td></tr>
<tr><td><code>+value</code></td><td>Addition</td><td><code>{price|+100}</code></td><td><code>1500</code> (if price=1400)</td></tr>
<tr><td><code>-value</code></td><td>Subtraction</td><td><code>{price|-50}</code></td><td><code>1350</code> (if price=1400)</td></tr>
<tr><td><code>*value</code></td><td>Multiplication</td><td><code>{price|*0.9}</code></td><td><code>1260</code> (if price=1400)</td></tr>
<tr><td><code>/value</code></td><td>Division</td><td><code>{seconds|/3600}</code></td><td><code>2.5</code> (if seconds=9000)</td></tr>
<tr><td><code>%value</code></td><td>Modulo</td><td><code>{number|%7}</code></td><td><code>3</code> (if number=10)</td></tr>
<tr><td colspan="4"><strong>Case</strong></td></tr>
<tr><td><code>upper</code></td><td>Uppercase</td><td><code>{name|upper}</code></td><td><code>JOHN</code> (if name="John")</td></tr>
<tr><td><code>lower</code></td><td>Lowercase</td><td><code>{name|lower}</code></td><td><code>john</code> (if name="John")</td></tr>
<tr><td><code>title</code></td><td>Title case each word</td><td><code>{name|title}</code></td><td><code>John Doe</code> (if name="john doe")</td></tr>
<tr><td><code>capitalize</code></td><td>First letter uppercase</td><td><code>{name|capitalize}</code></td><td><code>John</code> (if name="john")</td></tr>
<tr><td><code>case:type</code></td><td>Case conversion</td><td><code>{name|case:upper}</code></td><td><code>JOHN</code> (if name="John")</td></tr>
<tr><td colspan="4"><strong>Lists</strong></td></tr>
<tr><td><code>tags</code></td><td>Convert to tags</td><td><code>{users|tags}</code></td><td><code>@user1 @user2</code></td></tr>
<tr><td><code>list</code></td><td>Bulleted list</td><td><code>{items|list}</code></td><td><code>• item1\n• item2</code></td></tr>
<tr><td><code>comma</code></td><td>Comma separated</td><td><code>{items|comma}</code></td><td><code>item1, item2</code></td></tr>
<tr><td><code>expand</code></td><td>Expand array of arrays one level (in arrays only)</td><td><code>{keyboard|expand}</code></td><td><code>[[a, b], [c]]</code> → <code>[a, b], [c]</code> (in array)</td></tr>
<tr><td><code>keys</code></td><td>Extract keys from object (dict) to array</td><td><code>{storage_values|keys}</code></td><td><code>["group1", "group2"]</code> (if storage_values={"group1": {...}, "group2": {...}})</td></tr>
<tr><td colspan="4"><strong>Transformations</strong></td></tr>
<tr><td><code>code</code></td><td>Wrap value in code block</td><td><code>{field|code}</code></td><td><code>&lt;code&gt;value&lt;/code&gt;</code></td></tr>
<tr><td colspan="4"><strong>Formatting</strong></td></tr>
<tr><td><code>truncate:length</code></td><td>Truncate text</td><td><code>{text|truncate:50}</code></td><td><code>Very long text...</code></td></tr>
<tr><td><code>format:date</code></td><td>Date format</td><td><code>{timestamp|format:date}</code></td><td><code>25.12.2024</code></td></tr>
<tr><td><code>format:time</code></td><td>Time format</td><td><code>{timestamp|format:time}</code></td><td><code>14:30</code></td></tr>
<tr><td><code>format:time_full</code></td><td>Time format with seconds</td><td><code>{timestamp|format:time_full}</code></td><td><code>14:30:45</code></td></tr>
<tr><td><code>format:datetime</code></td><td>Full format</td><td><code>{timestamp|format:datetime}</code></td><td><code>25.12.2024 14:30</code></td></tr>
<tr><td><code>format:datetime_full</code></td><td>Full format with seconds</td><td><code>{timestamp|format:datetime_full}</code></td><td><code>25.12.2024 14:30:45</code></td></tr>
<tr><td><code>format:pg_date</code></td><td>PostgreSQL date format (YYYY-MM-DD)</td><td><code>{timestamp|format:pg_date}</code></td><td><code>2024-12-25</code></td></tr>
<tr><td><code>format:pg_datetime</code></td><td>PostgreSQL date-time format (YYYY-MM-DD HH:MM:SS)</td><td><code>{timestamp|format:pg_datetime}</code></td><td><code>2024-12-25 14:30:45</code></td></tr>
<tr><td><code>seconds</code></td><td>Convert time strings to seconds (supports format: Xw Yd Zh Km Ms)</td><td><code>{duration|seconds}</code></td><td><code>9000</code> (if duration="2h 30m")</td></tr>
<tr><td><code>shift:±interval</code></td><td>Shift date by interval (PostgreSQL style: +1 day, -2 hours, +1 year 2 months). Supports all date formats, correct month/year handling</td><td><code>{created|shift:+1 day}</code></td><td><code>2024-12-26</code> (if created="2024-12-25")</td></tr>
<tr><td colspan="4"><strong>Rounding to Period Start</strong></td></tr>
<tr><td><code>to_date</code></td><td>Round date to day start (00:00:00), returns ISO format</td><td><code>{created|to_date}</code></td><td><code>2024-12-25 00:00:00</code></td></tr>
<tr><td><code>to_hour</code></td><td>Round date to hour start (minutes and seconds = 0), returns ISO format</td><td><code>{created|to_hour}</code></td><td><code>2024-12-25 15:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_minute</code></td><td>Round date to minute start (seconds = 0), returns ISO format</td><td><code>{created|to_minute}</code></td><td><code>2024-12-25 15:30:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_second</code></td><td>Round date to second start (microseconds = 0), returns ISO format</td><td><code>{created|to_second}</code></td><td><code>2024-12-25 15:30:45</code></td></tr>
<tr><td><code>to_week</code></td><td>Round date to week start (Monday 00:00:00), returns ISO format</td><td><code>{created|to_week}</code></td><td><code>2024-12-23 00:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_month</code></td><td>Round date to month start (1st day, 00:00:00), returns ISO format</td><td><code>{created|to_month}</code></td><td><code>2024-12-01 00:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>to_year</code></td><td>Round date to year start (January 1st, 00:00:00), returns ISO format</td><td><code>{created|to_year}</code></td><td><code>2024-01-01 00:00:00</code> (if created="2024-12-25 15:30:45")</td></tr>
<tr><td><code>format:currency</code></td><td>Currency formatting</td><td><code>{amount|format:currency}</code></td><td><code>1000.00 ₽</code></td></tr>
<tr><td><code>format:percent</code></td><td>Percentage formatting</td><td><code>{value|format:percent}</code></td><td><code>25.5%</code></td></tr>
<tr><td><code>format:number</code></td><td>Number formatting</td><td><code>{value|format:number}</code></td><td><code>1234.56</code></td></tr>
<tr><td><code>format:timestamp</code></td><td>Convert to timestamp</td><td><code>{date|format:timestamp}</code></td><td><code>1703512200</code></td></tr>
<tr><td colspan="4"><strong>Conditional</strong></td></tr>
<tr><td><code>equals:value</code></td><td>Equality check (string comparison)</td><td><code>{status|equals:active}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>in_list:items</code></td><td>Check inclusion in list</td><td><code>{role|in_list:admin,moderator}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>true</code></td><td>Truth check (recommended for boolean)</td><td><code>{is_active|true}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>exists</code></td><td>Check value existence (not None and not empty string)</td><td><code>{field|exists}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>is_null</code></td><td>Check for null (None, empty string or string "null")</td><td><code>{field|is_null}</code></td><td><code>true</code> or <code>false</code></td></tr>
<tr><td><code>value:result</code></td><td>Return value when true</td><td><code>{status|equals:active|value:Active}</code></td><td><code>Active</code> or <code>null</code></td></tr>
<tr><td colspan="4"><strong>Utility</strong></td></tr>
<tr><td><code>fallback:value</code></td><td>Default value</td><td><code>{username|fallback:Guest}</code></td><td><code>John</code> or <code>Guest</code></td></tr>
<tr><td><code>length</code></td><td>Count length</td><td><code>{text|length}</code></td><td><code>15</code> (character count)</td></tr>
<tr><td><code>length</code></td><td>Count array length</td><td><code>{array|length}</code></td><td><code>3</code> (element count)</td></tr>
<tr><td><code>regex:pattern</code></td><td>Extract by regex</td><td><code>{text|regex:(\d+)}</code></td><td><code>123</code> (first number)</td></tr>
<tr><td colspan="4"><strong>Async Actions</strong></td></tr>
<tr><td><code>ready</code></td><td>Check async action readiness</td><td><code>{_async_action.ai_req_1|ready}</code></td><td><code>true</code> if completed, <code>false</code> if executing</td></tr>
<tr><td><code>not_ready</code></td><td>Check action still executing</td><td><code>{_async_action.ai_req_1|not_ready}</code></td><td><code>true</code> if executing, <code>false</code> if ready</td></tr>
</table>

### Usage Examples:

```yaml
params:
  # Simple operations
  result: "{value|+100|format:currency}"
  
  # Conditional logic
  status: "{user_status|equals:active|value:Active|fallback:Inactive}"
  
  # Modifier chain
  formatted: "{price|*0.9|format:currency|fallback:0.00 ₽}"
  
  # Regex extraction (use double quotes for backslashes!)
  duration: "{event_text|regex:(\\d+)\\s*min|fallback:0}"
  
  # Dot notation
  name: "{user.profile.name|fallback:Unknown}"
  
  # Time values
  duration_seconds: "{duration|seconds}"
  duration_minutes: "{duration|seconds|/60}"
  duration_hours: "{duration|seconds|/3600}"
  formatted_time: "{duration|seconds|format:number}"
  
  # Date shifting
  tomorrow: "{created|shift:+1 day}"
  next_month: "{created|shift:+1 month|format:date}"
  complex_shift: "{created|shift:+1 year 2 months|format:datetime}"
  
  # Rounding to period start
  start_of_day: "{created|to_date}"
  start_of_week: "{created|to_week}"
  formatted_month_start: "{created|to_month|format:date}"
  
  # Boolean fields (distinguish True/False/None)
  is_active: "{is_active|equals:True|value:✅ Enabled|fallback:{is_active|equals:False|value:❌ Disabled|fallback:❓ Unknown}}"
  is_polling: "{is_polling|equals:True|value:✅ Active|fallback:{is_polling|equals:False|value:❌ Inactive|fallback:❓ Unknown}}"
  
  # String fields (use equals:value)
  status: "{user_status|equals:active|value:Active|fallback:Inactive}"
  
  # Simplified version (if None not expected)
  is_simple: "{is_active|true|value:✅ Enabled|fallback:❌ Disabled}"
  
  # Check value existence (in conditions)
  # In conditions use: {field|exists} == True or {field|exists} == False
  
  # Check for null (in conditions)
  # In conditions use: {field|is_null} == True or {field|is_null} == False
```

**Example using exists in conditions:**

```yaml
step:
  - action: "validate"
    params:
      condition: "{response_value.feedback|exists} == True"
    transition:
      - action_result: "success"
        transition_action: "continue"  # Value exists
      - action_result: "failed"
        transition_action: "jump_to_scenario"
        transition_value: "create_feedback"  # Value doesn't exist
```

### Important: boolean vs string fields

**For boolean fields (True/False):**
- **Recommended:** `{is_active|true|value:✅ Enabled|fallback:❌ Disabled}`
- **Doesn't work:** `{is_active|equals:true|value:✅ Enabled}` (string comparison)

**For string fields:**
- **Use:** `{status|equals:active|value:Active|fallback:Inactive}`
- `true` modifier not suitable for string values

### Practical Examples:

#### **Example 1: Personalized greeting**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        👋 Hello, {username|fallback:Guest}!
        
        📊 Your statistics:
        • ID: {user_id}
        • Chats: {chat_count|fallback:0}
        • Last login: {last_login|format:datetime|fallback:Unknown}
```

#### **Example 2: Dynamic menu with conditions**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        🎛️ Main Menu
        
        Status: {user_status|equals:active|value:✅ Active|fallback:❌ Inactive}
        Balance: {balance|format:currency|fallback:0.00 ₽}
      inline:
        - [{"📊 Statistics": "stats"}, {"💰 Balance": "balance"}]
        - [{"⚙️ Settings": "settings"}]
```

#### **Example 3: Error handling with fallback**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        ❌ Processing error
        
        Error code: {error_code|fallback:UNKNOWN}
        Message: {error_message|fallback:Unknown error}
        Time: {timestamp|format:datetime}
      inline:
        - [{"🔄 Retry": "retry"}, {"🏠 Main Menu": "main"}]
```

#### **Example 4: Mathematical calculations**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        💰 Cost calculation
        
        Price: {base_price|format:currency}
        Discount: {discount_percent|fallback:0}%
        Total: {base_price|*{discount_percent|/100}|*{base_price|-1}|+{base_price}|format:currency}
```

#### **Example 5: Extracting data from text**
```yaml
step:
  - action: "send_message"
    params:
      text: |
        📝 Processing order
        
        Order number: "{event_text|regex:order\\s*(\\d+)|fallback:Not found}"
        Amount: "{event_text|regex:amount\\s*(\\d+)|format:currency|fallback:0.00 ₽}"
        Delivery time: "{event_text|regex:(\\d+)\\s*min|fallback:30}" minutes
```

#### **Example 6: Transition to scenario (interrupt current)**
```yaml
step:
  - action: "check_user_role"
    params:
      required_role: "admin"
    transition:
      - action_result: "success"
        transition_action: "jump_to_scenario"
        transition_value: "admin_panel"      # Transition to admin panel, current scenario interrupts
      - action_result: "error"
        transition_action: "continue"        # Continue executing current scenario
  
  # This step won't execute if jump_to_scenario triggered
  - action: "send_message"
    params:
      text: "Regular menu for users"
```

#### **Example 7: Moving through steps**
```yaml
step:
  - action: "check_permissions"
    params:
      required_role: "admin"
    transition:
      - action_result: "success"
        transition_action: "move_steps"
        transition_value: 2                 # Move 2 steps forward (skip 1 step, go to next)
      - action_result: "error"
        transition_action: "continue"        # Execute all steps
```

#### **Example 7.1: Jump to specific step**
```yaml
step:
  - action: "validate"
    params:
      condition: "$user_role == 'admin'"
    transition:
      - action_result: "success"
        transition_action: "jump_to_step"
        transition_value: 5                 # Jump to step with index 5 (steps numbered from 0)
      - action_result: "failed"
        transition_action: "continue"       # Continue execution
```

#### **Example 8: Universal transition "any"**
```yaml
step:
  - action: "send_message"
    params:
      text: "Message sent"
    transition:
      - action_result: "any"                 # Executes regardless of result
        transition_action: "abort"           # Always interrupt execution
      - action_result: "success"
        transition_action: "continue"        # ❌ This transition won't execute due to "any"
      - action_result: "error"
        transition_action: "continue"        # ❌ This transition won't execute due to "any"
```

**⚠️ Important:** `any` transition has highest priority and blocks execution of all other transitions. System always executes only one transition from all possible.

#### **Example 9: Dynamic keyboard with expand modifier**
```yaml
step:
  # Get tenant list
  - action: "get_tenants_list"
    params: {}
  
  # Build dynamic keyboard from public tenants
  - action: "build_keyboard"
    params:
      items: "{public_tenant_ids}"
      keyboard_type: "inline"
      text_template: "Tenant $value$"
      callback_template: "select_tenant_$value$"
      buttons_per_row: 2
  
  # Send message with dynamic keyboard + static buttons
  - action: "send_message"
    params:
      text: "Select tenant:"
      inline:
        - "{keyboard|expand}"              # Expand dynamic keyboard
        - [{"🔙 Back": "main_menu"}]      # Static button
```

**How `expand` works:**
- `expand` modifier expands array of arrays one level **only when used in array**
- In example above `{keyboard|expand}` in `inline` array expands `[[{...}, {...}], [{...}]]` to `[{...}, {...}], [{...}]`
- This allows combining dynamically generated keyboard rows with static rows
- **Important:** `expand` works only in array context. In string or dict value remains unchanged

**Example without expand (incorrect):**
```yaml
inline:
  - "{keyboard}"                           # ❌ Gets [[[...]], [...]] - 3 nesting levels!
  - [{"🔙 Back": "main_menu"}]
```

**Example with expand (correct):**
```yaml
inline:
  - "{keyboard|expand}"                     # ✅ Gets [[...], [...]] - 2 nesting levels
  - [{"🔙 Back": "main_menu"}]
```

---

## ⚡ Async Actions

**Purpose:** Launch long actions in background with ability to continue scenario execution and check result readiness.

### Mechanics:

Async actions allow launching long operations (e.g., LLM requests, large data processing) in background without blocking scenario execution. Scenario can continue executing other actions, check result readiness and wait for completion when necessary.

### Async Action Structure:

```yaml
step:
  - step_id: 1
    action_name: "ai_request"
    async: true                    # Async execution flag
    action_id: "ai_req_1"         # Unique ID for tracking (required)
    params:
      prompt: "Hello!"
```

**Parameters:**
- **`async: true`** — flag that action should execute asynchronously
- **`action_id`** — unique action identifier (required for async actions)
- **`action_name`** — action name to execute
- **`params`** — action parameters

### How Async Action Mechanism Works:

**What happens when launching async action:**

1. **Launch action in background:**
   - When launching async action it starts executing in background without blocking scenario execution
   - Scenario continues working and can execute other actions while async action executes
   - System automatically tracks action execution state

2. **Save action reference in `_async_action`:**
   - System saves reference to executing action in special field `_async_action[action_id]`
   - `_async_action` — system dictionary storing all launched async actions
   - Dictionary key — `action_id` (which you specified), value — reference to executing action
   - **Important:** `_async_action` stored separately from `_cache` to be available for readiness checks between steps

3. **Automatic state tracking:**
   - When action completes (successfully or with error), system automatically updates its state
   - Update happens automatically in background, regardless of scenario execution
   - Can check readiness via placeholder `{_async_action.action_id|ready}` at any time

**Why syntax `{_async_action.action_id|ready}` is used:**

- `_async_action` — system field automatically created when launching async actions
- `action_id` — ID you specified when launching async action (e.g., `"ai_req_1"`)
- `ready` — modifier checking if action completed (returns `True` if ready, `False` if still executing)
- This allows using readiness check in validation conditions and creating complex scenarios with waits

**Example:**
After launching several async actions system automatically creates structure:
- `_async_action["ai_req_1"]` — reference to first AI request
- `_async_action["data_proc_1"]` — reference to data processing
- `_async_action["ai_req_2"]` — reference to second AI request

You can check readiness of any via placeholder: `{_async_action.ai_req_1|ready}`

### Checking Readiness:

To check async action readiness use `ready` and `not_ready` modifiers in placeholders. This allows creating complex scenarios with waits via validation and transitions.

**Modifiers:**
- **`{_async_action.action_id|ready}`** — returns `True` if action completed, `False` if still executing
- **`{_async_action.action_id|not_ready}`** — returns `True` if action still executing, `False` if ready

**How it works:**
- Placeholder `{_async_action.action_id|ready}` accesses system field `_async_action` and checks state of action with specified `action_id`
- `ready` modifier checks if action completed — returns `True` if action ready, `False` if still executing
- Result can be used in validation conditions to create wait loops and complex logic

**Usage example in validation:**
```yaml
step:
  - action: "validate"
    params:
      condition: "{_async_action.ai_req_1|ready} == True"  # Check readiness
    transition:
      - action_result: "failed"
        transition_action: "move_steps"
        transition_value: -2  # Go back if not ready yet
```

### Waiting for Result:

To get async action result use `wait_for_action` action:

```yaml
step:
  - step_id: 3
    action_name: "wait_for_action"
    params:
      action_id: "ai_req_1"
      timeout: 60  # Optional timeout in seconds
```

**Parameters:**
- **`action_id`** — async action ID to wait for (required)
- **`timeout`** — wait timeout in seconds (optional)

**Result:**
- `wait_for_action` returns main action result **AS IS** (as if it executed directly)
- If main action completed successfully → returns its result with `response_data`, which automatically goes to flat `_cache` (or `_cache[_namespace]` if `_namespace` specified, considering key substitution via `_response_key`)
- If main action completed with error → returns its error
- If wait error (timeout, Future not found) → returns `wait_for_action` error

### Practical Example:

```yaml
ai_processing:
  description: "Processing AI request with loading indicator"
  trigger:
    - event_type: "message"
      event_text: "/ai"

  step:
    # Step 1: Launch AI request asynchronously
    - action: "completion"
      async: true
      action_id: "ai_req_1"
      params:
        prompt: "{event_text|regex:/ai\\s+(.+)}"
    
    # Step 2: Send loading message
    - action: "send_message"
      params:
        text: "⏳ Processing request..."
    
    # Step 3: Delay before check
    - action: "sleep"
      params:
        seconds: 1.0  # 1 second delay between checks
    
    # Step 4: Check readiness via validation
    # Use placeholder {_async_action.ai_req_1|ready} to check action state
    - action: "validate"
      params:
        condition: "{_async_action.ai_req_1|ready} == True"
      transition:
        - action_result: "failed"
          transition_action: "move_steps"
          transition_value: -1  # Go back to delay step (step 3) if not ready yet
    
    # Step 5: Delete loading message (executes only when action ready)
    - action: "delete_message"
      params:
        delete_message_id: "{last_message_id}"
    
    # Step 6: Wait for AI result (get data into context)
    - action: "wait_for_action"
      params:
        action_id: "ai_req_1"
        timeout: 60  # 60 second timeout
    # response_data goes to flat _cache = {response_completion: "AI answer", prompt_tokens: 50, completion_tokens: 100}
    
    # Step 7: Send AI result
    - action: "send_message"
      params:
        text: "{_cache.response_completion|fallback:Processing error}"
```

**What happens in this example:**
1. Async action launched — system saves reference to it in `_async_action["ai_req_1"]`
2. Loading message sent
3. 1 second delay made (prevents 100% CPU)
4. Readiness checked via validation — placeholder `{_async_action.ai_req_1|ready}` checks if action completed
5. If not ready — go back to delay step (loop: delay → check → delay → check...)
6. If ready — delete loading message and get result

**This example shows:**
- How to use readiness check via validation to create wait loops
- How to properly organize loop with delay to prevent 100% CPU
- Placeholder `{_async_action.action_id|ready}` mechanics in validation conditions

### Important Features:

**1. Result goes to context only via `wait_for_action`:**
- Main action result goes to scenario `_cache` only after calling `wait_for_action`
- `wait_for_action` gets result from completed action and returns it as regular action result
- Result automatically saved to flat `_cache` (or `_cache[_namespace]` if `_namespace` specified, considering key substitution via `_response_key`)
- Without `wait_for_action` result remains in system and not available in scenario via placeholders

**2. Multiple async actions:**
- Can launch multiple async actions simultaneously with different `action_id`
- Each action tracked independently via its `action_id` in `_async_action`
- Can check each action readiness separately: `{_async_action.action_id_1|ready}`, `{_async_action.action_id_2|ready}`
- Can create complex conditions: `{_async_action.ai_1|ready} and {_async_action.data_1|ready}`

**3. Timeouts:**
- Can specify `timeout` in `wait_for_action` to limit wait time
- On timeout `wait_for_action` returns `timeout` error, but scenario execution continues
- Main action continues executing in background even after timeout — action reference remains in `_async_action` and can check readiness later

### Example with Multiple Async Actions:

```yaml
parallel_processing:
  description: "Parallel processing of multiple requests"
  trigger:
    - event_type: "message"
      event_text: "/process"

  step:
    # Launch multiple actions in parallel
    - action: "completion"
      async: true
      action_id: "ai_1"
      params:
        prompt: "Question 1"
    # response_data: {"response_completion": "Answer 1", "prompt_tokens": 50, "completion_tokens": 100}
    
    - action: "process_data"
      async: true
      action_id: "data_proc_1"
      params:
        data: "{event_text}"
    # response_data: {"processed_data": "Processed data", "status": "success"}
    
    # Wait for AI result (saved to _cache)
    # IMPORTANT: Don't use readiness check loop without delay - leads to 100% CPU!
    # Just wait for result directly via wait_for_action with timeout
    - action: "wait_for_action"
      params:
        action_id: "ai_1"
        timeout: 60  # 60 second timeout
    # wait_for_action returns main action result AS IS
    # response_data from result goes to flat _cache = {response_completion: "Answer 1", prompt_tokens: 50, completion_tokens: 100}
    
    # Wait for data processing result (saved to _cache)
    - action: "wait_for_action"
      params:
        action_id: "data_proc_1"
        timeout: 30  # 30 second timeout
        _namespace: "data_processing"  # Use custom key to save both results
    # response_data goes to _cache.data_processing = {processed_data: "Processed data", status: "success"}
    
    # Use results (all data available via _cache)
    - action: "send_message"
      params:
        text: |
          AI answer: {_cache.response_completion|fallback:Not received}
          Tokens: {_cache.completion_tokens|fallback:0}
          Processed data: {_cache.data_processing.processed_data|fallback:Not processed}
          Status: {_cache.data_processing.status|fallback:Unknown}
```

**ℹ️ Important:** 
- `wait_for_action` returns main action result **AS IS** (as if it executed directly)
- Result processed at `scenario_engine` level as regular `response_data`
- Data goes to flat `_cache` (or `_cache[_namespace]` if `_namespace` specified, considering key substitution via `_response_key`)
- If `wait_for_action` called twice without `_namespace`, second result overwrites first (data merged via deep merge)
- **Solution:** Use `_namespace` to save different async action results to different keys
- **Additionally:** Use `_response_key` for convenient substitution of replaceable field key in async action results

### Recommendations:

1. **Always specify `action_id`** for async actions — this is only way to track their status
2. **Add timeouts** to `wait_for_action` for long operations — prevents infinite wait
3. **Handle errors** — add `transition` to handle `error` and `timeout` results in `wait_for_action`
4. **Use readiness check loops with delay** — if need readiness check loop, must add `sleep` before returning to check
5. **For multiple async actions use `wait_for_action` directly** — don't create readiness check loops for multiple actions, just wait each via `wait_for_action` with timeout
6. **Use `_namespace`** to save different async action results to different `_cache` keys
