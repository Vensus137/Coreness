---
title: Master Bot — Tenant Management
description: Guide to Master Bot in Coreness. System bot for managing tenants, creating bots and synchronizing configurations.
keywords: master bot, tenant management, bot creation, coreness admin
---

# Master Bot — Tenant Management System

**Master Bot** is a system bot for managing platform tenants `Coreness`, working similar to [@BotFather](http://t.me/botfather) in **Telegram**.

## 🎯 Purpose

Master Bot provides a full-featured management system for:
- **Selecting and switching** between available tenants
- **Configuring** tenant settings (tokens, parameters)
- **Managing Storage** (Tenant Storage and User Storage)
- **Data synchronization** with GitHub repositories
- **Access control** based on user roles
- **Language selection** for the interface (Russian / English)

## 📂 Structure

```
master-bot/
├── bots/
│   └── telegram.yaml       # Bot configuration
│
├── scenarios/               # Bot scenarios
│   ├── main/               # Core functionality
│   │   ├── commands.yaml   # Commands (/start, /help, /me, /file, /language)
│   │   ├── access.yaml     # User access check
│   │   ├── settings.yaml   # User settings (language)
│   │   ├── errors.yaml     # Error handling
│   │   └── default.yaml    # Default scenarios (default_check, check_message)
│   │
│   ├── management/         # Tenant management
│   │   ├── tenant.yaml           # Tenant selection and management
│   │   ├── tenant_config.yaml    # Configuration setup (AI token, etc.)
│   │   ├── tenant_storage.yaml   # Tenant Storage management
│   │   └── user_storage.yaml     # User Storage management
│   │
│   └── scheduled/          # Automated tasks
│       └── cleanup_temp_storage.yaml  # Temporary data cleanup
│
└── storage/                # Data and localization
    ├── main.yaml           # Main settings (users, access)
    ├── i18n_default.yaml   # Translations: errors, access, language
    ├── i18n_command.yaml   # Translations: /start, /help
    ├── i18n_tenant.yaml    # Translations: tenant menu, config, tokens
    ├── i18n_user_storage.yaml    # Translations: User Storage
    └── i18n_tenant_storage.yaml  # Translations: Tenant Storage
```

## 🚀 Core Features

<img src="https://habrastorage.org/webt/qn/xx/nj/qnxxnjxicp83lppv7yfrh0dwjby.gif" alt="Master Bot" width="400" />

### 1. Language Selection

- **Command:** `/language`
- **Available to:** all users
- **Action:** choose interface language (Russian / English). The selected language is stored in User Storage and applied to all Master Bot scenarios (menus, messages, buttons).

Before operations, the `default_check` scenario runs: access check and loading of translations for the user's current language.

### 2. Tenant Management

#### Tenant Selection
- **For regular users:** only tenants where they are owners (`tenant_owner`) are available
- **For administrators:** all system tenants (system + public)
- **User Storage:** active tenant saved in `active_tenant_id` for quick access

#### Tenant Information
Tenant menu displays:
- **Bot status:** enabled/disabled
- **Working status:** working/not working
- **Update date:** last synchronization
- **Last error:** if occurred

### 3. Configuration Setup

#### Bot Token Setup
- **Token input:** format validation `number:string` (Telegram Bot API format)
- **Token removal:** enter `null` or `none`
- **Automatic check:** token verified on polling start

#### AI Token Setup
- **Token input:** for AI providers (OpenRouter, Azure OpenAI, etc.)
- **Token removal:** enter `null` or `none`
- **Validation:** token format check (letters, numbers, hyphens, underscores)

### 4. Storage Management

#### Tenant Storage
Full-featured tenant attribute storage management:
- **View groups:** list all Storage groups
- **View group:** output in YAML format
- **View key:** view specific key value
- **Edit:** add/change values
- **Delete:** remove keys or entire groups

**Input format:**
```
group                    # View group
group key               # View key value
group key value         # Change/add value
```

**Example:**
```
settings                  # View settings group
settings max_users        # View max_users value
settings max_users 100    # Set max_users = 100
```

#### User Storage
Similar management of user data storage (input: `user_id`, `user_id key`, `user_id key value`).

### 5. Data Synchronization

**Function:** `🔄 Sync` (in tenant menu)

Performs full tenant synchronization:
- **Pull from GitHub:** download latest changes from repository
- **Update scenarios:** synchronize all scenario YAML files
- **Update Storage:** synchronize attribute storage
- **Update configuration:** synchronize bot settings

### 6. Access Control

**Access levels:**
- **Administrator:** access to all tenants and all functions
- **Tenant owner:** access to own tenants and their management
- **Regular user:** only public information (`/me`)

**Access check:** before operations, the `default_check` scenario runs (access check and language/translation loading).

### 7. Automated Tasks

**Temporary Data Cleanup** (`cleanup_temp_storage`)
- **Schedule:** daily at 3:00 AM
- **Function:** remove temporary data from Storage (keys with `temp.*` prefix)

### 8. Commands

| Command      | Description |
|-------------|-------------|
| `/start`    | Start bot, main menu |
| `/help`     | Help on bot features |
| `/language` | Choose interface language (RU/EN) |
| `/me`       | Public info about yourself (ID, username, name, language) |
| `/file`     | Hidden command for developers: get attachment `file_id` and `type` |

## 🛡️ Security

- **Access validation:** rights check before each operation (via `default_check`)
- **Owner verification:** regular users see only their tenants
- **Token validation:** format check before saving
- **User states:** input timeouts (300 seconds)
- **Confirmations:** critical operations require confirmation
