---
title: Plugin Configuration Guide
description: Structure and configuration of plugins in Coreness. config.yaml, interfaces, dependencies and configuration examples.
keywords: coreness plugins, config.yaml, plugin interfaces, dependency injection
---

# YAML Config Templates for Plugins (Services and Utilities)

This document serves as a reference for formatting configs for all project plugin types (services and utilities).
Sections marked as (optional) can be omitted if not needed for specific case.
Follow template structure for your plugin type.

## 1. Universal Template for All Utilities

**Applies to: Custom Layers, Foundation, Core**

```yaml
name: "logger"                    # Unique utility name (required)
description: "Brief utility description"
singleton: false                  # (optional) true if plugin should be singleton

dependencies:                     # (optional, if utility uses other utilities)
  - "logger"                      # Format: "utility_name" (unique utility name)
  - "database"                    # System automatically finds utility by name
  - "cache"                       # List of required utilities

optional_dependencies:            # (optional) Dependencies that may be absent
  - "tg_bot"                      # Format: "utility_name" (unique utility name)
  - "analytics"                   # System passes None if utility not found

settings:                         # (optional, if has settings)
  param_name:
    type: string
    default: "..."
    description: "..."

methods:                          # REQUIRED for utilities - public methods
  method_name:
    description: "..."
    input:
      param1:
        type: ...
        description: "..."
    output:
      type: ...
      description: "..."

actions:                          # (optional) Actions for scenario calls
  action_name:
    description: "Action description"
    access_rules: ["rule_name"]   # (optional) Access rules for validation
    public: false                 # (optional) Scenario availability: true=public, false=system (default false)
    input:
      data:                       # REQUIRED - data block with parameters
        type: object
        properties:
          param1:
            type: ...
            description: "..."
          param2:
            type: ...
            optional: true
            description: "Optional parameter"
    output:
      result:                     # REQUIRED - execution result
        type: string
        description: "Result: success, error, timeout, not_found"
      error:                      # Optional - error structure
        type: object
        optional: true
        description: "Error structure on failure"
        properties:
          code:
            type: string
            description: "Error code"
          message:
            type: string
            description: "Error message"
          details:
            type: array
            optional: true
            description: "Error details (e.g., field validation errors)"
      response_data:              # Optional - response data (analogous to data in API)
        type: object
        properties:
          field1:
            type: integer
            description: "Field 1 description"
          field2:
            type: string
            replaceable: true  # (optional) Marker for fields that can be replaced via response_key
            description: "Field 2 description"
features:                         # (optional, if any)
  - "..."
```

---

## 2. Services — Service API Methods

```yaml
name: "user_service"              # Unique service name (required)
description: "Brief service description"
singleton: false                  # (optional) true if plugin should be singleton

dependencies:                     # (optional, if service uses utilities)
  - "logger"                      # Format: "utility_name" (unique utility name)
  - "database_service"            # System automatically finds utility by name
  - "hash_manager"                # Utilities automatically passed to constructor
  
optional_dependencies:            # (optional) Dependencies that may be absent
  - "cache_service"               # Format: "utility_name" (unique utility name)
  - "analytics_service"           # System passes None if utility not found
  
settings:                         # (optional, if has settings)
  # Standard service settings
  processing_interval:            # (recommended for services with processing loop)
    type: float
    default: 0.10
    description: "Interval (in seconds) between processing iterations"
  batch_size:                     # (recommended for services with batch processing)
    type: integer
    default: 50
    description: "Maximum elements processed per iteration"
  
  # Other service-specific settings
  param_name:
    type: string
    default: "..."
    description: "..."
    
actions:                          # REQUIRED for services - scenario actions
  create_profile:
    description: "Create user profile"
    access_rules: ["system_access"]  # Access rules for validation
    public: true                      # (optional) true — available in general scenarios; default false (system)
    input:
      data:                       # REQUIRED - data block with parameters
        type: object
        properties:
          user_id:
            type: integer
            description: "User ID"
          source:
            type: string
            optional: true
            description: "Registration source (optional)"
    output:
      result:                     # REQUIRED - execution result
        type: string
        description: "Result: success, error, timeout, not_found"
      error:                      # Optional - error structure
        type: object
        optional: true
        description: "Error structure on failure"
        properties:
          code:
            type: string
            description: "Error code"
          message:
            type: string
            description: "Error message"
          details:
            type: array
            optional: true
            description: "Error details (e.g., field validation errors)"
      response_data:              # Optional - response data (analogous to data in API)
        type: object
        properties:
          user_id:
            type: integer
            description: "User ID"
          profile_created:
            type: boolean
            description: "Profile created successfully"
  
  get_profile:
    description: "Get user profile"
    access_rules: ["data_integrity"]  # Access rules for validation
    public: false                     # Explicitly mark system action (optional)
    input:
      data:                       # REQUIRED - data block with parameters
        type: object
        properties:
          user_id:
            type: integer
            description: "User ID"
    output:
      result:                     # REQUIRED - execution result
        type: string
        description: "Result: success, error, timeout, not_found"
      error:                      # Optional - error structure
        type: object
        optional: true
        description: "Error structure on failure"
        properties:
          code:
            type: string
            description: "Error code"
          message:
            type: string
            description: "Error message"
          details:
            type: array
            optional: true
            description: "Error details"
      response_data:              # Optional - response data (analogous to data in API)
        type: object
        properties:
          user_id:
            type: integer
            description: "User ID"
          username:
            type: string
            description: "Username"
          first_name:
            type: string
            description: "First name"
          last_name:
            type: string
            description: "Last name"

# ℹ️ actions section REQUIRED for services - describes scenario actions
# ℹ️ run() method OPTIONAL - for background service launch
# ℹ️ Services called via scenarios, passing parameters to actions
# ℹ️ In input MUST use data block with field descriptions inside
# ℹ️ In output result always required, error and response_data optional
# ℹ️ error - structured object with code, message, details fields (not string)
# ℹ️ response_data - analogous to data in REST API, contains returned data
# ℹ️ Actions accept flat data dictionary for universality
# ℹ️ Optional dependencies allow services to work with additional utilities
# ℹ️ access_rules defines access rules for action validation
# ℹ️ public: boolean — marks scenario availability (default false = system)

features:                         # (optional, if any)
  - "..."
```

---

## Access Validation System (access_rules)

### Purpose
`access_rules` field defines access rules for action validation. System automatically checks access rights before executing action.

### Current Settings
**All access rules and user groups are in `action_hub/config.yaml`** — central place for access validation system management.

### Available Access Rules:
- **`system_access`** — access only for system operations (bot, tenant management)
- **`data_integrity`** — access for data operations (message sending, validation)
- **`no_access`** — actions without access restrictions (event processing)

### Usage Examples:
```yaml
actions:
  start_bot:
    description: "Start bot"
    access_rules: ["system_access"]  # System operations only
    
  send_message:
    description: "Send message"
    access_rules: ["data_integrity"]  # Data operations
    
  process_event:
    description: "Process event"
    access_rules: ["no_access"]  # No restrictions
```

## Action Response Format (output)

### Response Structure

All actions return uniform response format:

```yaml
output:
  result:                     # REQUIRED - execution status
    type: string
    description: "Result: success, error, timeout, not_found"
  error:                      # Optional - error structure
    type: object
    optional: true
    properties:
      code:                   # Error code
        type: string
      message:                # Error message
        type: string
      details:                # Error details (optional)
        type: array
        optional: true
  response_data:              # Optional - response data (analogous to data in REST API)
    type: object
    properties: ...
```

### Response Examples

#### Successful Response:
```json
{
  "result": "success",
  "response_data": {
    "user_id": 123,
    "username": "john_doe"
  }
}
```

#### Error Response:
```json
{
  "result": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input data validation error",
    "details": [
      {
        "field": "email",
        "message": "Field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

#### Special Status (not error):
```json
{
  "result": "not_found"
}
```

### Field Purpose

- **`result`** — action execution status. Can be: `success`, `error`, `timeout`, `not_found`, etc. Used in transitions to determine next actions.
- **`error`** — structured error information. Contains error code, message, and details. Format complies with REST API standards for easy future transition.
- **`response_data`** — response data (only when `result=success`). Analogous to `data` field in REST API. Can contain any data structure.

### Error Codes (Recommended)

For `error.code` field, recommended standard codes:

- **`VALIDATION_ERROR`** — input data validation error (incorrect parameters, missing required fields)
- **`NOT_FOUND`** — resource not found (user, bot, tenant, etc.)
- **`ALREADY_EXISTS`** — resource already exists (attempt to create duplicate)
- **`PERMISSION_DENIED`** — insufficient rights for operation
- **`INTERNAL_ERROR`** — internal service error (unexpected exceptions, DB errors)
- **`TIMEOUT`** — operation timeout exceeded
- **`INVALID_STATE`** — invalid state for operation (e.g., attempt to cancel already paid invoice)
- **`API_ERROR`** — external API error (GitHub, Telegram, etc.)
- **`SYNC_ERROR`** — data synchronization error
- **`PARSE_ERROR`** — data parsing error (configurations, scenarios, etc.)

## replaceable Marker

### Purpose
Marker `replaceable: true` indicates that field in `response_data` can be replaced via `response_key` parameter in action input. If `response_key` specified, main value returned under this key instead of standard one.

### Usage
```yaml
output:
  response_data:
    properties:
      main_value:
        type: string
        replaceable: true  # Field can be replaced via response_key
        description: "Main value"
```

### Example
```yaml
# In config.yaml
output:
  response_data:
    properties:
      user_storage_values:
        type: any
        replaceable: true
        description: "User data"

# In scenario
- action: "get_user_storage"
  params:
    key: "active_tenant_id"
    response_key: "active_tenant_id"  # Value will be in _cache.active_tenant_id
```

## General Recommendations

- **Don't add empty or unused sections**
- **Document only what's actually used by other layers or users**
- **Follow template structure for your service type**
- **When in doubt — refer to this document or ask architect**
- **All services use single template for unification**
- **Follow dependency hierarchy described in project architecture**
- **Use `plugin_management` for plugin enable/disable management**
- **Database operations through `database_service` utility**
- **Always specify `access_rules` for service actions**
- **Use `replaceable` marker for fields that can be replaced via `response_key`**

## Key Differences Between Utilities and Services

### 🔧 Utilities
- **`methods` section**: **REQUIRED** - describes public methods
- **`actions` section**: **OPTIONAL** - describes actions for scenario calls
- **Purpose**: Supporting components for functionality extension
- **Dependencies**: Only on other utilities

### 🚀 Services
- **`actions` section**: **REQUIRED** - describes scenario actions
- **`run()` method**: **OPTIONAL** - for background service launch
- **Purpose**: Core application business logic (orchestrators, event handlers)
- **Dependencies**: On utilities (not on other services)

## dependencies Section

### Purpose
`dependencies` section allows automatically determining and passing required utilities to service or utility constructor. This provides:

- **Automatic dependency injection** — utilities passed automatically
- **Dependency hierarchy check** — system verifies dependency correctness
- **Registration simplification** — no need to manually specify dependencies when creating service
- **Architecture flexibility** — utilities can be easily moved between levels

### Dependency Declaration Format
```yaml
dependencies:
  - "logger"             # Unique utility name
  - "database"           # System automatically finds utility by name
  - "cache"              # Regardless of which level it's in
optional_dependencies:
  - "tg_bot"             # Optional dependency
  - "analytics"          # System passes None if utility not found
```

### Dependency Rules
1. **Utilities** can only depend on other **utilities**
2. **Services** can depend on **utilities**
3. **Services** CANNOT depend on other **services**
4. **Circular dependencies** forbidden
5. **Optional dependencies** NOT passed to constructor if utility not found
