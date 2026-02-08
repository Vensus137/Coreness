---
title: Attribute Storage Guide
description: Working with attribute storage in Coreness. Tenant Storage, User Storage, value types and usage in scenarios.
keywords: coreness storage, key-value storage, tenant storage, user storage, tenant settings
---

# Storage Configuration Guide (Data Storage)

> **📖 Complete guide** to creating and configuring data storage for flexible management of settings, limits, features, and user data.

## 🎯 Purpose

**Storage** — flexible key-value data storage system that allows:

- Store tenant settings (limits, parameters, configurations)
- Manage tenant features and capabilities
- Store user data and settings
- Flexibly add new attributes without DB schema changes
- Automatically synchronize data from configuration to DB

**Advantages:**
- ✅ Flexibility — can add new attributes without DB migrations
- ✅ Organization — data grouped by logical files (Tenant Storage) or by users (User Storage)
- ✅ Simplicity — simple data types (strings, numbers, bool, arrays, objects)
- ✅ Automatic type conversion on read
- ✅ Data isolation — user data isolated by tenants

## 🔀 Storage Types

System supports two storage types:

### Tenant Storage
- **Purpose:** Store tenant settings and configurations
- **Structure:** Grouping by `group_key` (settings, limits, features, etc.)
- **Data source:** YAML files in `storage/` folder of tenant configuration
- **Synchronization:** Automatic synchronization from configuration to DB
- **Key:** `(tenant_id, group_key, key)`

### User Storage
- **Purpose:** Store user data and settings
- **Structure:** Flat structure without groups (`{key: value}`)
- **Data source:** Set programmatically via scenario actions
- **Synchronization:** Not synchronized with configuration, managed only via actions
- **Key:** `(tenant_id, user_id, key)`

**Differences:**

| Characteristic | Tenant Storage | User Storage |
|----------------|----------------|--------------|
| Grouping | By `group_key` | Without groups |
| Data source | YAML files | Scenario actions |
| Synchronization | Automatic from configuration | Manual management |
| Usage scope | Tenant settings | User data |
| Structure | `{group_key: {key: value}}` | `{key: value}` |

## 🏢 Tenant Storage

### Storage Structure

#### Location

Tenant Storage located in `storage/` folder inside tenant configuration:

```
tenant_101/
├── bots/
│   └── telegram.yaml
├── storage/               # Storage folder
│   ├── settings.yaml     # Settings group
│   ├── limits.yaml       # Limits group
│   └── features.yaml      # Features group
└── scenarios/
    └── ...
```

#### File Structure

Each file in `storage/` folder contains attribute groups. File name doesn't affect grouping — it's just way to logically organize configuration.

**Example:**
```yaml
# storage/config.yaml - file name doesn't matter
settings:
  max_users: 100
  max_storage: 500
  default_language: "en"

limits:
  daily_requests: 1000
  max_file_size: 10485760
```

All files from `storage/` folder combined during configuration synchronization.

### Database Synchronization

#### Synchronization Mechanism

During Tenant Storage configuration synchronization system performs following actions:

1. **Get groups from DB** — system gets list of all existing groups in database
2. **Determine groups for synchronization** — compares groups from configuration with groups in DB
3. **Delete synchronized groups** — deletes only groups present in configuration
4. **Load data from config** — all groups from configuration loaded to database

#### Important Features

- **Groups from configuration** — fully synchronized (old data deleted, new loaded)
- **Groups absent in config** — remain untouched in database (not deleted automatically)
- **New groups** — automatically created during synchronization
- **Full config match** — synchronized groups fully match configuration

**Example:**

If DB has groups: `settings`, `limits`, `features`, `old_group`

And config has only: `settings`, `limits`, `features`

Then during synchronization:
- ✅ `settings`, `limits`, `features` — will be deleted and reloaded from config
- ✅ `old_group` — will remain untouched in DB (won't be deleted)

**To delete group from DB** use `delete_storage` action in scenario or manually delete all group records.

### File Organization

#### Organization Principles

1. **Files for logical grouping** — can create any number of files for convenient configuration organization
2. **File combining** — all files from `storage/` folder combined during synchronization
3. **Attribute groups** — inside file use `{group_key: {key: value}}` structure to group related attributes
4. **Key uniqueness** — keys must be unique within group (`group_key`)

#### Structure Example

```
storage/
├── config.yaml          # Arbitrary file name
│   settings:
│     max_users: 100
│     default_language: "en"
│   limits:
│     daily_requests: 1000
│     max_file_size: 10485760
│
└── additional.yaml     # Another file for additional settings
    features:
      enable_premium: true
      enable_api: false
```

### Usage Example

**File: `storage/config.yaml`** (file name can be any)

```yaml
# Basic settings
settings:
  max_users: 100                          # Integer
  max_storage: 500                        # Integer
  default_language: "en"                  # String
  allowed_languages: ["ru", "en", "de"]   # String array
  enable_notifications: true              # Boolean
  maintenance_mode: false                 # Boolean

# Limits and restrictions
limits:
  daily_requests: 1000                     # Integer
  max_file_size: 10485760                # Integer (10 MB in bytes)
  rate_limit_per_minute: 30              # Integer
  discount_percentage: 10.5               # Float
  price_tiers: [9.99, 19.99, 29.99]      # Float array

# Features and capabilities
features:
  enable_premium: true                    # Boolean
  enable_api: false                       # Boolean
  enable_webhooks: false                 # Boolean
  supported_regions: ["eu", "us", "asia"] # String array

# Tariffs and prices
pricing:
  base_price: 9.99                        # Float
  premium_price: 29.99                    # Float
  trial_days: 14                          # Integer
```

## 👤 User Storage

### Purpose

**User Storage** — user data storage that allows:

- Store user settings and preferences
- Save user state between sessions
- Manage personal user data
- Isolate user data by tenants

### Structure

User Storage has flat structure without groups:

```
{key: value}
```

**Example:**
```yaml
language: "en"
theme: "dark"
messages_sent: 150
favorite_colors: ["red", "blue", "green"]
user_preferences:
  language: "en"
  theme: "dark"
  notifications: true
```

### Features

- **Tenant isolation:** User data tied to `tenant_id` and `user_id`
- **Flat structure:** No grouping by `group_key`, only `key: value`
- **Programmatic management:** Data set and changed only via scenario actions
- **Automatic context:** `tenant_id` and `user_id` automatically available from event context

### Usage Example

**Setting values via scenario:**

```yaml
set_user_preferences:
  description: "Set user preferences"
  
  trigger:
    - event_type: "callback"
      callback_data: "set_preferences"
  
  step:
    - action: "set_user_storage"
      params:
        key: "language"
        value: "en"
    
    - action: "set_user_storage"
      params:
        key: "theme"
        value: "dark"
    
    - action: "set_user_storage"
      params:
        key: "user_preferences"
        value:
          language: "en"
          theme: "dark"
          notifications: true
    
    - action: "send_message"
      params:
        text: "✅ Settings saved!"
```

**Getting values:**

```yaml
show_user_preferences:
  description: "Show user preferences"
  
  trigger:
    - event_type: "callback"
      callback_data: "show_preferences"
  
  step:
    # Get all values in one request
    - action: "get_user_storage"
    
    - action: "send_message"
      params:
        text: |
          👤 <b>Your settings</b>
          
          Language: <code>{_cache.user_storage_values.language|fallback:not set}</code>
          Theme: <code>{_cache.user_storage_values.theme|fallback:not set}</code>
```

**Note:** When requesting specific key (`key` specified) returns direct value available via `{_cache.user_storage_values}`. When requesting all values (without `key`) returns full structure `{key: value}` available via `{_cache.user_storage_values.key}`

## 🔢 Value Types

### Supported Types

In both Storage types can use following data types:

- ✅ **Strings** — text values
- ✅ **Integers** — integer numbers
- ✅ **Floats** — floating point numbers
- ✅ **Booleans** — true/false
- ✅ **Arrays** — value lists (support simple types and complex structures)
- ✅ **JSON objects (dictionaries)** — nested data structures
- ✅ **Nested structures** — dictionary arrays, dictionaries with arrays, nested dictionaries

### How to Specify Values

In YAML files (for Tenant Storage) and when setting values (for User Storage) can write values in their natural form — system automatically determines type:

```yaml
settings:
  max_users: 100                    # Integer
  price: 9.99                       # Float
  enable_feature: true              # Boolean
  default_language: "en"            # String
  allowed_languages: ["ru", "en", "de"]  # String array
  price_tiers: [9.99, 19.99, 29.99]      # Float array
  
  # JSON objects (dictionaries)
  admin_config:
    id: 1133574222
    name: "Admin"
    role: "admin"
    permissions: ["read", "write"]
  
  # Dictionary arrays (structure arrays)
  users:
    - id: 1
      name: "User 1"
      role: "user"
    - id: 2
      name: "User 2"
      role: "admin"
  
  # Nested structures
  nested_data:
    level1:
      level2:
        value: "deep nested"
        items: [1, 2, 3]
```

**Boolean values:**
- `true`, `false` (boolean values in YAML)
- `"true"`, `"false"` (strings - will be converted to boolean values)

**Arrays:**
- Can contain simple types: strings, numbers, float, bool
- Can contain complex structures: dictionaries, nested arrays
- Array elements automatically converted to appropriate types on read
- Access to elements via placeholders: `{_cache.storage_values.settings.allowed_languages[0]}`

**Dictionaries (JSON objects):**
- Can contain any supported value types
- Support nesting up to 10 levels deep
- Access to fields via dot notation: `{_cache.storage_values.settings.admin_config.name}`
- Combination with arrays: `{_cache.storage_values.settings.users[0].name}`

## 🎬 Usage in Scenarios

### Available Actions

#### Tenant Storage

In scenarios following actions available for working with Tenant Storage:

- `get_storage` — get tenant storage values (one value, group or all values). Supports parameters `group_key`, `key`, `group_key_pattern`, `key_pattern` for flexible search
- `get_storage_groups` — get list of unique group keys for tenant
- `set_storage` — set values in tenant storage. Supports mixed approach: full structure via `values` or partial via `group_key`/`key`/`value`
- `delete_storage` — delete values or groups from tenant storage. Supports deleting specific value, group or by patterns

#### User Storage

In scenarios following actions available for working with User Storage:

- `get_user_storage` — get user storage values (one value or all values). Supports parameters `key` and `key_pattern` for flexible search
- `set_user_storage` — set values in user storage. Supports mixed approach: full structure via `values` or partial via `key`/`value`
- `delete_user_storage` — delete values from user storage. Supports deleting specific value, all values or by pattern

**Important:** 
- Parameters `tenant_id` and `user_id` automatically available from event context and don't require explicit specification in scenarios
- Data from action `response_data` automatically saved to `_cache` (flat caching by default)
- Access to data via placeholders: `{_cache.storage_values}` for Tenant Storage and `{_cache.user_storage_values}` for User Storage
- For Tenant Storage when requesting only group (`group_key` specified, `key` not specified): returns group structure `{key: value}` (without group_key nesting), available via `{_cache.storage_values.{key}}`
- For Tenant Storage when requesting specific key (`group_key` and `key` specified): returns direct value available via `{_cache.storage_values}`
- For Tenant Storage when requesting all values (nothing specified): returns full structure `{group_key: {key: value}}` available via `{_cache.storage_values.{group_key}.{key}}`
- For User Storage when requesting all values: `{_cache.user_storage_values.{key}}`
- For User Storage when requesting specific key: `{_cache.user_storage_values}` (direct value)

### Example 1: Getting and Displaying Value

**Simple example — getting one value:**

```yaml
show_settings:
  description: "Show tenant settings"
  
  trigger:
    - event_type: "message"
      event_text: "/settings"
  
  step:
    # Get value from storage
    - action: "get_storage"
      params:
        group_key: "settings"
        key: "max_users"
    
    # Use obtained value in message
    - action: "send_message"
      params:
        text: |
          📊 <b>Settings</b>
          
          Max users: <code>{_cache.storage_values}</code>
```

**Value access:**
- When requesting specific key (`group_key` and `key` specified) returns direct value (primitive or object as is) available via `{_cache.storage_values}`
- In example above: `{_cache.storage_values}` returns value `100` (or other `max_users` value)
- When requesting only group (`group_key` specified, `key` not specified) returns group structure `{key: value}` available via `{_cache.storage_values.{key}}`

### Example 2: Getting Group Values

**Getting all group values in one request:**

```yaml
show_all_settings:
  description: "Show all settings"
  
  trigger:
    - event_type: "callback"
      callback_data: "show_settings"
  
  step:
    # Get entire settings group in one request
    - action: "get_storage"
      params:
        group_key: "settings"
    
    # Use all group values
    - action: "send_message"
      params:
        text: |
          ⚙️ <b>All settings</b>
          
          Max users: <code>{_cache.storage_values.max_users}</code>
          Max storage: <code>{_cache.storage_values.max_storage}</code>
          Default language: <code>{_cache.storage_values.default_language}</code>
          
          Notifications: {_cache.storage_values.enable_notifications|true|value:✅|fallback:❌}
```

**Advantages:**
- One request instead of multiple separate requests
- All group values loaded at once
- More efficient for displaying group of related settings
- When requesting only `group_key` returns group structure `{key: value}` (without group_key nesting) available via `{_cache.storage_values.{key}}`

### Example 3: Working with User Storage

**Getting and setting user data:**

```yaml
# Setting user preferences
set_user_settings:
  description: "Set user preferences"
  
  trigger:
    - event_type: "callback"
      callback_data: "set_settings"
  
  step:
    - action: "set_user_storage"
      params:
        key: "language"
        value: "en"
    
    - action: "set_user_storage"
      params:
        key: "theme"
        value: "dark"
    
    - action: "set_user_storage"
      params:
        key: "messages_sent"
        value: 0
    
    - action: "send_message"
      params:
        text: "✅ Settings saved!"

# Getting all user data
show_user_data:
  description: "Show all user data"
  
  trigger:
    - event_type: "callback"
      callback_data: "show_data"
  
  step:
    - action: "get_user_storage"
    
    - action: "send_message"
      params:
        text: |
          👤 <b>Your data</b>
          
          Language: <code>{_cache.user_storage_values.language|fallback:not set}</code>
          Theme: <code>{_cache.user_storage_values.theme|fallback:not set}</code>
          Messages sent: <code>{_cache.user_storage_values.messages_sent|fallback:0}</code>

# Deleting user data
delete_user_data:
  description: "Delete user data"
  
  trigger:
    - event_type: "callback"
      callback_data: "delete_data"
  
  step:
    - action: "delete_user_storage"
      params:
        key: "language"
    
    - action: "send_message"
      params:
        text: "🗑️ Data deleted!"
```

**User Storage features:**
- `tenant_id` and `user_id` automatically available from event context
- Data isolated by tenants and users
- No grouping — flat structure `{key: value}`
- Data set only via scenario actions

---

### Example 4: YAML Formatting

**Displaying data in readable YAML format:**

```yaml
show_formatted_storage:
  description: "Show storage in YAML format"
  
  trigger:
    - event_type: "callback"
      callback_data: "show_formatted"
  
  step:
    # Getting group with formatting
    - action: "get_storage"
      params:
        group_key: "settings"
        format: true
    
    - action: "send_message"
      params:
        text: |
          ⚙️ <b>Settings (YAML format)</b>
          
          <pre>{_cache.formatted_text}</pre>
```

**`format` parameter:**
- Available for all data getting actions (`get_storage`, `get_user_storage`)
- When `format: true` field `formatted_text` added to `response_data` with data in YAML format
- Access to formatted text via `{_cache.formatted_text}`
- Convenient for displaying complex data structures to users
