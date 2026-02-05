---
title: Plugin Development
description: Guide to creating custom plugins for Coreness. Plugin structure, lifecycle methods, DI and examples.
keywords: plugin development, coreness plugins, lifecycle methods, custom plugins
---

# Plugin Guide

## Architecture Overview

Project uses modular architecture based on plugins. All plugins are in `plugins/` folder and divided into two main types:

📋 **Detailed Project Architecture:** [Project Architecture](ARCHITECTURE.md)

### 📁 Folder Structure
```
plugins/
├── utilities/         # Supporting utilities
│   ├── foundation/    # Fundamental utilities (logger, plugins_manager)
│   ├── custom_layers/ # Thematic layers (telegram, api, database)
│   ├── core/          # Core utilities (event_processor, database_service)
│   └── extensions/    # Utility extensions (not included in base platform version)
└── services/          # Business services
    ├── core/          # Core services
    ├── hub/           # Hub services
    ├── additional/    # Additional services
    └── extensions/    # Service extensions (not included in base platform version)
```

## Plugin Types

### 🔧 Utilities
- **Purpose**: Supporting components for functionality extension
- **Features**:
  - Cannot work autonomously
  - Passed to services as dependencies via DI
  - Can have dependencies on other utilities
  - Organized by special layers and levels

📋 **Conceptual Layer Description:** [Project Architecture - Layers and Their Purpose](ARCHITECTURE.md#layers-and-their-purpose)

### 🚀 Services
- **Purpose**: Core application business logic
- **Features**:
  - Work autonomously and asynchronously
  - Can have optional `run()` method for background launch
  - Can depend on utilities (foundation, level-layers, core, database)
  - Can be organized into subcategories (core, hub, additional)

### 🔌 Extensions
- **Purpose**: Additional plugins to extend platform functionality
- **Features**:
  - Can be either utilities or services
  - Located in `plugins/utilities/extensions/` or `plugins/services/extensions/`
  - Allow adding new functionality without modifying base platform
  - Not overwritten during platform updates
  - Added by users as needed
  - Follow the same rules as regular plugins

## Practical Layer Usage Examples

### Foundation — When to Use?
**Use for:**
- Logging (logger)
- Plugin management (plugins_manager)
- Any utilities needed to launch DI-container

**Examples:**
```python
# ✅ Correct: logger uses only system libraries
import logging
import sys
from datetime import datetime

class Logger:
    def __init__(self):
        # Only Python system libraries
        pass
```

### Custom Layers — When to Use?
**Use for:**
- Thematic utilities (telegram, api, etc.)
- Utilities for specific technologies or platforms
- Grouping related utilities by functionality
- Utilities within own layer (cross-layer usage not recommended)

### Core — When to Use?
**Use for:**
- Event processing (event_processor)
- Database operations (database_service)
- Any high-level infrastructure utilities

### Services — When to Use?
**Use for:**
- Application business logic
- Queue action processing
- Autonomous services with `run()` method

### Extensions — When to Use?
**Use for:**
- Extending platform functionality with additional plugins
- Adding new functionality without modifying base platform
- Plugins that should not be overwritten during platform updates
- Creating custom plugins for specific tasks

**How to add an extension:**
1. Copy plugin folder to `plugins/utilities/extensions/` or `plugins/services/extensions/`
2. Ensure folder contains `config.yaml`
3. Restart application

Extensions are automatically discovered and loaded by the system without additional configuration.

## Plugin Creation Rules

### 1. Plugin Folder Structure
```
my_plugin/
├── config.yaml        # REQUIRED! Without it plugin won't be discovered
├── my_plugin.py       # Plugin main code
└── README.md          # Documentation (optional)
```

**⚠️ Important:** `config.yaml` file is **required** for all plugins. Without it plugin won't be discovered by system and won't work.

### 2. Plugin Type Determination
Plugin type determined **automatically** by location:
- If plugin in `plugins/utilities/` → **utility**
- If plugin in `plugins/services/` → **service**

### 3. Nesting Support
Plugins can be at any nesting depth:
```
plugins/
├── utilities/
│   ├── foundation/
│   │   ├── logger/           # Foundation utility
│   │   └── plugins_manager/  # Foundation utility
│   ├── telegram/
│   │   ├── telegram_api/     # Telegram Bot API
│   │   └── telegram_polling/ # Telegram polling
│   ├── core/
│   │   ├── action_hub/       # Core utility
│   │   └── database_manager/ # Core utility
│   └── extensions/
│       └── http_server/      # Extension utility
└── services/
    ├── core/
    │   ├── event_processor/  # Core service
    │   └── scenario_processor/ # Core service
    ├── hub/
    │   ├── bot_hub/          # Hub service
    │   └── tenant_hub/       # Hub service
    ├── additional/
    │   └── ai_service/       # Additional service
    └── extensions/
        ├── http_api_service/ # Extension service
        └── ai_rag_service/   # Extension service (RAG functionality)
```

## Plugin Configuration (config.yaml)

Detailed description of configuration file structure for all plugin types (utilities and services) is in separate document:

📋 **[YAML Config Templates for Services and Utilities](PLUGIN_CONFIG_GUIDE.md)**

This document contains:
- Universal template for all utilities (Foundation, Core, Database, Level N)
- Service template
- Required and optional sections
- Configuration examples
- Dependency rules
- Key differences between utilities and services

## Dependency System

📋 **Dependency Hierarchy and Rules:** [Project Architecture - Dependency Hierarchy](ARCHITECTURE.md#dependency-hierarchy)

### Dependency Examples
```yaml
# Foundation utility (logger)
# dependencies: absent (uses only system libraries)

# Custom layer utility (tg_bot_api)
dependencies:
  - "logger"           # Foundation utility
  - "settings_manager" # Foundation utility

# Service (chat_service)
dependencies:
  - "logger"              # Foundation utility
  - "database_service"    # Core utility
  - "event_processor"     # Core utility

# Plugin with optional dependencies (any type)
dependencies:
  - "logger"              # Required dependency
  - "hash_manager"        # Required dependency
optional_dependencies:
  - "cache_service"       # Optional dependency
  - "analytics_service"   # Optional dependency
```

**Note:** Optional dependencies don't affect initialization order and don't cause errors if absent.

## Initialization and Loading Order

### Initialization Algorithm
1. **Scanning** all plugins recursively
2. **Building dependency graph**
3. **Checking circular dependencies**
4. **Topological sorting** of utilities
5. **Utility initialization** in dependency order
6. **Service initialization** (any order)

### Initialization Order Example
```
1. logger (foundation, no dependencies)
2. plugins_manager (foundation, depends on logger)
3. settings_manager (foundation, depends on logger)
4. tg_bot_api (telegram layer, depends on logger, settings_manager)
5. tg_permission_manager (telegram layer, depends on logger, tg_bot_api)
6. event_processor (core, depends on logger, settings_manager, database_service)
7. chat_service (depends on logger, database_service, event_processor)
```

## Best Practices

### ✅ Recommended
- Use **meaningful names** for plugins
- Group **related utilities** by appropriate layers
- Document **dependencies** and **interfaces**
- Follow **single responsibility principle**
- Use **typing** in configuration
- **Foundation utilities** should use only Python system libraries

### ❌ Forbidden
- Create **circular dependencies** - system doesn't support and application won't start
- Create **plugins without config.yaml** - plugin won't be discovered and won't work
- Make **services dependent on services** - violates architecture
- **Foundation utilities** shouldn't depend on other utilities

### ⚠️ Not Recommended
- Use **too deep nesting** (>5 levels)
- Duplicate **functionality** in different plugins
- **Custom layer utilities** use utilities from other custom-layers unnecessarily

## Debugging and Diagnostics

### Dependency Check
```python
# CRITICAL: Check circular dependencies
if not plugins_manager.check_circular_dependencies():
    print("❌ CIRCULAR DEPENDENCIES DETECTED!")
    print("Application won't start. Fix dependencies.")

# Get initialization order
order = plugins_manager.get_dependency_order()
print("Initialization order:", order)

# Get specific plugin dependencies
deps = plugins_manager.get_plugin_dependencies("my_plugin")
print("Dependencies:", deps)

# Check all plugins have config.yaml
missing_configs = plugins_manager.find_plugins_without_config()
if missing_configs:
    print("❌ PLUGINS WITHOUT config.yaml:", missing_configs)
    print("These plugins won't be discovered by system!")

# Check Foundation utilities use only system libraries
foundation_issues = plugins_manager.check_foundation_utilities()
if foundation_issues:
    print("❌ FOUNDATION UTILITIES USE OTHER UTILITIES:", foundation_issues)
```

### Logging
All plugin operations are logged:
- Configuration loading
- Plugin discovery
- Dependency errors
- Initialization order
- Foundation utility checks

## Migration and Updates

### Adding New Plugin
1. Create folder in appropriate directory (foundation/core/database/level_N/services)
2. Add `config.yaml` with description
3. Implement plugin code
4. Restart application

### Changing Dependencies
1. Update `config.yaml`
2. Check no circular dependencies
3. Ensure dependency hierarchy compliance
4. Restart application

### Removing Plugin
1. Delete plugin folder
2. Remove dependencies from other plugins
3. Restart application
