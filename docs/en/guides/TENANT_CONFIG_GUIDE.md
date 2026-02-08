---
title: Tenant Configuration Guide
description: Configuring tenants and Telegram bots in Coreness. Bot configuration, scenario organization, external repository synchronization.
keywords: telegram bot setup, tenant configuration, multitenancy, github synchronization
---

# Tenant Configuration Guide

ℹ️ **Purpose:** Setting up tenants (clients) and their Telegram bots for working with the system.

## 📁 Configuration Structure

All tenants are located in one folder `config/tenant/`. 

### Tenant Folder Structure

```
config/tenant/
├── tenant_101/                 # Public tenant (ID = 101)
│   ├── bots/                   # Bot configs (e.g. Telegram, WhatsApp)
│   │   └── telegram.yaml      # Telegram bot configuration
│   ├── config.yaml             # Tenant configuration (optional)
│   ├── storage/                # Tenant attributes storage (optional)
│   │   └── ...                 # See STORAGE_CONFIG_GUIDE.md
│   └── scenarios/              # Scenarios (optional)
│       └── ...
├── tenant_137/                 # Public tenant (ID = 137)
│   └── ...
└── ...
```

### Tenant Types

- **System tenants** (ID < 100):
  - Limited in changes
  - Managed by the system

- **Public tenants** (ID ≥ 100):
  - Synchronized with external `Repository-Tenant` repository
  - Fully managed through configuration
  - Used for client bots and public services

⚠️ **IMPORTANT:** 
- Folder name must strictly follow format `tenant_<ID>`, where `<ID>` is unique numeric tenant identifier
- Folder structure is identical for all tenants regardless of type

## 🔄 Tenant Synchronization

Public tenants (ID ≥ 100) are synchronized with external `Repository-Tenant` repository through GitHub.

- **Update:** Automatic synchronization with GitHub
- **Management:** Through system actions (`sync_all_tenants`, `sync_tenant`)
- **Purpose:** Client bots, public services
- **Manual synchronization:** Through system actions when needed

## 🤖 bots/telegram.yaml

**Purpose:** Telegram bot configuration for tenant. Stored in `bots/telegram.yaml` (folder `bots/` can contain configs for different bots).

### Example Configuration:

```yaml
# bots/telegram.yaml — Telegram bot configuration for tenant
bot_token: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
is_active: true

# Bot commands (optional)
commands:
  - command: "start"
    description: "Main menu"
    scope: "all_private_chats"
  - command: "help"
    description: "Help"
    scope: "all_private_chats"

# Commands for clearing (optional)
command_clear:
  - scope: "all_private_chats"        # Clear commands in private chats
  - scope: "all_group_chats"          # Clear commands in group chats
  - scope: "chat"                     # Clear commands in specific chat
    chat_id: 123456789
  - scope: "chat_member"              # Clear commands for specific user in chat
    chat_id: 123456789
    user_id: 987654321
```

### Parameters:

- **`bot_token`** — bot token from BotFather (optional)
- **`is_active`** — whether bot is active (true/false)

### 💡 Storing Bot Token:

Bot token can be set in two ways:

1. **Through configuration** (`bots/telegram.yaml`) — during configuration synchronization, token from file is saved to database
2. **Through master bot** — token can be set through master bot interface (bot must be created through configuration synchronization)

**Priority:** During configuration synchronization, token from `bots/telegram.yaml` has priority and updates token in database.

**💡 Life hack:** You can set token once through configuration (`bots/telegram.yaml`), then remove it from file — token will remain in database and continue to be used. This allows not storing token in repository after initial setup.
- **`commands`** — list of bot commands (optional):
  - **`command`** — command name (without /)
  - **`description`** — command description
  - **`scope`** — command scope:
    - `"default"` — default (private chats + groups)
    - `"all_private_chats"` — all private chats
    - `"all_group_chats"` — all group chats
    - `"chat"` — specific chat (requires `chat_id`)
    - `"chat_member"` — specific user in chat (requires `chat_id` and `user_id`)
- **`command_clear`** — list of scopes for clearing commands (optional):
  - **`scope`** — scope for clearing commands (same options as above)
  - **`chat_id`** — chat ID (for scope: `chat`, `chat_member`)
  - **`user_id`** — user ID (for scope: `chat_member`)

### Important Features:

- **Bot activation:** Only bots with `is_active: true` will be started. Commands are automatically registered in Telegram on startup. Inactive bots are ignored by system
- **Command scopes:** Described in parameters above (`default`, `all_private_chats`, `all_group_chats`, `chat`, `chat_member`)

## ⚙️ config.yaml

**Purpose:** Tenant configuration with attributes (API keys, settings and other parameters).

### Example Configuration:

```yaml
# Tenant configuration
ai_token: "sk-or-v1-..."  # AI API key for tenant (optional)
```

### Parameters:

- **`ai_token`** — AI API key for tenant (optional)
  - Used for actions requiring AI API key (e.g., `completion`, `embedding`, `save_embedding`)
  - If not specified, actions can use default key (if allowed in service settings)

### 💡 Storing Tenant Configuration:

Tenant configuration can be set in two ways:

1. **Through configuration** (`config.yaml`) — during configuration synchronization, attributes from file are saved to database
2. **Through master bot** — attributes can be updated through master bot interface (similar to bot token)

**Priority:** During configuration synchronization, attributes from `config.yaml` have priority and update values in database.

**💡 Life hack:** You can set token once through configuration (`config.yaml`), then remove it from file — token will remain in database and continue to be used. This allows not storing token in repository after initial setup.

### Usage in Scenarios:

All attributes from tenant configuration are automatically available in scenarios through special `_config` dictionary:

```yaml
step:
  - action: "completion"
    params:
      prompt: "Hello!"
      # ai_token automatically taken from _config.ai_token
```

**Access through placeholders:**
```yaml
params:
  text: "Token: {_config.ai_token|fallback:Not set}"
```

## 📂 scenarios/

**Purpose:** Organization of tenant scenarios. All YAML files from `scenarios/` folder (including subfolders) are automatically loaded. Subfolders can be used for logical file organization.

📖 **Detailed guide:** See [SCENARIO_CONFIG_GUIDE.md](SCENARIO_CONFIG_GUIDE.md)

## 💾 storage/

**Purpose:** Tenant attributes storage (key-value structure for flexible storage of settings, limits, features and other data). Allows flexible tenant configuration management without changing DB schema.

📖 **Detailed guide:** See [STORAGE_CONFIG_GUIDE.md](STORAGE_CONFIG_GUIDE.md)
