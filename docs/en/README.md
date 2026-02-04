# 📚 Coreness Documentation

Welcome to the **Coreness** platform documentation — a system for building bots, automating business processes, and AI solutions through declarative YAML configurations.

> 🔧 **For advanced users:** [Advanced Documentation](advanced/README.md) — architecture, plugins, deployment

---

## ⚡ Documentation Table of Contents

### 🚀 [Practical Scenario Examples](EXAMPLES_GUIDE.md)
- [Quick Start](EXAMPLES_GUIDE.md#-quick-start)
- [Advanced Examples](EXAMPLES_GUIDE.md#-advanced-examples)
  - [Working with Payments](EXAMPLES_GUIDE.md#working-with-payments-invoices)
  - [Working with RAG Storage](EXAMPLES_GUIDE.md#working-with-rag-storage)

### 📋 [Scenario Creation Guide](SCENARIO_CONFIG_GUIDE.md)
- [Scenario Structure](SCENARIO_CONFIG_GUIDE.md#-scenario-structure)
- [Triggers](SCENARIO_CONFIG_GUIDE.md#-triggers-trigger)
- [Scheduled Scenarios](SCENARIO_CONFIG_GUIDE.md#-scheduled-scenarios-cron-execution)
- [Actions (step)](SCENARIO_CONFIG_GUIDE.md#-actions-step)
  - [Data Caching](SCENARIO_CONFIG_GUIDE.md#data-caching-in-scenarios)
  - [Saving Context Between Scenarios](SCENARIO_CONFIG_GUIDE.md#saving-context-between-scenarios)
- [Transitions](SCENARIO_CONFIG_GUIDE.md#-transitions-transition)
- [Placeholders](SCENARIO_CONFIG_GUIDE.md#-placeholders)
  - [Placeholder Syntax](SCENARIO_CONFIG_GUIDE.md#placeholder-syntax)
  - [Available Data](SCENARIO_CONFIG_GUIDE.md#available-data)
  - [Accessing Nested Elements](SCENARIO_CONFIG_GUIDE.md#accessing-nested-elements)
  - [Modifiers](SCENARIO_CONFIG_GUIDE.md#modifiers)
  - [Usage Examples](SCENARIO_CONFIG_GUIDE.md#usage-examples)
- [Async Actions](SCENARIO_CONFIG_GUIDE.md#-async-actions-async-actions)

### 🎯 [System Actions Guide](ACTION_GUIDE.md)

### 📡 [System Events Guide](EVENT_GUIDE.md)
- [Common Fields](EVENT_GUIDE.md#common-fields)
- [Message Fields](EVENT_GUIDE.md#message-fields)
- [Callback Fields](EVENT_GUIDE.md#callback-fields)
- [Attachment Fields](EVENT_GUIDE.md#attachment-fields)

### ⚙️ [Tenant Configuration Guide](TENANT_CONFIG_GUIDE.md)
- [tg_bot.yaml](TENANT_CONFIG_GUIDE.md#-tg_botyaml)
- [Tenant Synchronization](TENANT_CONFIG_GUIDE.md#-tenant-synchronization)

### 💾 [Storage Attributes Guide](STORAGE_CONFIG_GUIDE.md)
- [Tenant Storage](STORAGE_CONFIG_GUIDE.md#-tenant-storage)
- [User Storage](STORAGE_CONFIG_GUIDE.md#-user-storage)
- [Usage in Scenarios](STORAGE_CONFIG_GUIDE.md#-usage-in-scenarios)

### 🤖 [AI Models Guide](AI_MODELS_GUIDE.md)
- [Models](AI_MODELS_GUIDE.md#models)
- [Parameter Descriptions](AI_MODELS_GUIDE.md#parameter-descriptions)

### 🔄 [Changelog](CHANGELOG.md)

---

## 🚀 Getting Started

#### [📖 Practical Scenario Examples](EXAMPLES_GUIDE.md)

A collection of practical examples — from quick start to advanced scenarios with payments, RAG storage, and complex logic. Includes step-by-step guide for creating your first bot, basic scenario examples, advanced examples working with payments and vector storage for RAG (Retrieval-Augmented Generation).

**When to use:** If you're new to the platform, want to quickly create a test bot, or looking for implementation examples for specific tasks (e.g., working with payments, saving and searching data in vector storage).

---

## 📖 Complete Documentation Index

#### [📋 Scenario Creation Guide](SCENARIO_CONFIG_GUIDE.md)

**What it is:** Complete guide to creating and configuring scenarios for Telegram bots with support for placeholders, transitions, and dynamic logic.

**Why you need it:** All your bot actions (commands, menus, message handling) are implemented through scenarios. This describes the entire creation process: from writing triggers to complex logic with transitions and placeholders, with examples for each case.

**What's inside:**
- Scenario structure
- Triggers (scenario launch conditions)
- Action sequences (step)
- Transitions between scenarios (transition)
- Placeholders: syntax, modifiers, available data
- Practical examples for different tasks

**When to use:** When creating new scenarios or modifying existing ones. This is the main guide for working with bot logic.

---

#### [⚙️ Tenant Configuration Guide](TENANT_CONFIG_GUIDE.md)

**What it is:** Guide to configuring tenants (clients) and their Telegram bots.

**Why you need it:** When adding a new bot to the system or configuring a new tenant. This describes how to configure a bot (token, commands, scenario groups), how to organize folder structure for scenarios, and how synchronization with external repository works.

**What's inside:**
- Tenant configuration structure
- Tenant types (system and public)
- Tenant synchronization
- Bot configuration (tg_bot.yaml)
- Organizing scenarios in folders
- Synchronization with external repository

**When to use:** When adding a new bot or tenant, changing configuration of existing ones.

---

#### [💾 Storage Attributes Guide](STORAGE_CONFIG_GUIDE.md)

**What it is:** Guide to working with tenant attribute storage (Storage) — a flexible key-value structure for storing settings, limits, and functions.

**Why you need it:** When you need to store tenant settings (user limits, function parameters, tariffs, etc.) without changing the database schema. Storage allows you to flexibly add new attributes through configuration files.

**What's inside:**
- Storage structure and file organization
- Value types (strings, numbers, booleans)
- Creating and synchronizing attributes
- Usage examples

**When to use:** When you need to store tenant settings, limits, feature flags, and other configuration data.

---

#### [🎯 System Actions Guide](ACTION_GUIDE.md)

**What it is:** Complete reference of all available actions in the system.

**Why you need it:** When you know what you want to do in a scenario — send a message, delete it, process data through AI — here you'll find the needed action and all its parameters. This is the main reference for actions like `send_message`, `delete_message`, `completion`, `validate`, and others.

**What's inside:**
- List of all available actions in the system
- Detailed parameter descriptions (input and output)
- Data types and field optionality
- Practical usage examples in YAML configuration

**When to use:** Always when creating or editing scenarios and you need to know which parameters to pass to an action and how.

---

#### [📡 System Events Guide](EVENT_GUIDE.md)

**What it is:** Complete reference of all fields available in events.

**Why you need it:** When you use placeholders in scenarios (e.g., `{username}` or `{user_id}`), this data comes from events. Here are described all available fields: user ID, chat ID, message text, attachments, callback button data, and much more.

**What's inside:**
- Common fields for all events (user_id, chat_id, message_id, username, etc.)
- Message fields (event_text, attachment, is_reply, is_forward)
- Callback button fields (callback_data, callback_id)
- Attachment structure (photos, documents, videos, audio, etc.)
- Usage examples in placeholders

**When to use:** When working with placeholders in scenarios, when you need to get data from an event.

---

#### [🤖 AI Models Guide](AI_MODELS_GUIDE.md)

**What it is:** Reference for available AI models through Polza.AI and their parameters.

**Why you need it:** When you use the `completion` action in scenarios and want to choose a suitable AI model. Here are described all available models (OpenAI, Google, Anthropic, DeepSeek, etc.), their parameters, prices, and capabilities.

**What's inside:**
- List of all available models by providers
- Parameter support (JSON, Tools, temperature, max_tokens, etc.)
- Prices per million tokens
- Parameter descriptions and their purpose

**When to use:** When configuring AI scenarios, when you need to choose a model and configure generation parameters.

---

#### [🔄 Changelog](CHANGELOG.md)

Latest changes, new features, breaking changes, and migrations.

**When to use:** For tracking platform updates and checking breaking changes when updating.

---

## 📚 Recommended Learning Order

1. **[Practical Examples](EXAMPLES_GUIDE.md)** — create your first bot and explore examples
2. **[Scenario Guide](SCENARIO_CONFIG_GUIDE.md)** — learn scenario creation
3. **[Actions Guide](ACTION_GUIDE.md)** — learn available actions
4. **[Events Guide](EVENT_GUIDE.md)** — learn working with placeholders
5. **[Tenant Setup](TENANT_CONFIG_GUIDE.md)** — configure your bot
6. **[Storage Attributes](STORAGE_CONFIG_GUIDE.md)** — work with data
7. **[AI Models](AI_MODELS_GUIDE.md)** — AI setup (optional)
8. **[Changelog](CHANGELOG.md)** — latest changes (optional)

---
