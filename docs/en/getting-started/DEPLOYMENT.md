---
title: Deployment Guide
description: Complete guide to installing and deploying Coreness. Docker, PostgreSQL, webhook setup and server updates.
keywords: coreness deployment, docker deployment, postgresql setup, webhook configuration
---

# Deployment

Short guide for deploying the platform from scratch.

## Getting Started

1. **Get the repository:**
   - Via Git: `git clone <repository_URL>`, then go to the project directory (`cd <repo_name>`).
   - Or download an archive from GitHub (Code → Download ZIP), extract it, and open the directory in your terminal.
2. After cloning, the project runs **with default settings (SQLite)**. For proper environment setup, database, and future updates, use the **Core Manager** utility.

## Running Core Manager

```bash
python tools/core_manager/core_manager.py
```

On first run the utility will ask for:

1. **Environment** (test / prod)
   - `test` — testing (separate ports and containers, e.g. postgres-test, port 5433).
   - `prod` — production (postgres, port 5432).

2. **Deployment mode** (docker / native)
   - `docker` — containers (Docker + docker-compose): utility starts and updates containers, config in `~/.coreness`, `dc` command from `docker/compose`.
   - `native` — no containers: connect to DB via your settings (e.g. localhost), after update install deps from project root `requirements.txt`. Handy for local dev and Windows.

3. **Interface language** (English / Русский). You can change it anytime via menu option 4.

Settings are saved in `config/.version`.

**Platform:** On Windows, **native** mode is recommended — docker compose on Windows often causes issues and the utility is not designed for that; native works fine. On Linux and servers you can use **docker**.

## Utility Menu

```
==================================================
                   CORE MANAGER
==================================================

  Version: 1.1.0-beta2-10
  Environment: test
  Deployment mode: docker

--------------------------------------------------

1. Update system
2. Database operations
3. Update utility
4. Change language
0. Exit

--------------------------------------------------
Select action:
```

- **1. Update system** — update platform from repository (choose version, backup, update files, DB migration, restart containers in docker mode).
- **2. Database operations** — migrations, create backup, restore from backup.
- **3. Update utility** — self-update Core Manager.
- **4. Change language** — switch interface language.

## Main Operations

### System Update

Update from GitHub: choose version → backup → update files → offer DB migration → restart containers (docker) or install dependencies from `requirements.txt` (native). **Settings and version file** (`config/settings.yaml`, `config/.version`) **are not overwritten**, so your settings are preserved.

### Database Operations

- **Migrations** — bring DB schema in line with models (SQLite and PostgreSQL).
- **Backup** — SQLite: file copy; PostgreSQL: via pg_dump in container or local client.
- **Restore** — from a chosen backup.

### Self-Update

Menu option 3: fetch new Core Manager version from GitHub, update utility files, and restart.

## Configuration

Main config: `tools/core_manager/config.yaml`.

Relevant sections:
- `version_file.path` — path to version file (`config/.version`)
- `system_update` — repository URL, branch, file list for updates
- `docker_compose.global_config_dir` — Docker config directory (`~/.coreness`)
- `database.backup_dir` — DB backup directory (`data/backups`)

Version file `config/.version` stores: `version`, `language`, `environment`, `deployment_mode`.

## Support

If you have questions or run into issues: check this guide and the utility output; if needed, contact the developer or open an issue in the project repository.
