---
title: Changelog
description: Coreness changelog. Latest changes, new features, breaking changes and migrations between versions.
keywords: coreness changelog, version history, updates, breaking changes, migration
---

# Changelog

All notable changes to this project documented in this file.

## [1.2.1] - 2026-02-10

### ⚠️ BREAKING CHANGES
- **ai_rag_service**: default chunk sizes increased (chunk_size 512→1000, chunk_overlap 100→200, min_chunk_size 50→200). Reprocessed documents will have fewer chunks

### Added
- **download_service**: action `download_and_extract` — download by URL, text extraction (PDF, DOCX, TXT, MD, HTML, CSV), Google Drive/Docs/Sheets/GitHub support
- **ai_rag_service**: adaptive chunking and structure preservation (tables, code, lists, headers not split)

### Fixed
- **Core Manager**: pre-release handling in update checks — “latest version” is now latest stable only; system update always shows version list with current highlighted; utility update offers choice when a pre-release exists (pre-release vs latest stable) and downloads by selected tag instead of main branch

## [1.2.0] - 2026-02-09

### ⚠️ BREAKING CHANGES
- **telegram_bot_manager:** Removed `sync_bot`, `stop_all_bots`, `sync_bot_config`, `sync_bot_commands`; sync only via `sync_telegram_bot`. Renamed: `start_bot`→`start_telegram_bot`, `stop_bot`→`stop_telegram_bot`, `get_bot_status`→`get_telegram_bot_status`, `set_bot_token`→`set_telegram_bot_token`. Bot data only via `get_telegram_bot_info_by_id` (by bot_id); `get_bot_info` and `get_telegram_bot_info` (by token) removed.
- **tenant_hub:** Removed from Action Hub (internal): `sync_tenant_data`, `sync_tenant_config`, `sync_tenants_from_files`. Use `sync_tenant` for tenant sync.

### Added
- `get_bot_id_by_tenant_id` (tenant_hub): get bot_id by tenant_id and bot_type (telegram only), for scenarios.
- `get_tenant_status`: tenant cache only (last_updated_at, last_failed_at, last_error); bot data via `get_telegram_bot_status` by bot_id.
- `restrict_chat_member` (telegram_api): action to restrict users in supergroups (permission groups: messages, attachments, other, management).
- **send_message (telegram_api):** support for flag and string for `message_reply`: `true` — reply to current event message, integer/string — message ID. For `message_edit`, string support added (same as integer) so placeholders like `"{message_id}"` work without type errors.
- **execute_scenario (transition):** new transition type that executes another scenario and returns to current scenario (unlike `jump_to_scenario` which terminates current). Cache from executed scenario automatically merged into current scenario. Supports single scenario (string) or array of scenarios.

### Changed
- Tenant management scenarios: `set_telegram_bot_token`; menu uses `get_tenant_status` and `get_telegram_bot_status` by bot_id.

### Fixed
- General system improvements and bug fixes (incl. ai_rag_service: `ai_token` for action `save_embedding` is now optional when `generate_embedding=false`).

### Technical Improvements
- Unified Telegram action naming; single public bot sync — `sync_telegram_bot`.

## [1.1.2] - 2026-02-08

### ⚠️ BREAKING CHANGES
- **Tenant configuration structure:** The `tg_bot.yaml` file in the tenant root has been replaced by a `bots/` folder containing bot configs. Telegram bot config is now stored in `bots/telegram.yaml`. The `bots/` folder can hold configs for different bots (e.g. `telegram.yaml`, `whatsapp.yaml`).

### Changed
- Documentation updated and improved: section structure, navigation, and wording
- Hub structure reworked: tenant_hub and the bot management service (formerly referred to as «bot hub»); bot management is now centralized in the Telegram service (telegram_bot_manager)

### Technical Improvements
- Tenant hub refactoring: action handlers extracted (actions), GitHub sync logic unified, domain modules renamed (utils → domain, TenantDataManager → TenantRepository)

## [1.1.1] - 2026-02-04

### Changed
- Documentation: quick start now uses system tenants (no GitHub); public tenants as optional block
- Configuration: system tenants boundary set to 99 (`max_system_tenant_id: 99` in `config/settings.yaml`), 100+ are public
- When `github_url` is not set, no errors are shown, sync is skipped, system works only with system tenants
- Tenant 1 (master bot): scenario rework — language selection support (i18n), improved and lighter UX, documentation improved

### Fixed
- General system improvements and minor fixes

### Technical Improvements
- Backup system: simplified backup management with DB type separation into folders (sqlite/, postgresql/), added compression (gzip for SQLite, pg_dump -Z 9 for PostgreSQL), unified formats between utility and plugin

## [1.1.0] - 2026-02-02

### Added
- In the actions guide (ACTION_GUIDE): extension actions (from plugins in the extensions folder) are marked with ⭐ in the table of contents and section headers, with a short note about extensions
- Documentation now describes extension actions (from the extensions folder)

### Changed
- General documentation improvements
- Deployment guide (DEPLOYMENT.md) fully updated for the Core Manager utility

### Technical Improvements
- Deployment utility fully reworked: replaced with Core Manager (`tools/core_manager`). Full bilingual support (EN/RU), optimized structure and logic, improved UI/UX, self-update refined. Deployment guide updated to match the new utility

## [1.0.3] - 2026-01-21

### Added

- Added AI models guide in English (`docs/en/AI_MODELS_GUIDE.md`)
- Added complete English version of documentation — all main guides available in `docs/en/`
- All configuration files and code comments translated to English

### Technical Improvements

- Created `extensions` level for plugins — allows easily adding additional plugins to extend platform functionality, which are not overwritten during updates
- Updated plugin documentation — added description of extension system and usage rules

## [1.0.2] - 2026-01-16

### ⚠️ BREAKING CHANGES

- **Placeholders: Renaming modifier `time` → `seconds`** — modifier renamed for clarity and consistency. Functionality unchanged, but syntax changed: use `{duration|seconds}` instead of `{duration|time}` in all scenarios
- **Placeholders: Renaming PostgreSQL formats `date_postgres`/`datetime_postgres` → `pg_date`/`pg_datetime`** — formats renamed for brevity. Update usage: `{timestamp|format:pg_date}` instead of `{timestamp|format:date_postgres}`, `{timestamp|format:pg_datetime}` instead of `{timestamp|format:datetime_postgres}`

### Added

- **Placeholders: Support for literal values in quotes** — now can use values directly in placeholders without passing through dictionary: `{'hello'|upper}`, `{'1d 2w'|seconds}`, `{'100'|+50}`. Supports single and double quotes with escaping (`'it\'s'`, `"say \"hi\""`)
- **Placeholders: `shift` modifier for date shifting** — new modifier for working with dates in PostgreSQL style: `{created|shift:+1 day}`, `{created|shift:+1 year 2 months}`, `{created|shift:-2 hours}`. Supports all date formats (PostgreSQL, standard, ISO, timestamp), correctly handles months/years and month edges (e.g., Jan 31 + 1 month = Feb 29 in leap year)
- **Placeholders: Modifiers for rounding dates to period start** — new modifiers for rounding dates to start of various periods: `to_date` (start of day), `to_hour` (start of hour), `to_minute` (start of minute), `to_second` (start of second), `to_week` (start of week - Monday), `to_month` (start of month), `to_year` (start of year). All return ISO format (`YYYY-MM-DD HH:MM:SS`). Examples: `{created|to_date}`, `{created|to_month|format:date}`

## [1.0.1] - 2026-01-15

### Fixed
- `get_tenants_list`: All tenant ID lists (`tenant_ids`, `public_tenant_ids`, `system_tenant_ids`) now returned sorted in ascending order

### Technical Improvements
- Simplified Docker management utility (`docker/compose`) — removed environment specification requirement for most commands, direct work with containers by name (e.g., `dc logs app-test`, `dc start app-test`), improved `logs` command with tail and follow support by default (last 100 lines + follow)

## [1.0.0] - 2025-12-31

### 🎉 Version 1.0.0 Release

Platform reached stable state and ready for full production use. During development from version 0.4.0 to 1.0.0 platform underwent significant improvements in all key aspects.

### Architecture and Infrastructure

- **PostgreSQL Migration** — transition from SQLite to PostgreSQL for improved performance, scalability and data storage reliability
- **Telegram Webhooks** — webhook support instead of polling with automatic SSL certificate generation
- **Deployment System** — deployment automation via GitHub Actions, deployment management utility with DB migration, backup and versioning support
- **Automatic Backups** — background DB backup service with configurable interval and automatic rotation
- **Database Access Control Views** — DB-level access control system via PostgreSQL views
- **GitHub Webhooks** — automatic tenant synchronization on repository changes

### AI and RAG (Retrieval-Augmented Generation)

- **Vector Storage** — integration with pgvector for PostgreSQL, support for 1024-dimensional vector embeddings
- **HNSW Index** — optimized vector search even on large data volumes
- **RAG Actions** — `save_embedding`, `search_embedding`, `get_recent_chunks`, `delete_embedding` for working with vector storage
- **RAG Integration in Completion** — `rag_chunks` parameter for automatic context formation from vector search
- **Migration to Polza.ai** — transition from OpenRouter to universal AI provider with extended pricing and modality support

### Scenarios and Actions

- **Unified Storage Actions** — unified action set for working with Tenant Storage and User Storage (get/set/delete)
- **Async Actions** — support for background execution of long operations (e.g., LLM requests) with waiting via `wait_for_action`
- **Scheduled Scenarios** — scenario launch on schedule via cron expressions
- **Dynamic Keyboards** — `build_keyboard` action for creating keyboards from arrays with templates
- **Centralized Validation** — unified validation system for all action input parameters with structured errors
- **Automatic Type Conversion** — automatic parameter type conversion when needed
- **Caching System** — unified caching utility for all critical data (bots, tenants, scenarios, users)

### Events and Triggers

- **New Event Types** — group member events (`member_joined`, `member_left`), payment events (`pre_checkout_query`, `payment_successful`)
- **Improved Conditions** — support for `$name` marker for fields in conditions, modifiers for placeholders (`exists`, `is_null`, `code`, `keys`, `expand`)
- **Placeholders** — extended placeholder system with support for complex data structures, dot notation and array element access

### Data Storage

- **Tenant Storage** — tenant attribute storage (key-value) with support for complex structures (JSON objects, arrays, nested structures)
- **User Storage** — user data storage for storing user settings and data
- **Storage Search** — `get_users_by_storage_value` action for finding users by storage values

### Payments and Invoices

- **invoice_service Service** — complete action set for working with invoices: creation, sending, payment confirmation/rejection, getting information, cancellation
- **Payment Processing** — automatic processing of `pre_checkout_query` and `payment_successful` events for working with Telegram Stars

### Performance and Reliability Improvements

- **Parallel Processing** — bots can process incoming events in parallel
- **Synchronization Optimization** — improved bot and tenant synchronization performance
- **Improved Error Handling** — structured error codes for all actions with fields `code`, `message`, `details`
- **Test Environment** — separate test environment for checking changes before production rollout

### Documentation

- **Extended Documentation** — created guides for AI models, storage, scenarios, events, usage examples
- **Quick Start** — separate guide for new users
- **Usage Examples** — practical examples working with RAG, payments, storage and other features

