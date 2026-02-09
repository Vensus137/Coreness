"""System update handler - orchestrates full platform update flow."""

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..core.dependencies import ensure_dependencies
from ..core.restart_manager import RestartManager
from ..database.docker.compose_finder import (
    find_compose_file,
    get_compose_cwd,
    postgres_container_exists,
)
from ..database.migration_handler import MigrationHandler
from ..ui.colors import Colors
from ..ui.dialogs import confirm
from .version_fetcher import get_available_versions, get_latest_version
from .platform_updater import PlatformUpdater


class SystemUpdateHandler:
    """Orchestrates system update: deps, version select, update files, migration offer."""

    RESUME_UPDATE_ARG = "--resume-update"

    def __init__(self, utility_root: Path, project_root: Path, config_manager, translator, version_file, restart_manager):
        self.utility_root = Path(utility_root)
        self.project_root = Path(project_root)
        self.config = config_manager
        self.t = translator
        self.version_file = version_file
        self.restart_manager = restart_manager

    def _get_current_version(self) -> str:
        """Get current version from version file or git."""
        v = self.version_file.get("version")
        if v:
            return v
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().lstrip("v")
        except Exception:
            pass
        return "unknown"

    def _install_native_dependencies(self) -> bool:
        """Install dependencies from project root for native deployment."""
        req_file = self.project_root / "requirements.txt"
        if not req_file.exists():
            return True
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _resolve_path(self, path_str: str) -> Path:
        """Resolve path with ~ to home directory."""
        s = path_str.strip()
        if s.startswith("~"):
            return Path.home() / s[1:].lstrip("/\\")
        return Path(s)

    def _install_dc_command(self) -> bool:
        """Install dc command from docker/compose to PATH (docker deployment only, Unix)."""
        if sys.platform == "win32":
            return True
        dc_config = self.config.get("docker_compose", {})
        dc_install = dc_config.get("dc_install", {})
        script_rel = dc_config.get("dc_script_path", "docker/compose")
        script_path = self.project_root / script_rel
        if not script_path.exists():
            return True

        root_path = dc_install.get("root_path", "/usr/local/bin")
        user_path = dc_install.get("user_path", "~/.local/bin")
        try:
            if os.geteuid() == 0:
                install_dir = self._resolve_path(root_path)
            else:
                install_dir = self._resolve_path(user_path)
                install_dir.mkdir(parents=True, exist_ok=True)
        except (AttributeError, OSError):
            install_dir = self._resolve_path(user_path)
            install_dir.mkdir(parents=True, exist_ok=True)

        target = install_dir / "dc"
        try:
            shutil.copy2(script_path, target)
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return True
        except Exception:
            return False

    def _get_compose_services(self, compose_path: Path, cwd: Optional[Path] = None) -> list:
        """Return list of service names from compose file. cwd must match compose project for correct project name."""
        try:
            work_dir = cwd if cwd is not None else self.project_root
            result = subprocess.run(
                ["docker", "compose", "-f", str(compose_path), "config", "--services"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            return [s.strip() for s in result.stdout.strip().splitlines() if s.strip()]
        except Exception:
            return []

    def _copy_compose_to_global_with_path_fix(self, source: Path, target: Path, global_config_dir: Path) -> None:
        """Copy compose file to global config dir and fix paths (context, volumes, supervisord) for running from global dir."""
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()
        project_root_str = str(self.project_root)
        content = re.sub(r"context:\s*\.\.", f"context: {project_root_str}", content)
        content = re.sub(r"-\s+\.\.:/workspace", f"- {project_root_str}:/workspace", content)
        content = re.sub(r"\./supervisord\.conf", str(global_config_dir / "supervisord.conf"), content)
        content = re.sub(r"-\s+\.\./([^:]+):", rf"- {project_root_str}/\1:", content)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

    def _ensure_docker_config_in_global_dir(self, environment: str) -> None:
        """Copy docker compose and related files from project docker/ to global_config_dir so we always work from there."""
        dc_config = self.config.get("docker_compose", {})
        global_config_dir_str = dc_config.get("global_config_dir", "~/.coreness")
        global_config_dir = Path(os.path.expanduser(global_config_dir_str))
        docker_dir = self.project_root / "docker"
        if not docker_dir.exists():
            return
        global_config_dir.mkdir(parents=True, exist_ok=True)
        base_source = docker_dir / "docker-compose.yml"
        if base_source.exists():
            self._copy_compose_to_global_with_path_fix(
                base_source, global_config_dir / "docker-compose.yml", global_config_dir
            )
        config_files = dc_config.get("config_files", {}) or {}
        env_filename = config_files.get(environment) or f"docker-compose.{environment}.yml"
        env_source = docker_dir / env_filename
        if not env_source.exists():
            env_source = docker_dir / f"docker-compose.{environment}.yml"
        if env_source.exists():
            self._copy_compose_to_global_with_path_fix(
                env_source, global_config_dir / env_filename, global_config_dir
            )
        # Override is not copied from repo: it is generated from dc_config by the dc command.
        for name in ("supervisord.conf", "init-pgvector.sql"):
            src = docker_dir / name
            if src.exists() and src.is_file():
                shutil.copy2(src, global_config_dir / name)
        # PostgreSQL configs: copy only if target does not exist so we do not overwrite tuned settings.
        for pattern in ("postgresql.*.conf", "pg_hba.*.conf"):
            for src in docker_dir.glob(pattern):
                if src.is_file():
                    dst = global_config_dir / src.name
                    if not dst.exists():
                        shutil.copy2(src, dst)

    def _restart_docker_containers(self, environment: str) -> bool:
        """Build and restart non-postgres containers for current environment only. Postgres is handled by database module."""
        dc_config = self.config.get("docker_compose", {})
        self._ensure_docker_config_in_global_dir(environment)
        compose_path = find_compose_file(self.project_root, environment, dc_config)
        if not compose_path:
            return True

        cwd = get_compose_cwd(compose_path, dc_config)
        # Always use base + all environment files to see all services (no orphan warnings)
        compose_files = []
        base_compose = cwd / "docker-compose.yml"
        if base_compose.exists():
            compose_files.append(str(base_compose))
        
        # Add all environment-specific files from config
        config_files = dc_config.get("config_files", {}) or {}
        for env_name, env_file in config_files.items():
            env_compose = cwd / env_file
            if env_compose.exists():
                compose_files.append(str(env_compose))
        
        # Override files are managed by docker compose automatically, no need to specify
        compose_f_args = [arg for f in compose_files for arg in ("-f", f)]

        skip_list = dc_config.get("skip_restart_services", {}) or {}
        skip_services = skip_list.get(environment, []) if isinstance(skip_list, dict) else []

        try:
            all_services = self._get_compose_services(compose_path, cwd)
            if not all_services:
                return True

            to_restart = [s for s in all_services if s not in skip_services]
            if not to_restart:
                return True

            services_str = ", ".join(to_restart)
            print(Colors.info(self.t.get("system_update.restart_services_for_env", env=environment, services=services_str)))
            print(Colors.info(self.t.get("system_update.build_then_up")))

            result = subprocess.run(
                ["docker", "compose"] + compose_f_args + ["build"] + to_restart,
                cwd=cwd,
                capture_output=False,
                timeout=600,
            )
            if result.returncode != 0:
                print(Colors.warning(self.t.get("system_update.build_failed_manual")))
                return False

            subprocess.run(
                ["docker", "compose"] + compose_f_args + ["stop"] + to_restart,
                cwd=cwd,
                capture_output=True,
                timeout=60,
            )
            subprocess.run(
                ["docker", "compose"] + compose_f_args + ["rm", "-f"] + to_restart,
                cwd=cwd,
                capture_output=True,
                timeout=30,
            )

            result = subprocess.run(
                ["docker", "compose"] + compose_f_args + ["up", "-d", "--no-deps"] + to_restart,
                cwd=cwd,
                capture_output=False,
                timeout=120,
            )
            if result.returncode != 0:
                print(Colors.warning(self.t.get("system_update.up_failed_manual")))
                return False

            for service in to_restart:
                print(Colors.success(f"  {service}: {self.t.get('system_update.container_restarted')}"))
            return True
        except subprocess.TimeoutExpired:
            print(Colors.warning(self.t.get("system_update.restart_failed_manual")))
            return False
        except Exception as e:
            print(Colors.warning(f"{self.t.get('system_update.restart_failed_manual')} {e}"))
            return False

    def _restart_to_resume_update(self) -> None:
        """Restart utility; RestartManager writes marker and new process runs migration prompt and docker restart."""
        self.restart_manager.restart_with_resume(self.RESUME_UPDATE_ARG)

    def handle_resume(self, argv: list) -> None:
        """Run resume steps (migration prompt default N, then docker restart if needed). Called by RestartManager after marker/argv check."""
        while self.RESUME_UPDATE_ARG in argv:
            argv.remove(self.RESUME_UPDATE_ARG)
        self._run_resume_steps()

    def _run_resume_steps(self) -> None:
        """After restart: install dc, restart non-postgres containers, then migration prompt. Postgres is not started here; migration module handles it."""
        deployment_mode = self.version_file.get("deployment_mode", "docker")
        environment = self.version_file.get("environment", "prod")
        db_config = dict(self.config.get("database", {}))
        db_config.setdefault("environment", environment)
        db_config.setdefault("deployment_mode", deployment_mode)

        if deployment_mode == "docker":
            print(Colors.info(self.t.get("system_update.installing_dc")))
            if self._install_dc_command():
                print(Colors.success(f"✓ {self.t.get('system_update.dc_installed')}"))
            else:
                print(Colors.warning(self.t.get("system_update.dc_install_skipped")))

            print(Colors.info(self.t.get("system_update.restart_containers")))
            if self._restart_docker_containers(environment):
                print(Colors.success(f"✓ {self.t.get('system_update.containers_restarted')}"))

            dc_config = self.config.get("docker_compose", {})
            ran_init_migration = False
            if postgres_container_exists(self.project_root, environment, dc_config):
                ran_init_migration = False
            else:
                migration_handler = MigrationHandler(self.project_root, self.t, db_config)
                migration_handler.run(skip_confirm=True)
                ran_init_migration = True

            if not ran_init_migration and confirm(self.t.get("system_update.run_migration_prompt"), default=False, translator=self.t):
                migration_handler = MigrationHandler(self.project_root, self.t, db_config)
                migration_success = migration_handler.run(skip_confirm=True)
                if not migration_success:
                    print(Colors.warning(f"\n{self.t.get('system_update.migration_failed_containers_not_restarted')}"))
        elif deployment_mode == "native":
            if confirm(self.t.get("system_update.run_migration_prompt"), default=False, translator=self.t):
                migration_handler = MigrationHandler(self.project_root, self.t, db_config)
                migration_success = migration_handler.run(skip_confirm=True)
                if not migration_success:
                    print(Colors.warning(f"\n{self.t.get('system_update.migration_failed_containers_not_restarted')}"))

    def run(self) -> None:
        """Execute full system update flow."""
        try:
            # 1. Check dependencies
            deps = self.config.get("system_update.dependencies", [])
            if deps and not ensure_dependencies(deps, self.t):
                print(Colors.error(self.t.get("system_update.dependencies_failed")))
                return

            repo_url = self.config.get("system_update.repository.url")
            if not repo_url:
                print(Colors.error(self.t.get("system_update.repo_not_configured")))
                return

            token = self.config.get_system_update_token()

            # 2. Fetch versions
            print(Colors.info(f"\n{self.t.get('system_update.checking')}"))
            available = get_available_versions(repo_url, token, limit=5)
            if not available:
                print(Colors.error(self.t.get("system_update.no_versions")))
                if not token:
                    token_env = self.config.get("system_update.token_env", "GITHUB_TOKEN")
                    print(Colors.error(self.t.get("system_update.repo_not_found", token_env=token_env)))
                return

            latest = get_latest_version(repo_url, token) or available[0]["version"]
            current = self._get_current_version()

            # 3. Display versions (always offer update; current is highlighted in the list below)
            print(f"{self.t.get('system_update.current')}: {Colors.version(current)}")
            print(f"{self.t.get('system_update.latest')}: {Colors.version(latest or 'unknown')}")

            # 4. Version selection (show repository source)
            print(f"\n{self.t.get('system_update.repository')}: {Colors.info(repo_url)}")
            print(f"{self.t.get('system_update.select_version')}:")
            for i, ver_info in enumerate(available, 1):
                ver = ver_info["version"]
                # Use release name if available, otherwise use version (tag name)
                display_name = ver_info.get("name", ver)
                marker = " (latest)" if ver == latest else ""
                marker += " (current)" if ver == current else ""
                if ver_info.get("prerelease"):
                    marker += f" ({self.t.get('system_update.prerelease_label')})"
                print(f"  {i}. {display_name}{marker}")
            print(f"  0. {self.t.get('system_update.cancel_option')}")

            choice = input(f"\n{self.t.get('messages.choice')} (0-{len(available)}): ").strip()
            if choice == "0":
                print(Colors.info(self.t.get("messages.cancelled")))
                return

            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(available):
                    print(Colors.error(self.t.get("messages.invalid_choice")))
                    return
                selected_version = available[idx]["version"]
            except ValueError:
                print(Colors.error(self.t.get("messages.invalid_choice")))
                return

            # 5. Confirm
            environment = self.version_file.get("environment", "prod")
            deployment_mode = self.version_file.get("deployment_mode", "docker")
            env_display = self.t.get(f"environments.{environment}")
            dep_display = self.t.get(f"deployment_modes.{deployment_mode}")

            print(f"\n{self.t.get('system_update.environment')}: {env_display}")
            print(f"{self.t.get('system_update.deployment_mode')}: {dep_display}")

            if not confirm(self.t.get("system_update.confirm_update", version=selected_version), default=True, translator=self.t):
                print(Colors.info(self.t.get("messages.cancelled")))
                return

            # 6. Perform update
            updater = PlatformUpdater(self.project_root, self.config.config)
            backup_path: Optional[Path] = None

            try:
                # Clone
                print(Colors.info(self.t.get("system_update.cloning")))
                repo_path = updater.clone_repository(token)
                if not repo_path:
                    print(Colors.error(self.t.get("system_update.clone_failed")))
                    return

                # Checkout tag
                print(Colors.info(self.t.get("system_update.checkout_version", version=selected_version)))
                if not updater.checkout_tag(repo_path, selected_version):
                    print(Colors.error(self.t.get("system_update.checkout_failed", version=selected_version)))
                    updater.cleanup()
                    return

                # Backup
                print(Colors.info(self.t.get("system_update.creating_backup")))
                backup_path = updater.backup_files()
                if not backup_path:
                    print(Colors.error(self.t.get("system_update.backup_failed")))
                    updater.cleanup()
                    return
                print(Colors.success(f"✓ {self.t.get('system_update.backup_created')}"))

                # Update files
                print(Colors.info(self.t.get("system_update.updating_files")))
                if not updater.update_files(repo_path):
                    print(Colors.error(self.t.get("system_update.file_update_failed")))
                    raise RuntimeError("File update failed")

                print(Colors.success(f"✓ {self.t.get('system_update.files_updated')}"))

                # Update version file
                print(Colors.info(self.t.get("system_update.updating_version_file")))
                self.version_file.set("version", selected_version)
                self.version_file.save()

                # Post-update: native only (Docker: dc install and container restart happen in resume)
                if deployment_mode == "native":
                    print(Colors.info(self.t.get("system_update.installing_dependencies")))
                    if self._install_native_dependencies():
                        print(Colors.success(f"✓ {self.t.get('system_update.dependencies_installed')}"))
                    else:
                        print(Colors.warning(self.t.get("system_update.dependencies_failed")))

                # Cleanup temp
                print(Colors.info(self.t.get("system_update.cleanup_temp")))
                updater.cleanup()

                # Remove backup on success
                updater.remove_backup(backup_path)
                backup_path = None

                # 7. Restart utility so new code is loaded; new process will offer migration (default N) and docker restart
                print(Colors.success(f"\n✓ {self.t.get('system_update.update_complete')}"))
                print(Colors.info(self.t.get("system_update.restarting_for_migration")))
                self._restart_to_resume_update()

            except Exception as e:
                print(Colors.error(f"\n{self.t.get('system_update.update_failed')}: {e}"))
                if backup_path and backup_path.exists():
                    print(Colors.info(self.t.get("system_update.restoring_backup")))
                    if updater.restore_backup(backup_path):
                        print(Colors.success(f"✓ {self.t.get('system_update.restored')}"))
                    updater.remove_backup(backup_path)
                updater.cleanup()

        except KeyboardInterrupt:
            print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
        except Exception as e:
            print(Colors.error(f"\n{self.t.get('system_update.update_failed')}: {e}"))
            import traceback
            traceback.print_exc()
