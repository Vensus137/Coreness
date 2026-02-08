---
title: System Settings Configuration
description: Configuring global Coreness parameters via settings.yaml. Database, logging, Redis and other system settings.
keywords: system settings, settings.yaml, coreness configuration, database settings
---

# Platform Configuration Settings

ℹ️ This section — examples and explanations for main system configuration files:
- **settings.yaml** — global settings for all services, centralized parameter overrides (e.g., processing_interval, batch_size, etc.). Recommended to change only when necessary as it affects all services.
- **Plugin Management** — centralized system for enabling/disabling plugins via `plugin_management` in `settings.yaml`

## 🔌 Plugin Management

**Purpose:** Centralized system for enabling/disabling plugins (utilities and services) via core configuration.

### Configuration Example:

```yaml
# config/settings.yaml (global settings)
plugin_management:
  # Service management (application launch foundation)
  services:
    default_enabled: false    # Services disabled by default
    disabled_services: []     # Disabled services list
    enabled_services: []      # Enabled services list
  
  # Utility management (fine-tuning supporting components)
  utilities:
    default_enabled: true     # Utilities enabled by default
    disabled_utilities: []    # Disabled utilities list
    enabled_utilities: []     # Forced enabled utilities list
```

### Settings Priority:
1. **Global settings** (`config/settings.yaml`) - single settings source
2. **Default value** depends on plugin type:
   - **Services:** `false` (disabled by default)
   - **Utilities:** `true` (enabled by default)

⚠️ **IMPORTANT:** If `plugin_management` section completely absent - **services disabled, utilities enabled**!

### Usage Examples:

#### Disabling Heavy Services in Tests:
```yaml
# config/settings.yaml
plugin_management:
  services:
    disabled_services:
      - "gigachat_service"
      - "salute_speech"
      - "promo_manager"
```

#### Minimal Production Configuration:
```yaml
# config/settings.yaml
plugin_management:
  services:
    default_enabled: true  # Enabled by default
    disabled_services:
      - "gigachat_service"  # Disable only heavy services
      - "salute_speech"
```

#### Strict Configuration (all disabled by default):
```yaml
# config/settings.yaml
plugin_management:
  services:
    default_enabled: false  # Disabled by default
    enabled_services:
      - "logger"
      - "database_service"
      - "tg_event_bot"
      - "hub_service"
```

#### Development with Debugging:
```yaml
# config/settings.yaml
plugin_management:
  services:
    default_enabled: true  # Enabled by default
    disabled_services:
      - "gigachat_service"  # Disable heavy AI services
```

### 💡 Centralized Management Benefits:

- **Compactness** - all enable/disable settings in one place
- **Centralization** - no need to search settings across files
- **Simplicity** - easy to enable/disable plugin groups
- **Performance** - disabled plugins don't consume resources

### ⚠️ Important Features:

- **Disabled plugins** not initialized and don't consume resources
- **Dependencies** - if plugin disabled, all dependent plugins won't start
- **Circular dependencies** - system automatically detects and excludes problematic plugins
- **Default value** depends on type:
  - **Services:** `false` (must explicitly enable)
  - **Utilities:** `true` (enabled by default)
- **Security** - system won't accidentally start extra services without explicit indication

### 🔍 Logic Explanation:

#### **Case 1: `plugin_management` Section Present**
```yaml
plugin_management:
  services:
    default_enabled: true   # All services enabled by default
    disabled_services: []    # Exceptions (disabled)
    enabled_services: []     # Explicitly enabled (if default_enabled: false)
  utilities:
    default_enabled: true   # All utilities enabled by default
    disabled_utilities: []   # Exceptions (disabled)
    enabled_utilities: []    # Explicitly enabled (if default_enabled: false)
```
- **Result:** All plugins enabled except those in disabled lists

#### **Case 2: `plugin_management` Section Absent**
```yaml
# No plugin_management section at all
```
- **Result:** Services disabled, utilities enabled (system won't start without services)

#### **Case 3: Partial Configuration**
```yaml
plugin_management:
  services:
    default_enabled: false  # All disabled by default
    enabled_services:       # Explicitly enable only needed
      - "logger"
      - "database_service"
```
- **Result:** Only services from `enabled_services` enabled, utilities enabled by default

---

## ⚙️ settings.yaml

**Purpose:** Global settings for all services, centralized parameter overrides and service launch management.

### Configuration Example:

```yaml
# Plugin management
plugin_management:
  # Service management (application launch foundation)
  services:
    default_enabled: false    # Services disabled by default
    disabled_services:        # Disabled services list
      - "gigachat_service"
      - "salute_speech"
    enabled_services:         # Enabled services list
      - "hub_service"
      - "tg_event_bot"
  
  # Utility management (fine-tuning supporting components)
  utilities:
    default_enabled: true     # Utilities enabled by default
    disabled_utilities:       # Disabled utilities list
      - "cache_service"
    enabled_utilities: []     # Forced enabled utilities list

# Global system settings
global:
  file_base_path: "resources"    # Base folder for all files (attachments, audio, etc.)

# Logging settings
logger:
  console_enabled: true   # Console log output control
  file_enabled: false    # File log output control

# Date formatting settings
datetime_formatter:
  default_timezone: "Europe/Moscow"  # Default timezone
  date_format: "%d.%m.%Y"            # Date format
  time_format: "%H:%M:%S"            # Time format
```

### Explanations:

- **`settings.yaml`** — global file for centralized system and service settings.
- **`plugin_management`** — plugin management section:
  - **`services`** — service management (application launch foundation)
  - **`utilities`** — utility management (supporting components)
- **`global`** — global system settings section:
  - **`file_base_path`** — base path for all resources (files, audio, images, etc.)
- **`logger`** — logging settings:
  - **`console_enabled`** — enable/disable console log output
  - **`file_enabled`** — enable/disable file log writing
- **`datetime_formatter`** — date formatting settings:
  - **`default_timezone`** — default timezone
  - **`date_format`** — date display format
  - **`time_format`** — time display format
- **Service and utility settings** — optional sections for overriding specific service/utility parameters:
  - Other parameters — override settings from service/utility config.yaml
  - **Launch management** — via `plugin_management` section (see "Plugin Management" section)
- See respective service/utility config.yaml for specific parameter descriptions and meanings.
- Can add new sections for other services/utilities by analogy.

### 💡 Important Features:

**Security:**
- Never commit API credentials to repository
- Use environment variables for storing secrets

**Settings Override:**
- Can override any utility parameters via global settings
- Environment variables automatically resolved in all settings
