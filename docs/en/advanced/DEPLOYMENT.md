# 🚀 Deployment System

Unified self-sufficient system for deployment management, server updates, and DB migrations.

## 📋 Contents

- [Quick Start](#quick-start)
- [Core Operations](#core-operations)
  - [Server Update](#server-update)
  - [Repository Deployment](#repository-deployment)
  - [Database Operations](#database-operations)
  - [Docker Image Rollback](#docker-image-rollback)
  - [Old Image Cleanup](#old-image-cleanup)
- [Configuration](#configuration)
- [Versioning](#versioning)
- [Docker](#docker)
- [Graceful Shutdown](#graceful-shutdown-during-updates)
- [Webhook Setup](#webhook-setup)
  - [GitHub Webhooks](#github-webhooks)
  - [Telegram Webhooks](#telegram-webhooks)
- [Database Access Management](#database-access-management)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
python tools/deployment/deployment_manager.py
```

**Menu:**
1. 🚀 Repository Deployment
2. 🔄 Server Update
3. 🗄️ Database Operations
4. ⏪ Docker Image Rollback
5. 🧹 Old Image Cleanup

---

## Core Operations

### 🔄 Server Update

Automated update process from GitHub:

1. Environment detection (test/prod)
2. Branch cloning from repository
3. Version detection from git tag
4. File and DB backup
5. File update by presets
6. DB migrations (universal + specific)
7. Update `config/.version`
8. Docker image build with versioning
9. **Container restart with graceful shutdown** (see [Graceful Shutdown](#graceful-shutdown-during-updates))
10. `dc` command installation

**Exclusions:** 
- `config/settings.yaml` - manually configured on server
- `config/tenant/` - tenant configurations not updated
- `config/.version` - local version file on server
- PostgreSQL configuration files (if added to `custom_exclude`):
  - `docker/postgresql.test.conf` - PostgreSQL settings for test environment
  - `docker/postgresql.prod.conf` - PostgreSQL settings for prod environment
  - `docker/pg_hba.test.conf` - authentication settings for test environment
  - `docker/pg_hba.prod.conf` - authentication settings for prod environment

**Important:** PostgreSQL configuration files can be excluded from updates via `custom_exclude` in `tools/deployment/config.yaml`. This preserves local settings (memory, authentication) between updates. If files are not excluded, they will be updated with repository versions during each server update.

### 🚀 Repository Deployment

Deploy code to external repositories (Core, Tenant):
- Version selection from CHANGELOG.md
- File filtering by presets
- Branch and commit creation
- Automatic Merge Request creation

### 🗄️ Database Operations

**Universal Migrations:**
- Automatic schema change detection
- Table and column creation/deletion
- Data type changes
- Index recreation
- JSON field validation

**Specific Migrations:**
- Versioned scripts in `tools/deployment/migrations/vX.Y.Z/`
- DB backup and restoration

### ⏪ Docker Image Rollback

Rollback to previous image version (prod only):
- View available versions
- Select version for rollback
- Confirmation and execution

### 🧹 Old Image Cleanup

Remove unused and old Docker image versions:
- Clean dangling images (unused intermediate images)
- Remove old image versions (keep last N versions)
- Show freed space
- Available for test and prod environments

---

## Configuration

**File:** `tools/deployment/config.yaml`

**Main Settings:**
- `server_update.repository` - repository and branches
- `server_update.deployment.presets` - file filtering rules
- `server_update.deployment.custom_exclude` - files excluded from updates
- `repositories` - external repositories for deployment
- `migration_settings` - migration settings

**Excluding Files from Updates:**

Files specified in `server_update.deployment.custom_exclude` are not updated during server updates. This preserves local settings between updates.

**Exclusion Examples:**
- `config/settings.yaml` - global application settings
- `config/.version` - local version file
- `docker/postgresql.*.conf` - PostgreSQL configuration (memory, performance settings)
- `docker/pg_hba.*.conf` - PostgreSQL authentication settings

**Important:** If PostgreSQL configuration files are not excluded, they will be updated with repository versions during each update, which may result in loss of local settings (e.g., memory settings for test/prod environments).

---

## Versioning

Version is stored in `config/.version`:
```yaml
version: "0.18.0"
release: false  # true for release versions
```

Determined from git tag. Updated automatically after successful deployment.

---

## Docker

**Management via `docker/compose` (`dc` command):**
```bash
dc start        # Start containers
dc stop         # Stop
dc logs         # View logs
dc sv status    # Supervisor process status
dc sv restart   # Restart process
dc stats        # Resource usage
dc install      # Install dc command
```

**Main Commands:**
- `dc start/stop/restart` - container management
- `dc down` - stop and remove containers
- `dc up [service]` - start containers
- `dc logs [service]` - view logs
- `dc shell [service]` - open shell in container
- `dc sv [status|restart|stop|start|logs] [proc]` - Supervisor management
- `dc resources set [service] --cpus X --memory Y` - configure resources

**Global Docker Compose Configuration:**

The `dc` command uses compose files from the global directory `~/.docker-compose/`:
- Files are automatically copied there during server updates
- This allows using one `dc` command for different environments on one server
- **Important:** PostgreSQL configuration files (`postgresql.*.conf`, `pg_hba.*.conf`) are also copied to the global directory during updates

**Source Files (in repository):**
- `docker/docker-compose.yml` - base
- `docker/docker-compose.test.yml` - test environment
- `docker/docker-compose.prod.yml` - prod environment
- `docker/docker-compose.override.yml` - local settings (not in git)
- `docker/postgresql.test.conf` / `docker/postgresql.prod.conf` - PostgreSQL configuration
- `docker/pg_hba.test.conf` / `docker/pg_hba.prod.conf` - PostgreSQL authentication settings

**Where to Change Settings:**

- **For local server changes:** edit files in `~/.docker-compose/` (not overwritten during updates if added to `custom_exclude`)
- **For repository changes:** edit files in `docker/` and commit to repository (will be copied to global directory on next update)

**Features:**
- Prod: `app` service, `app` container (code in image for rollback)
- Test: `app-test` service, `app-test` container (code via volume)
- Dev: `app` service, `app` container (code via volume, for local development)
- Prod and Test have different service names for simultaneous execution on one server
- Prod images are automatically versioned during build
- Old versions can be cleaned via deployment menu (option 5)

---

## Graceful Shutdown During Updates

System ensures proper application shutdown during server updates.

### How It Works

During server update (menu option 2), the following process occurs:

1. **Container Stop** (`docker-compose stop`)
   - Docker sends SIGTERM to container
   - Container gets up to **15 seconds** (`stop_grace_period`) for proper shutdown
   - If application finishes earlier, container stops immediately (doesn't wait full 15 seconds)

2. **Signal Processing in Supervisor**
   - Supervisor (PID 1) receives SIGTERM
   - Forwards signal to child process (Python application)
   - Waits up to **10 seconds** (`stopwaitsecs`) before forced stop

3. **Application Graceful Shutdown**
   - Application receives SIGTERM and starts graceful shutdown
   - Background task completion (up to 2 seconds)
   - DI-container shutdown (up to 3 seconds)
   - Total timeout calculated as sum of `di_container_timeout + background_tasks_timeout`

4. **New Container Start**
   - After stop, new container starts with updated image
   - Uses `--force-recreate` to recreate container

### Timeout Settings

**Docker Compose** (`docker/docker-compose.yml`):
- `stop_grace_period: 15s` - maximum wait time for container shutdown

**Supervisor** (`docker/supervisord.conf`):
- `stopsignal=TERM` - stop signal (SIGTERM)
- `stopwaitsecs=10` - wait time before SIGKILL
- `killasgroup=true` - terminate entire process group
- `stopasgroup=true` - stop entire process group

**Shutdown Settings** (in `config/settings.yaml`):
- `global.shutdown.di_container_timeout: 5.0s` - DI-container shutdown time (all plugins)
- `global.shutdown.plugin_timeout: 3.0s` - standard plugin shutdown time
- `global.shutdown.background_tasks_timeout: 2.0s` - background task completion time

All settings can be changed in `config/settings.yaml` to adapt to specific environment.

---

## Webhook Setup

### GitHub Webhooks

For automatic tenant configuration synchronization on repository changes, GitHub webhook setup is required.

#### Step 1: Determine Webhook URL

Webhook URL depends on environment and server configuration:

- **Production:** `https://your-server-ip:443/webhooks/github`
- **Test:** `https://your-server-ip:8443/webhooks/github`

**Important:** 
- Replace `your-server-ip` with your server's IP address or domain
- Ensure port is accessible externally (check firewall settings)
- Uses HTTPS with self-signed certificate (automatically generated)
- Ports 443 (prod) and 8443 (test) are allowed by Telegram for webhooks

#### Step 2: Generate Secret

Generate secure secret for webhook validation:

```bash
# Generate random secret (32 characters)
openssl rand -hex 32
```

#### Step 3: Configure Environment Variable

Set secret in environment variable on server:

```bash
# In Docker Compose (add to environment section)
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
```

Or in `.env` file (if used):
```
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
```

#### Step 4: Configure Webhook in GitHub

1. Go to repository on GitHub
2. Open **Settings** → **Webhooks** → **Add webhook**
3. Fill form:
   - **Payload URL:** `https://your-server-ip:443/webhooks/github` (prod) or `https://your-server-ip:8443/webhooks/github` (test)
   - **Content type:** `application/json`
   - **Secret:** paste same secret used in `GITHUB_WEBHOOK_SECRET`
   - **SSL verification:** 
     - For **HTTPS with valid certificate**: enable (default)
     - For **HTTPS with self-signed certificate**: disable (used in system)
   - **Which events would you like to trigger this webhook?:** select **Just the push event**
4. Click **Add webhook**

#### Step 5: Enable Webhooks in Settings

In `config/settings.yaml` or via environment variables:

```yaml
tenant_hub:
  use_webhooks: true  # Enable GitHub webhooks
```

#### Step 6: Verify Operation

1. Ensure application is running and `http_api_service` is enabled
2. Make test commit to repository
3. Check application logs — should see webhook receipt message
4. In GitHub under Webhooks → your webhook → Recent Deliveries you can see delivery status

---

### Telegram Webhooks

For using webhooks instead of polling to receive Telegram updates, external server URL setup is required.

#### Step 1: Configure External URL

In `config/settings.yaml` or via environment variables:

```yaml
http_server:
  port: 8443  # For test environment (or 443 for prod)
  external_url: "https://your-server-ip:8443"  # External IP or server domain
  # For prod environment:
  # port: 443
  # external_url: "https://your-server-ip:443"
  # Or for domain:
  # external_url: "https://example.com:443"
```

**Important:**
- URL must be accessible from internet (not localhost, not 127.0.0.1)
- Must support HTTPS (Telegram requires HTTPS for webhooks)
- **Ports:** Telegram only allows ports 80, 88, 443, or 8443
  - **Recommended:** 443 for prod, 8443 for test
- Can use IP address directly: `https://123.45.67.89:8443`
- Or domain: `https://example.com:443`

#### Step 2: Enable Webhooks

In `config/settings.yaml`:

```yaml
bot_hub:
  use_webhooks: true  # Enable Telegram webhooks
```

#### Step 3: Automatic SSL Certificate Generation

When webhooks are enabled, the system automatically:
- Generates self-signed SSL certificate for specified `external_url`
- Configures HTTPS in `http_server`
- Uploads certificate to Telegram when setting webhook

**Requirements:**
- `cryptography` library must be installed (added to `requirements.txt`)
- `external_url` must be specified in `http_server` settings

#### Step 4: Verify Operation

1. Ensure `http_api_service` is enabled (`enabled: true`)
2. Start application
3. When starting bot via `start_bot` or `sync_bot_config`, webhook will be automatically set
4. Check logs — should see webhook setup message
5. Send message to bot via Telegram — should be received and processed

#### Features

- **Automatic Setup:** Webhook is set automatically on bot start if `use_webhooks: true`
- **Self-Signed Certificate:** Generated automatically on each restart (not saved)
- **Mode Switching:** Can switch between webhooks and polling via `use_webhooks` setting
- **Global Setting:** Setting applies to all bots simultaneously (either all webhooks or all polling)

---

## Features for Home PC / Local Server

If running application on home PC or local server:

**Accessibility Issues:**
- **Provider's Public IP** may be inaccessible externally due to:
  - **NAT/router** — blocks incoming connections, needs port forwarding
  - **CGNAT (Carrier-Grade NAT)** — provider uses shared IP for multiple clients, direct access impossible
  - **Dynamic IP** — IP address may change on reconnection
  - **Provider Firewall** — may block incoming connections on non-standard ports

**Solutions:**

1. **Port Forwarding on Router:**
   - Configure port forwarding 443 (prod) or 8443 (test) to your PC
   - Find PC local IP: `ipconfig` (Windows) or `ifconfig` (Linux)
   - In router settings: External Port 443 → Internal IP your PC:443 (prod)
   - Or: External Port 8443 → Internal IP your PC:8443 (test)
   - Use provider's public IP in webhook URL

2. **Accessibility Check:**
   ```bash
   # From another computer or via online service (e.g., canyouseeme.org)
   # Check if your port is accessible externally
   ```

3. **Development Alternatives:**
   - **ngrok** — creates tunnel: `ngrok http 8443` → get public URL
   - **Cloudflare Tunnel** — free tunnel with HTTPS
   - **Local Development** — use polling instead of webhooks (`use_webhooks: false`)

**Recommendations:**
- For **production** use VPS/cloud server with public IP
- For **testing** on home PC use ngrok or temporarily disable webhooks (polling)

---

## Database Access Management

System automatically creates PostgreSQL views for DB-level access control. This allows DB administrators to configure user access to data via `view_access` table.

### How It Works

1. **Automatic View Creation** — on system start, views are automatically created for all tables with `tenant_id`:
   - Simple views (direct `tenant_id`): `v_tenant`, `v_tenant_storage`, `v_user_storage`, `v_tenant_user`, `v_bot`, `v_scenario`, `v_invoice`, etc.
   - Complex views (via joins): `v_bot_command`, `v_scenario_trigger`, `v_scenario_step`, `v_scenario_step_transition`, etc.

2. **`view_access` Table** — contains access settings:
   - `login` — PostgreSQL username (for `current_user`)
   - `tenant_id` — Tenant ID (0 = access to all tenants)

3. **Data Filtering** — views automatically filter data based on `current_user` and `view_access` entries

### Access Setup

#### Step 1: Create PostgreSQL User

```sql
-- Create read-only user
CREATE USER readonly_user WITH PASSWORD 'your_secure_password';

-- Or user with limited rights
CREATE USER analyst_user WITH PASSWORD 'your_secure_password';
```

**Important:** System automatically creates two roles:
- **`user`** — SELECT rights on all views (for regular users with limited access via filtering)
- **`admin`** — SELECT rights on all tables and views, INSERT/UPDATE/DELETE rights on `view_access` table (for DB administrators — extended access)

**Note:** Admin doesn't need to manage other tables (INSERT/UPDATE/DELETE) as platform does this. Database is operational, so admin only manages access via `view_access` table.

New users just need to be assigned appropriate role.

#### Step 2: Assign Role to New Users

```sql
-- For regular users (access only via views with filtering)
GRANT "user" TO readonly_user;
GRANT "user" TO analyst_user;

-- For DB administrators (SELECT on all tables/views, manage access via view_access)
GRANT admin TO admin_user;
```

#### Step 3: Configure Access in view_access Table

```sql
-- Access to specific tenant (ID = 1)
INSERT INTO view_access (login, tenant_id) VALUES ('readonly_user', 1);

-- Access to all tenants (tenant_id = 0)
INSERT INTO view_access (login, tenant_id) VALUES ('readonly_user', 0);

-- Access to multiple tenants
INSERT INTO view_access (login, tenant_id) VALUES 
    ('analyst_user', 1),
    ('analyst_user', 2),
    ('analyst_user', 3);
```

#### Step 4: Verify Operation

```sql
-- Connect as user
SET ROLE readonly_user;

-- Check access
SELECT * FROM v_tenant;  -- Should see only permitted tenants
SELECT * FROM v_tenant_storage;  -- Only data from permitted tenants
```

### Features

- **PostgreSQL Only** — views created only for PostgreSQL, ignored for SQLite
- **Automatic Update** — views recreated on each system start (`CREATE OR REPLACE VIEW`)
- **Automatic Roles** — system automatically creates two roles:
  - `user` — SELECT rights on all views (for regular users with limited access)
  - `admin` — SELECT rights on all tables and views, INSERT/UPDATE/DELETE rights on `view_access` table (for DB administrators — manage access)
- **Security** — users see only data permitted via `view_access`
- **Flexibility** — can configure access to specific tenants or all (tenant_id = 0)

### Usage Examples

**Analyst with Access to Multiple Tenants:**
```sql
-- Create user
CREATE USER analyst WITH PASSWORD 'secure_password';

-- Assign user role (automatically gives SELECT rights on all views)
GRANT "user" TO analyst;

-- Configure access
INSERT INTO view_access (login, tenant_id) VALUES 
    ('analyst', 1),
    ('analyst', 2);
```

**Read-Only User for Monitoring:**
```sql
-- Create user
CREATE USER monitor WITH PASSWORD 'secure_password';

-- Assign user role (automatically gives SELECT rights on all views)
GRANT "user" TO monitor;

-- Access to all tenants (read-only)
INSERT INTO view_access (login, tenant_id) VALUES ('monitor', 0);
```

**DB Administrator (Manage Access):**
```sql
-- Create user
CREATE USER db_admin WITH PASSWORD 'secure_password';

-- Assign admin role (SELECT on all tables/views, manage view_access)
GRANT admin TO db_admin;

-- Now admin can manage access:
-- INSERT INTO view_access (login, tenant_id) VALUES ('new_user', 1);
-- UPDATE view_access SET tenant_id = 2 WHERE login = 'user' AND tenant_id = 1;
-- DELETE FROM view_access WHERE login = 'old_user';
```

---

## Troubleshooting

### GitHub Webhooks

**Webhook not working:**
- Check port is accessible externally (firewall, Docker port mapping, router port forwarding)
- Ensure `http_api_service` is enabled (`enabled: true` in settings)
- Check application logs for errors
- Ensure secret matches in GitHub and environment variable
- For home PC: check port forwarding and port accessibility externally

**Error 401 (Invalid signature):**
- Check secret in GitHub matches `GITHUB_WEBHOOK_SECRET`
- Ensure secret has no extra spaces or characters

**Webhook arrives but sync doesn't happen:**
- Check application logs — files may not be related to tenant configurations
- Ensure `use_webhooks: true` in `tenant_hub` settings

**GitHub shows delivery error:**
- Check URL is accessible from internet (not localhost, not 127.0.0.1)
- For self-signed certificate: disable SSL verification in GitHub webhook settings
- Check delivery logs in GitHub (Webhooks → your webhook → Recent Deliveries) for error details

### Telegram Webhooks

**Webhook not setting:**
- Check `external_url` is specified in `http_server` settings (not empty string)
- Ensure `http_api_service` is enabled (`enabled: true`)
- Check application logs for errors during webhook setup
- Ensure `cryptography` library is installed

**Error generating SSL certificate:**
- Check `cryptography` library is installed: `pip install cryptography`
- Ensure `external_url` contains valid IP address or domain
- Check application logs for error details

**Webhook set but updates not arriving:**
- Check port is accessible externally (firewall, Docker port mapping)
- Ensure port matches Telegram requirements (80, 88, 443, or 8443)
- Ensure `external_url` points to real external IP/domain (not localhost)
- Check application logs — should see webhook receipt messages
- In Telegram Bot API can check webhook status via `getWebhookInfo`

**Error "Webhook can be set up only on ports 80, 88, 443 or 8443":**
- Ensure `http_server.external_url` specifies one of allowed ports
- For test environment use port 8443
- For prod environment use port 443
- Update port forwarding in `docker-compose.test.yml` (8443) and `docker-compose.prod.yml` (443)

**Error 401 (Invalid secret token):**
- This is normal on system restart — secret token is regenerated
- Ensure webhook was reinstalled after restart
- Check application logs for details
