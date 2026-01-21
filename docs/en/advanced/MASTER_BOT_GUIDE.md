# Master Bot — Tenant Management System

**Master Bot** is a system bot for managing platform tenants `Coreness`, working similar to [@BotFather](http://t.me/botfather) in **Telegram**.

## 🎯 Purpose

Master Bot provides a full-featured management system for:
- **Selecting and switching** between available tenants
- **Configuring** tenant settings (tokens, parameters)
- **Managing Storage** (Tenant Storage and User Storage)
- **Data synchronization** with GitHub repositories
- **Access control** based on user roles

## 📂 Structure

```
master-bot/
├── tg_bot.yaml              # Bot configuration
│
├── scenarios/               # Bot scenarios
│   ├── main/               # Core functionality
│   │   ├── commands.yaml   # Commands (/start, /help, /me, /file)
│   │   ├── access.yaml     # User access check
│   │   ├── errors.yaml     # Error handling
│   │   └── default.yaml    # Default responses
│   │
│   ├── management/         # Tenant management
│   │   ├── tenant.yaml           # Tenant selection and management
│   │   ├── tenant_config.yaml    # Configuration setup (AI token, etc.)
│   │   ├── tenant_storage.yaml   # Tenant Storage management
│   │   └── user_storage.yaml     # User Storage management
│   │
│   ├── other/              # Additional functions
│   │   └── mailing.yaml    # Message broadcasts
│   │
│   └── scheduled/          # Automated tasks
│       └── cleanup_temp_storage.yaml  # Temporary data cleanup
│
└── storage/                # Storage configurations
    └── main.yaml           # Main settings
```

## 🚀 Core Features

### 1. Tenant Management

#### Tenant Selection
- **For regular users:** only tenants where they are owners (`tenant_owner`) are available
- **For administrators:** all system tenants available (system + public)
- **User Storage:** active tenant saved in `active_tenant_id` for quick access

#### Tenant Information
Tenant menu displays:
- **Bot status:** enabled/disabled
- **Working status:** working/not working
- **Update date:** last synchronization
- **Last error:** if occurred

### 2. Configuration Setup

#### Bot Token Setup
- **Token input:** format validation `number:string` (Telegram Bot API format)
- **Token removal:** enter `null` or `none`
- **Automatic check:** token verified on polling start

#### AI Token Setup
- **Token input:** for AI providers (OpenRouter, Azure OpenAI, etc.)
- **Token removal:** enter `null` or `none`
- **Validation:** token format check (letters, numbers, hyphens, underscores)

### 3. Storage Management

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
Similar management of user data storage with same capabilities.

### 4. Data Synchronization

**Function:** `🔄 Data Synchronization`

Performs full tenant synchronization:
- **Pull from GitHub:** download latest changes from repository
- **Update scenarios:** synchronize all scenario YAML files
- **Update Storage:** synchronize attribute storage
- **Update configuration:** synchronize bot settings

### 5. Access Control

**Access Levels:**
- **Administrator:** access to all tenants and all functions
- **Tenant owner:** access to own tenants and their management
- **Regular user:** only public information (`/me`)

**Access check:** `access_check` scenario runs before each operation

### 6. Automated Tasks

**Temporary Data Cleanup** (`cleanup_temp_storage`)
- **Schedule:** daily at 3:00 AM
- **Function:** remove temporary data from Storage (keys with `temp.*` prefix)

### 7. Additional Functions

#### `/me` Command
Public command to view information about yourself:
- User ID
- Username
- First and last name
- Interface language

#### `/file` Command
Hidden command for developers:
- Get attachment `file_id`
- Get attachment `type`
- For subsequent file forwarding

#### Broadcasts (for administrators)
`/mail` command for mass message distribution to users.

## 🛡️ Security

- **Access validation:** rights check before each operation
- **Owner verification:** regular users see only their tenants
- **Token validation:** format check before saving
- **User states:** input timeouts (300 seconds)
- **Confirmations:** critical operations require confirmation
