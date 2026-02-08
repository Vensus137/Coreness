---
title: Documentation
description: Platform for AI agents and Telegram bots with YAML. Quick start, guides and reference.
keywords: Coreness, AI agents, Telegram bots, self-hosted platform, multitenant, Python, YAML configuration, automation, chatbots, RAG, AI models
---

# Coreness — Platform for Automation and AI Solutions

**Coreness** is an event-driven platform for building automated workflows through configuration files. You describe the logic in YAML; the platform handles execution, data storage, and integrations.

**Key use cases:** bot development (Telegram and others), business process automation, AI assistants and chatbots with LLM, scheduled tasks.

This documentation covers quick start, scenario guides, and reference.

> 🔧 **For advanced users:** [Advanced Documentation](advanced/README) — architecture, plugins

## ⚡ Documentation Table of Contents

- [Getting Started](getting-started/README)
- [Practical Scenario Examples](getting-started/EXAMPLES_GUIDE)
- [Master Bot — Tenant Management](getting-started/MASTER_BOT_GUIDE)
- [Deployment](getting-started/DEPLOYMENT)
- [Scenario Creation Guide](guides/SCENARIO_CONFIG_GUIDE)
- [Tenant Configuration Guide](guides/TENANT_CONFIG_GUIDE)
- [Storage Attributes Guide](guides/STORAGE_CONFIG_GUIDE)
- [System Actions Guide](reference/ACTION_GUIDE)
- [System Events Guide](reference/EVENT_GUIDE)
- [Placeholders](reference/PLACEHOLDERS)
- [AI Models Guide](reference/AI_MODELS_GUIDE)
- [Changelog](CHANGELOG)

## 🚀 Getting Started

### [📖 Practical Scenario Examples](getting-started/EXAMPLES_GUIDE)

A collection of examples: from quick start to scenarios with payments and RAG. Step-by-step first bot guide, basic and advanced examples included.

**When to use:** You're new to the platform, want a test bot fast, or need an example for a specific task (payments, vector storage).

---

### [🔧 Master Bot — Tenant Management](getting-started/MASTER_BOT_GUIDE)

System bot for managing tenants (like @BotFather). Use it to switch tenants, set tokens, manage Storage, and sync with GitHub.

**When to use:** You need one place to manage all tenants and bots after deployment.

---

## 📖 Complete Documentation Index

### [📋 Scenario Creation Guide](guides/SCENARIO_CONFIG_GUIDE)

**What it is:** Guide to creating scenarios for Telegram bots. Placeholders, transitions, and dynamic logic are covered.

**Why you need it:** Commands, menus, and message handling all live in scenarios. The guide walks you from triggers to advanced logic, with examples.

**What's inside:**
- Scenario structure
- Triggers (scenario launch conditions)
- Action sequences (step)
- Transitions between scenarios (transition)
- Placeholders: syntax, modifiers, available data
- Practical examples for different tasks

**When to use:** When creating new scenarios or modifying existing ones. This is the main guide for working with bot logic.

---

### [🔧 Master Bot — Tenant Management](getting-started/MASTER_BOT_GUIDE)

**What it is:** Guide to Master Bot. Tenant selection, token setup, Storage, and GitHub sync.

**Why you need it:** One entry point in Telegram to manage all tenants and bots after deployment.

**When to use:** Setting up tenants, configs, and Storage.

---

### [⚙️ Tenant Configuration Guide](guides/TENANT_CONFIG_GUIDE)

**What it is:** Guide to configuring tenants (clients) and their Telegram bots.

**Why you need it:** Adding a bot or a new tenant? This covers token, commands, scenario groups, folder layout, and repo sync.

**What's inside:**
- Tenant configuration structure
- Tenant types (system and public)
- Tenant synchronization
- Bot configuration (folder `bots/`, e.g. `bots/telegram.yaml`)
- Organizing scenarios in folders
- Synchronization with external repository

**When to use:** When adding a new bot or tenant, changing configuration of existing ones.

---

### [💾 Storage Attributes Guide](guides/STORAGE_CONFIG_GUIDE)

**What it is:** Guide to tenant attribute storage (Storage). Key-value store for settings, limits, and flags.

**Why you need it:** Store tenant settings without changing the DB. Add new attributes via config files.

**What's inside:**
- Storage structure and file organization
- Value types (strings, numbers, booleans)
- Creating and synchronizing attributes
- Usage examples

**When to use:** When you need to store tenant settings, limits, feature flags, and other configuration data.

---

### [🎯 System Actions Guide](reference/ACTION_GUIDE)

**What it is:** Reference of all actions in the system.

**Why you need it:** Need to send a message, delete it, or call AI? Here you find each action and its parameters. Reference for `send_message`, `delete_message`, `completion`, `validate`, and more.

**What's inside:**
- List of all available actions in the system
- Detailed parameter descriptions (input and output)
- Data types and field optionality
- Practical usage examples in YAML configuration

**When to use:** Always when creating or editing scenarios and you need to know which parameters to pass to an action and how.

---

### [📡 System Events Guide](reference/EVENT_GUIDE)

**What it is:** Reference of all fields in events.

**Why you need it:** Placeholders like `{username}` or `{user_id}` get data from events. Here are all fields: user_id, chat_id, message text, attachments, callback data.

**What's inside:**
- Common fields for all events (user_id, chat_id, message_id, username, etc.)
- Message fields (event_text, attachment, is_reply, is_forward)
- Callback button fields (callback_data, callback_id)
- Attachment structure (photos, documents, videos, audio, etc.)
- Usage examples in placeholders

**When to use:** When working with placeholders in scenarios, when you need to get data from an event.

---

### [🤖 AI Models Guide](reference/AI_MODELS_GUIDE)

**What it is:** Reference for AI models (Polza.AI) and their parameters.

**Why you need it:** Using `completion` and need to pick a model? Here are the models (OpenAI, Google, Anthropic, DeepSeek, etc.), parameters, and prices.

**What's inside:**
- List of all available models by providers
- Parameter support (JSON, Tools, temperature, max_tokens, etc.)
- Prices per million tokens
- Parameter descriptions and their purpose

**When to use:** When configuring AI scenarios, when you need to choose a model and configure generation parameters.

---

### [🔄 Changelog](CHANGELOG)

Latest changes, new features, breaking changes, and migrations.

**When to use:** Before upgrading — see what changed and what might break.

## 📚 Recommended Learning Order

1. **[Practical Examples](getting-started/EXAMPLES_GUIDE)** — create your first bot and explore examples
2. **[Deployment](getting-started/DEPLOYMENT)** — install the platform (if not yet deployed)
3. **[Master Bot](getting-started/MASTER_BOT_GUIDE)** — configure tenant management
4. **[Scenario Guide](guides/SCENARIO_CONFIG_GUIDE)** — learn scenario creation
5. **[Actions Guide](reference/ACTION_GUIDE)** — learn available actions
6. **[Events Guide](reference/EVENT_GUIDE)** — learn working with placeholders
7. **[Tenant Setup](guides/TENANT_CONFIG_GUIDE)** — configure your bot
8. **[Storage Attributes](guides/STORAGE_CONFIG_GUIDE)** — work with data
9. **[AI Models](reference/AI_MODELS_GUIDE)** — AI setup (optional)
10. **[Changelog](CHANGELOG)** — latest changes (optional)
