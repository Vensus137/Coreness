---
title: Advanced Documentation
description: Advanced Coreness documentation for experienced users. Architecture, plugin development and system settings.
keywords: coreness architecture, plugins, system settings
---

# 📚 Coreness Extended Documentation

Advanced guides for deep understanding of the platform, plugin development, and infrastructure management.

> 📖 **Main Documentation:** [Scenario and Configuration Guides](../README) — for building bots and working with the platform

## ⚡ Documentation Table of Contents

- [Platform Architecture](ARCHITECTURE)
- [Plugin Development](PLUGINS_GUIDE)
- [Plugin Configuration](PLUGIN_CONFIG_GUIDE)
- [System Actions](SYSTEM_ACTION_GUIDE)
- [System Settings](SETTINGS_CONFIG_GUIDE)
- [Logging](LOGGING_GUIDE)
- [Testing](TESTING_GUIDE)

## 📖 Complete Documentation Index

### [🏗️ Platform Architecture](ARCHITECTURE)

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

### [🔌 Plugin Development](PLUGINS_GUIDE)

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

### [⚙️ Plugin Configuration](PLUGIN_CONFIG_GUIDE)

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

### [🎯 System Actions](SYSTEM_ACTION_GUIDE)

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

### [⚙️ System Settings](SETTINGS_CONFIG_GUIDE)

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

### [📝 Logging](LOGGING_GUIDE)

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

### [🧪 Testing](TESTING_GUIDE)

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

## 🎯 Recommended Learning Path

For platform developers:

1. **[Architecture](ARCHITECTURE)** — understand the platform structure
2. **[Plugin Development](PLUGINS_GUIDE)** — learn to create plugins
3. **[Plugin Configuration](PLUGIN_CONFIG_GUIDE)** — study config.yaml
4. **[System Actions](SYSTEM_ACTION_GUIDE)** — deep dive into actions
5. **[Logging](LOGGING_GUIDE)** — configure debugging
6. **[Testing](TESTING_GUIDE)** — organize testing

For platform administrators:

1. **[System Settings](SETTINGS_CONFIG_GUIDE)** — optimize configuration

## 🔙 Back to Main Documentation

- [📚 Main Documentation](../README)
- [🚀 Getting Started](../getting-started/README)
- [📋 Scenario Guide](../guides/SCENARIO_CONFIG_GUIDE)
- [🎯 Action Guide](../reference/ACTION_GUIDE)
