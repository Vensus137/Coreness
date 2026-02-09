---
title: Platform Architecture
description: Detailed Coreness architecture description. Event-driven system, plugins, DI container, multitenancy and project structure.
keywords: coreness architecture, event-driven, dependency injection, plugins, multitenancy
---

# Project Architecture

## ⚠️ System Requirements

### Python Version
- **✅ Recommended:** Python 3.11
- **❌ Not recommended:** Python 3.12+ (may work incorrectly or not work at all)
- **ℹ️ Reason:** Dependencies on specific library and API versions

## Libraries Used

- **SQLAlchemy** — ORM for database operations
- **PyYAML** — YAML config parsing
- **psycopg2-binary** — PostgreSQL connection driver
- **python-dotenv** — environment variable loading
- **unidecode** — transliteration
- **emoji** — emoji support
- **requests** — HTTP client for external API requests (tools, dev)
- **aiohttp** — asynchronous HTTP client for Telegram Bot API
- **openai** — library for OpenAI API via OpenRouter
- **gitpython** — Git repository operations (deployment, updates)
- **telegramify-markdown** — Markdown to Telegram MarkdownV2 format conversion
- **croniter** — cron expression parsing for scheduled scenarios
- **pydantic** — data validation against config.yaml schemas
- **cryptography** — self-signed SSL certificate generation for Telegram webhooks
- **pgvector** — vector data operations in PostgreSQL for RAG (Retrieval-Augmented Generation)
- **python-dateutil** — date and time interval handling (correct month/year processing, month edges)
- **aiofiles** — asynchronous file operations
- **PyMuPDF** — PDF text extraction (fast, lightweight)
- **python-docx** — DOCX text extraction
- **chardet** — text encoding detection
- **beautifulsoup4** — HTML parsing and cleaning
- **html5lib** — HTML parser backend
- **pandas** — HTML table extraction
- **filetype** — file type detection via magic bytes

### Deployment System Dependencies

Deployment utility (`tools/deployment/`) uses additional libraries:
- **gitpython** — repository cloning, Git operations
- **requests** — GitHub API interaction for creating Merge Requests
- **PyYAML** — deployment configuration parsing (`config.yaml`)
- **python-dotenv** — environment variable loading (tokens, API keys)

## Operational Database

The project supports **two databases** with preset switching:

- **SQLite** — local database for small projects (simple setup)
- **PostgreSQL** — production database for production (high performance, scalability)

## Core Principles

- **Microservice Architecture**: each service operates independently and self-sufficiently
- **Event Driven Architecture**: all actions are initiated by events, processed by orchestrator
- **Vertical Slice Architecture**: each service is independent, receives only necessary data, doesn't depend on other services
- **Configurability**: all logic and routing are externalized to yaml configs
- **Layer Isolation**: clear responsibility separation between layers with dependency hierarchy
- **Inter-service Communication** — only through DB, except rare cases when a service provides public methods (API) for integration or special tasks

## Layers and Their Purpose

### **Foundation (foundation)** — Fundamental Utilities
- **Purpose:** Critically important utilities required to create DI-container and launch application.
- **Location:** `plugins/utilities/foundation/`
- **Can use:** Only Python system libraries.

### **Custom Layers** — Thematic Utility Layers
- **Purpose:** Utilities for specific technologies or platforms (Telegram, API, databases, etc.).
- **Location:** `plugins/utilities/[layer_name]/` (e.g., `telegram/`, `ai/`, `database/`)
- **Can use:** Foundation and utilities within its own layer (cross-layer usage not recommended).

### **Core (core)** — Infrastructure Utilities
- **Purpose:** Utilities for event creation and processing, DB queue writing, database operations. Highest utility level.
- **Location:** `plugins/utilities/core/`
- **Can use:** Foundation, custom-layers, and other core utilities.

### **Services (services)** — Business Services
- **Purpose:** Core business logic of the application, plugins with specific functionality.
- **Location:** `plugins/services/`
- **Can use:** Foundation, custom-layers, and core utilities.

📋 **Practical Layer Usage Examples:** [Plugin Guide](PLUGINS_GUIDE.md#practical-layer-usage-examples)

## Dependency Hierarchy

```
Foundation (logger, plugins_manager, settings_manager)
    ↑
┌─────────────────┐
│  Custom Layers  │
│ (telegram, etc) │
└─────────────────┘
    ↑
┌────────┐
│  Core  │
│  ───>  │
└────────┘
    ↑
Services
```

### Dependency Rules
1. **Foundation** — use only Python system libraries
2. **Custom Layers** — use foundation and utilities within their layer (cross-layer usage not recommended)
3. **Core** — use foundation, custom-layers, and other core utilities
4. **Services** — use foundation, custom-layers, and core utilities
5. **Circular dependencies** are **FORBIDDEN**

📋 **Dependency Examples and Practical Recommendations:** [Plugin Guide](PLUGINS_GUIDE.md#dependency-system)

## Directory Structure

```
app/                    # Core application
├── application.py      # Entry point and orchestrator
└── di_container.py     # Dependency container

plugins/                # Plugins (utilities and services)
├── utilities/          # Supporting utility layers
│   ├── foundation/     # Fundamental utilities (logger, plugins_manager)
│   ├── telegram/       # Telegram utilities (tg_bot_api, tg_utils)
│   ├── ai/             # AI utilities (ai_client)
│   └── core/           # Core utilities (event_processor, database_service)
└── services/           # Business services (plugins)

utils/                  # System utilities
├── database/           # DB utilities (migrations, updates)
├── updater/            # Core update utilities
└── ...                 # Other system utilities

config/                 # Business configuration
└── settings.yaml       # Global system settings
```

📋 **Plugin Creation Rules and Folder Structure:** [Plugin Guide](PLUGINS_GUIDE.md#plugin-creation-rules)

## Processing Flow

1. **Application** (`app/application.py`) initializes foundation utilities (logger, plugins_manager), collects information about all plugins, registers them, creates dependency container, and starts all services.
2. **Core** utilities (`plugins/utilities/core/`) receive events from external sources (e.g., Telegram Bot API via HTTP, external services), process them, and pass to orchestrator.
3. **Orchestrator** analyzes events, finds matching scenarios, and creates execution tasks.
4. **Services** (`plugins/services/`) execute business logic through core method calls.
5. **Inter-service Communication** — only through DB.

📋 **Initialization Algorithm and Loading Order:** [Plugin Guide](PLUGINS_GUIDE.md#initialization-and-loading-order)
