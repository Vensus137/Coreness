---
title: System Actions Guide
description: Reference for Coreness system actions. Special actions for internal operations and integrations.
keywords: system actions, coreness system actions, internal operations
---

# 🎯 System Actions Guide

> **Note:** This guide is being translated. Some parts may still be in Russian or incomplete.

Complete description of all available actions with their parameters and results.

## 📋 Table of Contents

- [action_hub](#action_hub) (1 actions)
  - [get_available_actions](#get_available_actions)
- [event_processor](#event_processor) (1 actions)
  - [process_event](#process_event)
- [scenario_processor](#scenario_processor) (3 actions)
  - [process_scenario_event](#process_scenario_event)
  - [sync_scenarios](#sync_scenarios)
  - [sync_tenant_scenarios](#sync_tenant_scenarios)
- [storage_hub](#storage_hub) (1 actions)
  - [sync_tenant_storage](#sync_tenant_storage)
- [telegram_bot_manager](#telegram_bot_manager) (11 actions)
  - [get_bot_info](#get_bot_info)
  - [get_bot_status](#get_bot_status)
  - [get_telegram_bot_info](#get_telegram_bot_info)
  - [set_bot_token](#set_bot_token)
  - [start_bot](#start_bot)
  - [stop_all_bots](#stop_all_bots)
  - [stop_bot](#stop_bot)
  - [sync_bot](#sync_bot)
  - [sync_bot_commands](#sync_bot_commands)
  - [sync_bot_config](#sync_bot_config)
  - [sync_telegram_bot](#sync_telegram_bot)
- [tenant_hub](#tenant_hub) (8 actions)
  - [get_tenant_status](#get_tenant_status)
  - [get_tenants_list](#get_tenants_list)
  - [sync_all_tenants](#sync_all_tenants)
  - [sync_tenant](#sync_tenant)
  - [sync_tenant_config](#sync_tenant_config)
  - [sync_tenant_data](#sync_tenant_data)
  - [sync_tenants_from_files](#sync_tenants_from_files)
  - [update_tenant_config](#update_tenant_config)

<a id="action_hub"></a>
## action_hub

**Description:** Central action hub for routing to services

<a id="get_available_actions"></a>
### get_available_actions

**Description:** Get all available actions with metadata

**Input Parameters:**

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
- **`response_data`** (`object`) — Dict of all available actions with metadata

**Usage Example:**

```yaml
# In scenario
- action: "get_available_actions"
  params:
    # Parameters not required
```


<a id="event_processor"></a>
## event_processor

**Description:** Service for processing polling events

<a id="process_event"></a>
### process_event

**Description:** Process polling event

**Input Parameters:**

- **`data`** (`object`) — Raw event from polling

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "process_event"
  params:
    data: {}
```


<a id="scenario_processor"></a>
## scenario_processor

**Description:** Service for processing events by scenarios

<a id="process_scenario_event"></a>
### process_scenario_event

**Description:** Process event by scenarios

**Input Parameters:**

- **`event_type`** (`string`, required, min length: 1) — Event type (message, callback_query, etc.)
- **`bot_id`** (`integer`, required, min: 1) — Bot ID that received the event

**Output Parameters:**

- **`result`** (`string`) — Processing result (success/error)
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "process_scenario_event"
  params:
    event_type: "example"
    bot_id: 123
```


<a id="sync_scenarios"></a>
### sync_scenarios

**Description:** Sync tenant scenarios: delete old → save new → reload cache

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID for scenario sync
- **`scenarios`** (`array (of object)`) — Array of scenarios to sync

**Output Parameters:**

- **`result`** (`string`) — Sync result (success/partial_success/error)
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "sync_scenarios"
  params:
    tenant_id: 123
    scenarios: []
```


<a id="sync_tenant_scenarios"></a>
### sync_tenant_scenarios

**Description:** Sync tenant scenarios: parse scenarios/*.yaml + sync to database

**Input Parameters:**

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
- action: "sync_tenant_scenarios"
  params:
    tenant_id: 123
```


<a id="storage_hub"></a>
## storage_hub

**Description:** Service for managing tenant storage

<a id="sync_tenant_storage"></a>
### sync_tenant_storage

**Description:** Sync tenant storage: parse storage/*.yaml + sync to database

**Input Parameters:**

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
- action: "sync_tenant_storage"
  params:
    tenant_id: 123
```


<a id="telegram_bot_manager"></a>
## telegram_bot_manager

**Description:** Service for managing Telegram bot lifecycle

<a id="get_bot_info"></a>
### get_bot_info

**Description:** Get bot info from database (with caching)

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`force_refresh`** (`boolean`, optional) — Force refresh cache

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Request result
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Bot data from database
  - **`bot_id`** (`integer`) — Bot ID
  - **`telegram_bot_id`** (`integer`) — Bot ID in Telegram
  - **`tenant_id`** (`integer`) — Tenant ID
  - **`bot_token`** (`string`) — Bot token
  - **`username`** (`string`) — Bot username
  - **`first_name`** (`string`) — Bot first name
  - **`is_active`** (`boolean`) — Whether bot is active
  - **`bot_command`** (`array`) — Bot commands

**Usage Example:**

```yaml
# In scenario
- action: "get_bot_info"
  params:
    bot_id: 123
    # force_refresh: boolean (optional)
```


<a id="get_bot_status"></a>
### get_bot_status

**Description:** Get polling status and bot activity

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Request result
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Bot status
  - **`is_polling`** (`boolean`) — Whether polling is active
  - **`is_webhook_active`** (`boolean`) — Whether webhook is active
  - **`is_active`** (`boolean`) — Whether bot is active
  - **`is_working`** (`boolean`) — Whether bot is working (polling or webhook)

**Usage Example:**

```yaml
# In scenario
- action: "get_bot_status"
  params:
    bot_id: 123
```


<a id="get_telegram_bot_info"></a>
### get_telegram_bot_info

**Description:** Get bot info via Telegram API

**Input Parameters:**

- **`bot_token`** (`string`, required, min length: 1) — Telegram bot token

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Request result
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) — Bot data from Telegram API
  - **`telegram_bot_id`** (`integer`) — Bot ID in Telegram
  - **`username`** (`string`) — Bot username
  - **`first_name`** (`string`) — Bot first name

**Usage Example:**

```yaml
# In scenario
- action: "get_telegram_bot_info"
  params:
    bot_token: "example"
```


<a id="set_bot_token"></a>
### set_bot_token

**Description:** Set bot token

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`bot_token`** (`string|None`, optional) — Bot token or null to clear

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "set_bot_token"
  params:
    tenant_id: 123
    # bot_token: string|None (optional)
```


<a id="start_bot"></a>
### start_bot

**Description:** Start bot (polling or webhook)

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "start_bot"
  params:
    bot_id: 123
```


<a id="stop_all_bots"></a>
### stop_all_bots

**Description:** Stop all bots

**Input Parameters:**


**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "stop_all_bots"
  params:
```


<a id="stop_bot"></a>
### stop_bot

**Description:** Stop bot

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "stop_bot"
  params:
    bot_id: 123
```


<a id="sync_bot"></a>
### sync_bot

**Description:** Sync bot: config + commands

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`bot_token`** (`string`, required, min length: 1) — Telegram bot token
- **`is_active`** (`boolean`, optional) — Whether bot is active
- **`bot_commands`** (`array`, optional) — List of bot commands

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
- **`response_data`** (`object`) (optional) — Response data (bot_id, action)
  - **`bot_id`** (`integer`) — Bot ID
  - **`action`** (`string`) — Action performed

**Usage Example:**

```yaml
# In scenario
- action: "sync_bot"
  params:
    tenant_id: 123
    bot_token: "example"
    # is_active: boolean (optional)
    # bot_commands: array (optional)
```


<a id="sync_bot_commands"></a>
### sync_bot_commands

**Description:** Sync bot commands: save to DB → apply in Telegram

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — Bot ID
- **`command_list`** (`array`) — List of bot commands

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "sync_bot_commands"
  params:
    bot_id: 123
    command_list: []
```


<a id="sync_bot_config"></a>
### sync_bot_config

**Description:** Sync bot config: create/update bot + start

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`bot_token`** (`string`, optional, min length: 1) — Telegram bot token
- **`is_active`** (`boolean`) — Whether bot is active

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
  - **`bot_id`** (`integer`) — Bot ID
  - **`action`** (`string`) — Action performed

**Usage Example:**

```yaml
# In scenario
- action: "sync_bot_config"
  params:
    tenant_id: 123
    # bot_token: string (optional)
    is_active: true
```


<a id="sync_telegram_bot"></a>
### sync_telegram_bot

**Description:** Sync Telegram bot for tenant: parse bots/telegram.yaml + create/update bot + sync commands + start

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, not_found
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details
- **`response_data`** (`object`) (optional) — Response data (bot_id, action)
  - **`bot_id`** (`integer`) — Bot ID
  - **`action`** (`string`) — Action performed

**Usage Example:**

```yaml
# In scenario
- action: "sync_telegram_bot"
  params:
    tenant_id: 123
```


<a id="tenant_hub"></a>
## tenant_hub

**Description:** Orchestrator service for managing tenants. Coordinates GitHub sync, delegates parsing and sync to specialized services

<a id="get_tenant_status"></a>
### get_tenant_status

**Description:** Get tenant status

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID

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
  - **`bot_is_active`** (`boolean`) — Whether tenant bot is active from DB settings (is_active flag)
  - **`bot_is_polling`** (`boolean`) — Whether tenant bot polling is active (polling process running)
  - **`bot_is_webhook_active`** (`boolean`) — Whether tenant bot webhook is active (webhook set via Telegram API)
  - **`bot_is_working`** (`boolean`) — Whether tenant bot is working (polling OR webhooks active). Actual bot status
  - **`last_updated_at`** (`string`) (optional) — Date of last successful tenant update
  - **`last_failed_at`** (`string`) (optional) — Date of last error when updating tenant
  - **`last_error`** (`string`) (optional) — Text of last error when updating tenant

**Usage Example:**

```yaml
# In scenario
- action: "get_tenant_status"
  params:
    tenant_id: 123
```


<a id="get_tenants_list"></a>
### get_tenants_list

**Description:** Get list of all tenant IDs split into public and system

**Input Parameters:**


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
- **`response_data`** (`object`) — 
  - **`tenant_ids`** (`array (of integer)`) — Array of all tenant IDs
  - **`public_tenant_ids`** (`array (of integer)`) — Array of public tenant IDs
  - **`system_tenant_ids`** (`array (of integer)`) — Array of system tenant IDs
  - **`tenant_count`** (`integer`) — Total number of tenants

**Usage Example:**

```yaml
# In scenario
- action: "get_tenants_list"
  params:
```


<a id="sync_all_tenants"></a>
### sync_all_tenants

**Description:** Sync all tenants (pull from GitHub first, then sync all)

**Input Parameters:**


**Output Parameters:**

- **`result`** (`string`) — Result: success, partial_success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "sync_all_tenants"
  params:
```


<a id="sync_tenant"></a>
### sync_tenant

**Description:** Sync tenant configuration with database (fetch from GitHub first, then sync)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID to sync

**Output Parameters:**

- **`result`** (`string`) — Result: success, error, timeout, not_found
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant"
  params:
    tenant_id: 123
```


<a id="sync_tenant_config"></a>
### sync_tenant_config

**Description:** Sync tenant config: pull from GitHub + parse + sync

**Input Parameters:**

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
- action: "sync_tenant_config"
  params:
    tenant_id: 123
```


<a id="sync_tenant_data"></a>
### sync_tenant_data

**Description:** Sync tenant data: create/update tenant

**Input Parameters:**

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
- action: "sync_tenant_data"
  params:
    tenant_id: 123
```


<a id="sync_tenants_from_files"></a>
### sync_tenants_from_files

**Description:** Sync tenants from list of changed files (universal method for webhooks and polling)

**Input Parameters:**

- **`files`** (`array (of string)`) — List of files in format ["path1", "path2"] or [{"filename": "path"}, ...]

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Result: success, partial_success, error
- **`response_data`** (`object`) (optional) — Response data (synced_tenants, total_tenants, errors)
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenants_from_files"
  params:
    files: []
```


<a id="update_tenant_config"></a>
### update_tenant_config

**Description:** Update tenant config (updates DB, invalidates cache). Only updates provided fields

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — Tenant ID
- **`ai_token`** (`string|None`, optional) — AI API token for tenant (optional; if not passed - field unchanged, if null - removed)

**Output Parameters:**

- **`result`** (`string`) — Result: success, error
- **`error`** (`object`) (optional) — Error structure
  - **`code`** (`string`) — Error code
  - **`message`** (`string`) — Error message
  - **`details`** (`array`) (optional) — Error details

**Usage Example:**

```yaml
# In scenario
- action: "update_tenant_config"
  params:
    tenant_id: 123
    # ai_token: string|None (optional)
```

