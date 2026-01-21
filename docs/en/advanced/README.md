# 📚 Coreness Extended Documentation

Advanced guides for deep understanding of the platform, plugin development, and infrastructure management.

> 📖 **Main Documentation:** [Scenario and Configuration Guides](../README.md) — for building bots and working with the platform

---

## ⚡ Documentation Table of Contents

### 🔧 [Master Bot — Tenant Management System](MASTER_BOT_GUIDE.md)
- [Purpose](MASTER_BOT_GUIDE.md#-purpose)
- [Structure](MASTER_BOT_GUIDE.md#-structure)
- [Core Features](MASTER_BOT_GUIDE.md#-core-features)
- [Security](MASTER_BOT_GUIDE.md#-security)

### 🏗️ [Platform Architecture](ARCHITECTURE.md)
- [System Requirements](ARCHITECTURE.md#-system-requirements)
- [Libraries Used](ARCHITECTURE.md#libraries-used)
- [Operational Database](ARCHITECTURE.md#operational-database)
- [Project Structure](ARCHITECTURE.md#project-structure)
- [Plugin Architecture](ARCHITECTURE.md#plugin-architecture)
- [Application Lifecycle](ARCHITECTURE.md#application-lifecycle)

### 🚀 [Deployment and Operations](DEPLOYMENT.md)
- [Quick Start](DEPLOYMENT.md#quick-start)
- [Core Operations](DEPLOYMENT.md#core-operations)
  - [Server Update](DEPLOYMENT.md#server-update)
  - [Repository Deployment](DEPLOYMENT.md#repository-deployment)
  - [Database Operations](DEPLOYMENT.md#database-operations)
- [Configuration](DEPLOYMENT.md#configuration)
- [Docker](DEPLOYMENT.md#docker)
- [Webhook Setup](DEPLOYMENT.md#webhook-setup)

### 🔌 [Plugin Development](PLUGINS_GUIDE.md)
- [Architecture Overview](PLUGINS_GUIDE.md#architecture-overview)
- [Plugin Types](PLUGINS_GUIDE.md#plugin-types)
- [Creating Plugins](PLUGINS_GUIDE.md#creating-plugins)
- [Lifecycle Methods](PLUGINS_GUIDE.md#lifecycle-methods)
- [Dependency Injection](PLUGINS_GUIDE.md#dependency-injection)
- [Best Practices](PLUGINS_GUIDE.md#best-practices)

### ⚙️ [Plugin Configuration](PLUGIN_CONFIG_GUIDE.md)
- [config.yaml Structure](PLUGIN_CONFIG_GUIDE.md#configyaml-structure)
- [Base Fields](PLUGIN_CONFIG_GUIDE.md#base-fields)
- [Plugin Interfaces](PLUGIN_CONFIG_GUIDE.md#plugin-interfaces)
- [Configuration Examples](PLUGIN_CONFIG_GUIDE.md#configuration-examples)

### 🎯 [System Actions](SYSTEM_ACTION_GUIDE.md)

### ⚙️ [System Settings](SETTINGS_CONFIG_GUIDE.md)
- [settings.yaml Structure](SETTINGS_CONFIG_GUIDE.md#settingsyaml-structure)
- [Plugin Management](SETTINGS_CONFIG_GUIDE.md#plugin-management)
- [Global Settings](SETTINGS_CONFIG_GUIDE.md#global-settings)

### 📝 [Logging](LOGGING_GUIDE.md)
- [Logging Levels](LOGGING_GUIDE.md#logging-levels)
- [Log Structure](LOGGING_GUIDE.md#log-structure)
- [Logging Configuration](LOGGING_GUIDE.md#logging-configuration)
- [Docker Logs](LOGGING_GUIDE.md#docker-logs)

### 🧪 [Testing](TESTING_GUIDE.md)
- [Scenario Testing](TESTING_GUIDE.md#scenario-testing)
- [Unit Tests](TESTING_GUIDE.md#unit-tests)
- [Integration Testing](TESTING_GUIDE.md#integration-testing)
- [E2E Testing](TESTING_GUIDE.md#e2e-testing)

---

## 🚀 Getting Started

#### [🔧 Master Bot — Tenant Management System](MASTER_BOT_GUIDE.md)

**Ready-to-use solution for managing tenants via Telegram**

Master Bot is a system bot for managing all platform tenants, working similar to @BotFather in Telegram.

**Features:**
- Select and switch between tenants
- Set bot and AI provider tokens
- Manage Tenant Storage and User Storage
- Sync data with GitHub repositories
- Role-based access control (admin, owner, user)
- Scheduled automated tasks

**When to use:** For centralized management of all tenants, bot configuration, Storage operations, and configuration synchronization.

---

## 📖 Complete Documentation Index

#### [🏗️ Platform Architecture](ARCHITECTURE.md)

**What it is:** Detailed description of platform architecture, patterns, and operational principles.

**Why you need it:** Understanding the platform's internal structure: from project organization to plugin system principles and event processing.

**What's inside:**
- Event-Driven Architecture — event model
- Vertical Slice Architecture — component isolation
- Dependency Injection — dependency management
- Multi-tenant architecture — data isolation
- Plugin system (utilities and services)
- Application lifecycle and graceful shutdown

**When to use:** For understanding platform principles, developing plugins, extending functionality, or contributing to development.

---

#### [🚀 Deployment and Operations](DEPLOYMENT.md)

**What it is:** Complete guide for platform installation and updates.

**Why you need it:** From initial setup to automated deployment via GitHub Actions and version management.

**What's inside:**
- Server installation (Linux, Docker)
- Environment setup (test + prod)
- PostgreSQL and pgvector configuration
- Database migrations
- Automated deployment via GitHub Actions
- Update and rollback system
- Backup and recovery
- Monitoring and logging

**When to use:** When deploying the platform in production, setting up CI/CD, or updating versions.

---

#### [🔌 Plugin Development](PLUGINS_GUIDE.md)

**What it is:** Guide for creating custom services and utilities.

**Why you need it:** Extend platform functionality through plugin architecture: create services for event processing or utilities for supporting tasks.

**What's inside:**
- Plugin types (services and utilities)
- Plugin structure and config.yaml
- Lifecycle methods (initialize, startup, shutdown)
- Dependency Injection in plugins
- Plugin creation examples
- Best practices and recommendations

**When to use:** When adding new functionality, integrating external services, or creating custom actions for scenarios.

---

#### [⚙️ Plugin Configuration](PLUGIN_CONFIG_GUIDE.md)

**What it is:** Detailed description of config.yaml structure for plugins.

**Why you need it:** Complete reference for all possible plugin configuration parameters and their purpose.

**What's inside:**
- config.yaml structure
- Required and optional fields
- Interface descriptions (services, actions, events)
- Dependency Injection in configuration
- Examples for different plugin types

**When to use:** When developing plugins for proper config.yaml setup.

---

#### [🎯 System Actions](SYSTEM_ACTION_GUIDE.md)

**What it is:** Complete reference of platform internal actions.

**Why you need it:** Detailed description of all system actions used in scenarios: from sending messages to database operations.

**What's inside:**
- All actions with parameter descriptions
- Input and output data
- Error codes and handling
- Usage examples
- Implementation technical details

**When to use:** For deep understanding of action behavior or when developing custom actions for plugins.

---

#### [⚙️ System Settings](SETTINGS_CONFIG_GUIDE.md)

**What it is:** Global platform parameters.

**Why you need it:** System-wide parameter configuration via `config/settings.yaml`: plugin management, file paths, shutdown settings, and other global parameters.

**What's inside:**
- Plugin management (enable/disable)
- Global settings (paths, limits)
- Graceful shutdown parameters
- Service settings
- Configuration examples

**When to use:** When setting up environment, optimizing performance, or managing enabled plugins.

---

#### [📝 Logging](LOGGING_GUIDE.md)

**What it is:** Working with logs and debugging.

**Why you need it:** Logging system setup, log levels, log structure, and application debugging recommendations.

**What's inside:**
- Logging levels (DEBUG, INFO, WARNING, ERROR)
- Log structure and formatting
- Plugin logging configuration
- Viewing logs in Docker
- Debugging and troubleshooting
- Best practices

**When to use:** When debugging issues, monitoring platform operation, or developing plugins.

---

#### [🧪 Testing](TESTING_GUIDE.md)

**What it is:** Platform testing approaches.

**Why you need it:** Testing strategies for scenarios, plugins, and the entire platform.

**What's inside:**
- Scenario testing
- Unit tests for plugins
- Integration testing
- E2E bot testing
- Test environment
- Test examples

**When to use:** When developing scenarios, creating plugins, or setting up CI/CD.

---

## 🎯 Recommended Learning Path

For platform developers:

1. **[Architecture](ARCHITECTURE.md)** — understand the platform structure
2. **[Plugin Development](PLUGINS_GUIDE.md)** — learn to create plugins
3. **[Plugin Configuration](PLUGIN_CONFIG_GUIDE.md)** — study config.yaml
4. **[System Actions](SYSTEM_ACTION_GUIDE.md)** — deep dive into actions
5. **[Logging](LOGGING_GUIDE.md)** — configure debugging
6. **[Testing](TESTING_GUIDE.md)** — organize testing

For platform administrators:

1. **[Deployment](DEPLOYMENT.md)** — deploy the platform
2. **[Master Bot](MASTER_BOT_GUIDE.md)** — configure tenant management
3. **[System Settings](SETTINGS_CONFIG_GUIDE.md)** — optimize configuration

---

## 🔙 Back to Main Documentation

- [📚 Main Documentation](../README.md)
- [🚀 Practical Examples](../EXAMPLES_GUIDE.md)
- [📋 Scenario Guide](../SCENARIO_CONFIG_GUIDE.md)
- [🎯 Action Guide](../ACTION_GUIDE.md)
