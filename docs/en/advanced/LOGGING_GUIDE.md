---
title: Logging Guide
description: Working with logs in Coreness. Log structure, log level configuration, Docker logs and debugging.
keywords: coreness logging, logs, debugging, docker logs, log levels
---

# Logging Guide

## Overview

The logging system uses **named loggers** with color highlighting by patterns. Each module gets its own named logger through the `logger` utility.

## What's in logger

- Named loggers for each module
- Color highlighting by patterns (console)
- File logging (`logs/core.log`)
- Log file rotation
- Smart formatting with colors

## Logging Levels

### `INFO` — informational messages

**Purpose:** Brief and essential **only about current function**. Don't describe functionality "inside".

**Examples:**
- `[Tenant-137] Parsing scenarios...`
- `[Tenant-1] [Bot-1] Bot updated`
- `Synchronizing {X} scenario groups...`

**Rules:**
- ✅ Brief and concise
- ✅ Only about current function
- ✅ Each function is self-sufficient in logging
- ❌ Don't describe what happens inside other functions

### `WARNING` — warnings

**Purpose:** Requires attention but not critical.

**Examples:**
- GitHub update error but continue working
- Skip group without name
- Missing token, polling not started

**Rules:**
- Use when process can continue
- Specify reason and action

### `ERROR` — errors

**Purpose:** Critical — process operation disrupted.

**Examples:**
- `[Tenant-137] Scenario parsing error: ...`
- `Scenario synchronization error: ...`
- Failed to create/update bot

**Rules:**
- Write on real errors
- Specify error reason

### `DEBUG` — debugging

**Purpose:** Used only when investigating errors and issues.

**Rules:**
- ❌ Not used in production code
- ✅ Only by user request for debugging

## Highlighting Patterns

System automatically highlights patterns in logs with colors. Available highlighting types:

### Square brackets `[...]` — Cyan (blue)

**Purpose:** Context — entity IDs, modules, services.

**Examples:**
- `[Tenant-137]` — tenant ID
- `[Bot-1]` — bot ID
- `[Queue-action]` — queue name
- `[Service-name]` — service name
- `[Module-name]` — module name

**Rules:**
1. **Hierarchy:** Tenant first, then Bot (if present)
   ```python
   # ✅ Correct
   self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Bot updated")
   
   # ❌ Incorrect
   self.logger.info(f"[Bot-{bot_id}] [Tenant-{tenant_id}] Bot updated")
   ```

2. **Format:** `[Entity-ID]` or `[Entity-name]`
   ```python
   [Tenant-137]           # Entity ID
   [Queue-critical]       # Entity name
   [Service-bot_hub]      # Service name
   ```

3. **Multiple contexts:** Separate with spaces
   ```python
   [Tenant-1] [Bot-2] Command synchronization
   [Queue-system] Processing task
   ```

### Parentheses `(...)` — Yellow

**Purpose:** Statuses, states, additional information.

**Examples:**
- `(error)` — error status
- `(warning)` — warning
- `(active)` — activity state
- `(3 groups)` — group count

**Rules:**
```python
self.logger.info(f"[Tenant-137] Synchronization (3 groups)")
self.logger.warning(f"[Bot-1] Missing token (polling not started)")
```

### Curly braces `{...}` — Green

**Purpose:** Data, configuration, values.

**Examples:**
- `{config}` — configuration
- `{tenant_id: 137}` — data
- `{status: active}` — values

**Rules:**
```python
# Usually used in placeholders
self.logger.info(f"Loading {count} scenarios")
```

### HTTP codes — Magenta (purple)

**Purpose:** HTTP status codes.

**Examples:**
- `HTTP 200` — success
- `HTTP 404` — not found
- `HTTP 500` — server error

## Pattern Summary Table

| Pattern | Color | Purpose | Example |
|---------|------|------------|--------|
| `[Entity-ID]` | Cyan | Context (Tenant, Bot, Service) | `[Tenant-137] [Bot-1]` |
| `(status)` | Yellow | Statuses, states | `(active)`, `(error)` |
| `{data}` | Green | Data, values | `{count}`, `{config}` |
| `HTTP XXX` | Magenta | HTTP codes | `HTTP 200`, `HTTP 404` |

## Using Colors and Formatting

### Colors
- Use built-in logger color highlighting (automatic)
- Colors applied to logging levels

### Patterns
- Use patterns like `[Entity-ID]` for structuring
- Helps in log searching and filtering

### Emojis
- ❌ **Don't use** emojis in logs
- Have color highlighting and patterns

## Correct Logging Examples

```python
# ✅ Good: brief, about current function
self.logger.info(f"[Tenant-{tenant_id}] Parsing scenarios...")

# ✅ Good: process start and end
self.logger.info(f"[Tenant-{tenant_id}] Updating data from GitHub...")
# ... process ...
self.logger.info(f"[Tenant-{tenant_id}] GitHub data updated")

# ✅ Good: with count specified
self.logger.info(f"[Tenant-{tenant_id}] Synchronizing {groups_count} scenario groups...")

# ✅ Good: error with description
self.logger.error(f"[Tenant-{tenant_id}] Scenario synchronization error: {error}")

# ❌ Bad: too many internal process details
self.logger.info(f"[Tenant-{tenant_id}] Starting scenario parsing, checking files, reading configuration...")

# ❌ Bad: emojis
self.logger.info(f"✅ [Tenant-{tenant_id}] Scenarios successfully synchronized")
```

## Final Rules

1. **Conciseness:** Only essentials, no excessive details
2. **Self-sufficiency:** Each function logs its own work
3. **Hierarchy:** Tenant first, then Bot/other entities
4. **No emojis:** Use colors and patterns
5. **DEBUG:** Only by request, not in prod
