# Coreness — Multi-tenant Platform for Automation and AI Solutions

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16+](https://img.shields.io/badge/PostgreSQL-16+-316192.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram-Bot%20API-26A5E4.svg?logo=telegram&logoColor=white)](https://core.telegram.org/bots/api)

<p align="left">
  <a href="https://t.me/vensus137"><img src="https://img.shields.io/badge/Developer-@vensus137-blue.svg" alt="Developer"></a>
</p>

> 🌐 **Language**: [Русский](README.md) | **English**

> **Note on language:** The project supports English (docs, code, tooling). You may still run into occasional inaccuracies or mixed-language bits.

`Coreness` is an **event-driven** platform for building automated **workflows** through configuration files. You describe the logic in YAML, and the platform handles execution, data storage, and integrations.

**Key Use Cases:**
- **Bot Development** (Telegram and other messengers)
- **Business Process Automation** and notifications
- **AI Assistants** and chatbots with LLM integration
- **Scheduled Tasks** and event-driven processing

---

## ✨ Key Features

### 🎯 Declarative Configuration
All bot logic is defined in **YAML files**. Create complex scenarios, triggers, conditions, and transitions without writing code.

```yaml
start:
  trigger:
    - event_type: "message"
      event_text: "/start"
  
  step:
    - action: "send_message"
      params:
        text: "Hello, {first_name}! 👋"
        inline:
          - [{"📋 Menu": "menu"}, {"ℹ️ Help": "help"}]
```

### 🏢 Built-in Multi-tenancy
Single platform instance — multiple independent bots with complete data isolation:
- **Row-Level Security** in PostgreSQL
- Separate configurations, scenarios, and Storage for each tenant
- GitHub synchronization for configurations (Infrastructure as Code)
- **Master Bot** — ready-to-use bot for tenant management (like @BotFather)

### 🤖 AI and RAG
Built-in integration with LLM models and vector search:
- **Semantic search** via pgvector (PostgreSQL)
- Support for OpenAI, Anthropic, Google, DeepSeek via aggregators (OpenRouter, Azure OpenAI)
- **RAG context** in scenarios — bots respond based on knowledge base
- Function calling and AI agents with tools

### ⏰ Scheduled Scenarios
Automation based on cron expressions:
- Daily reports
- Scheduled broadcasts
- Periodic checks and notifications

### 🔧 Flexibility and Extensibility
- **Plugin Architecture** — easily add new functionality
- **Storage** — flexible key-value storage for tenant settings
- **Transitions** — scenario flow control
- **Placeholders** — dynamic data in any parameters

---

## 🚀 What's Inside

**🎯 Configuration**
- **YAML Scenarios** — all logic described declaratively without code
- **Triggers** — launch by events, conditions, or schedule (cron)
- **30+ Actions** — send messages, AI, HTTP, validation, payments, etc.
- **Placeholders** — dynamic data with modifiers

**🏢 Architecture**
- **Multi-tenancy** — data isolation through Row-Level Security
- **Events** — event-driven architecture, loose coupling
- **Storage** — key-value storage for settings and states
- **Plugins** — extensibility through utilities and services

**🤖 AI and Integrations**
- **AI Completion** — OpenAI, Anthropic, Google, DeepSeek via aggregators (OpenRouter, Azure OpenAI)
- **Embeddings** — text vector representation generation via AI API
- ⭐ **RAG (vector search)** — saving, searching and managing embeddings via pgvector
- ⭐ **Webhooks** — Telegram and GitHub synchronization

**🚀 Deployment**
- **Docker** — ready configurations (test + prod)
- ...and much more

<sup>⭐ Additional plugins and their extensions. For more information, contact the [developer](https://t.me/vensus137)</sup>

---

## 📖 Documentation

Complete documentation is available in the **[`docs/`](docs/)** folder → **[Documentation Navigation](docs/en/README.md)**

### Quick Start
- 🚀 **[Practical Examples](docs/en/EXAMPLES_GUIDE.md)** — from simple bot to AI agent with RAG
- 📋 **[Scenario Guide](docs/en/SCENARIO_CONFIG_GUIDE.md)** — creating bot logic
- 🎯 **[Action Guide](docs/en/ACTION_GUIDE.md)** — reference of all available actions

### Configuration
- ⚙️ **[Tenant Configuration](docs/en/TENANT_CONFIG_GUIDE.md)** — bot setup
- 💾 **[Attribute Storage](docs/en/STORAGE_CONFIG_GUIDE.md)** — working with Storage
- 🤖 **[AI Models](docs/en/AI_MODELS_GUIDE.md)** — LLM integration

### Reference
- 📡 **[System Events](docs/en/EVENT_GUIDE.md)** — available fields in placeholders
- 🔄 **[Changelog](docs/en/CHANGELOG.md)** — change history and updates

### Advanced Documentation
- 🔧 **[Master Bot](docs/en/advanced/MASTER_BOT_GUIDE.md)** — tenant management system (like @BotFather)
- 🏗️ **[Platform Architecture](docs/en/advanced/ARCHITECTURE.md)** — detailed architecture and patterns
- 🚀 **[Deployment](docs/en/advanced/DEPLOYMENT.md)** — complete installation and update guide
- 🔌 **[Plugin Development](docs/en/advanced/PLUGINS_GUIDE.md)** — creating custom services and utilities
- ⚙️ **[System Configuration](docs/en/advanced/SETTINGS_CONFIG_GUIDE.md)** — global platform parameters
- 📝 **[Logging](docs/en/advanced/LOGGING_GUIDE.md)** — working with logs and debugging
- 🧪 **[Testing](docs/en/advanced/TESTING_GUIDE.md)** — platform testing approaches

---

## 🏗️ Architecture

```
coreness/
├── app/                 # Application core
│   ├── application.py   # Entry point and orchestrator
│   └── di_container.py  # DI container
│
├── plugins/             # Plugin system
│   ├── utilities/       # Utilities
│   └── services/        # Services
│
├── config/              # Configurations
│   ├── settings.yaml    # Global settings
│   └── tenant/          # Tenant configurations
│
├── tools/               # Platform utilities
├── scripts/             # Scripts
├── tests/               # Tests
└── docker/              # Docker configuration
```

**Principles:**
- **Event-Driven Architecture** — loose coupling through events
- **Vertical Slice Architecture** — each service is self-contained
- **Dependency Injection** — dependency management through DI container
- **Multi-tenant** — data isolation through Row-Level Security

---

## 📞 Contacts

**Project Telegram Channel:** [t.me/coreness](https://t.me/coreness)  
News, updates, and discussions

**Contact the Author:** [@vensus137](https://t.me/vensus137)  
Questions, suggestions, collaboration

---

## 📄 License

Distributed under the [MIT](LICENSE) license.

---

<p align="center">
  <strong>Coreness</strong> — Create. Automate. Scale.
</p>
