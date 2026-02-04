"""Database restore handler - refactored."""

import gzip
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ...ui.dialogs import confirm
from ..config.database_context import DatabaseContext
from ..connection.database_connection import DatabaseConnection
from ..docker.compose_finder import get_postgres_service_name_from_config
from ..docker.docker_operations import DockerPostgresOperations
from ..migration.output import MigrationFormatter


def run_restore(project_root: Path, config: dict, translator) -> bool:
    """Restore database from backup."""
    formatter = MigrationFormatter()
    formatter.print_section(translator.get("database.section_restore_backup"))
    
    try:
        context = DatabaseContext(
            project_root=project_root, database_config=config, docker_compose_config=config.get("docker_compose", {}),
            environment=config.get("environment", "prod"), deployment_mode=config.get("deployment_mode", "docker")
        )
        
        formatter.print_info(
            translator.get("database.env_mode_info", env=context.environment, mode=context.deployment_mode)
        )
        
        db_conn = DatabaseConnection(context)
        db_conn.connect()
        
        db_type = db_conn.db_type
        backup_dir = context.get_backup_dir_for_type(db_type)
        
        if not backup_dir.exists():
            formatter.print_error(
                translator.get("database.no_backups_for_type", db_type=db_type, path=str(backup_dir))
            )
            return False
        
        backups = sorted(backup_dir.glob("backup_*"), reverse=True)
        if not backups:
            formatter.print_error(
                translator.get("database.no_backups_for_type", db_type=db_type, path=str(backup_dir))
            )
            return False
        
        formatter.print_info(translator.get("database.available_backups"))
        for i, backup in enumerate(backups[:10], 1):
            size_mb = backup.stat().st_size / (1024 * 1024)
            print(f"  {i}. {backup.name} ({size_mb:.2f} MB)")
        print(f"  0. {translator.get('messages.cancel')}")
        print()
        
        choice = input(f"{translator.get('database.select_backup')}: ").strip()
        if choice == "0":
            formatter.print_info(translator.get("messages.cancelled"))
            return False
        
        try:
            index = int(choice) - 1
            if index < 0 or index >= min(10, len(backups)):
                formatter.print_error(translator.get("messages.invalid_choice"))
                return False
            selected = backups[index]
        except ValueError:
            formatter.print_error(translator.get("messages.invalid_choice"))
            return False
        
        print()
        formatter.print_warning(f"⚠ {translator.get('database.restore_warning')}: {selected.name}")
        if not confirm(translator.get("database.confirm_restore"), default=False, translator=translator):
            formatter.print_info(translator.get("messages.cancelled"))
            return False
        
        return _do_restore_from_file(db_conn, context, selected, formatter, translator)
        
    except Exception as e:
        formatter.print_error(f"{translator.get('database.restore_failed')}: {e}")
        return False


def run_restore_latest(project_root: Path, config: dict, translator) -> bool:
    """Restore database from latest backup (by mtime). Non-interactive."""
    formatter = MigrationFormatter()
    
    try:
        context = DatabaseContext(
            project_root=project_root, database_config=config, docker_compose_config=config.get("docker_compose", {}),
            environment=config.get("environment", "prod"), deployment_mode=config.get("deployment_mode", "docker")
        )
        
        db_conn = DatabaseConnection(context)
        db_conn.connect()
        
        db_type = db_conn.db_type
        backup_dir = context.get_backup_dir_for_type(db_type)
        
        if not backup_dir.exists():
            formatter.print_error(
                translator.get("database.no_backups_for_type", db_type=db_type, path=str(backup_dir))
            )
            return False
        
        backups = sorted(backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            formatter.print_error(
                translator.get("database.no_backups_for_type", db_type=db_type, path=str(backup_dir))
            )
            return False
        
        selected = backups[0]
        formatter.print_info(translator.get("database.restoring_from_latest", name=selected.name))
        
        return _do_restore_from_file(db_conn, context, selected, formatter, translator)
        
    except Exception as e:
        formatter.print_error(f"{translator.get('database.restore_failed')}: {e}")
        return False


def _do_restore_from_file(db_conn, context: DatabaseContext, backup_path: Path, formatter, translator) -> bool:
    """Restore database from a specific backup file."""
    db_type = db_conn.db_type
    
    if db_type == "sqlite":
        return _restore_sqlite(db_conn, backup_path, formatter, translator)
    elif db_type == "postgresql":
        return _restore_postgresql(db_conn, context, backup_path, formatter, translator)
    
    return False


def _restore_sqlite(db_conn, backup_path: Path, formatter, translator) -> bool:
    """Restore SQLite database from compressed backup."""
    sqlite_path = Path(db_conn.db_path)
    temp_backup = None
    
    # Create temporary backup of current database
    if sqlite_path.exists():
        temp_backup = sqlite_path.parent / f"core.db.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(sqlite_path, temp_backup)
        formatter.print_info(f"{translator.get('database.current_backed_up')}: {temp_backup.name}")
    
    formatter.print_info(translator.get("database.restoring"))
    
    try:
        # Check if backup is compressed
        if backup_path.suffix == '.gz':
            # Decompress gzip backup
            with gzip.open(backup_path, 'rb') as f_in:
                with open(sqlite_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # Direct copy for uncompressed backups
            shutil.copy2(backup_path, sqlite_path)
        
        # If successful, delete temporary backup
        if temp_backup and temp_backup.exists():
            temp_backup.unlink()
        
        formatter.print_success(f"✓ {translator.get('database.restore_success')}: {backup_path.name}")
        return True
        
    except Exception as e:
        # On error, restore from temporary backup if it exists
        if temp_backup and temp_backup.exists():
            shutil.copy2(temp_backup, sqlite_path)
            formatter.print_error(f"Restore failed, rolled back to previous state: {e}")
        raise


def _restore_postgresql(db_conn, context: DatabaseContext, backup_path: Path, formatter, translator) -> bool:
    """Restore PostgreSQL database."""
    conn_info = db_conn.get_connection_info()
    formatter.print_info(translator.get("database.restoring"))
    
    if context.is_docker_mode():
        db_service = get_postgres_service_name_from_config(context.project_root, context.environment, context.docker_compose_config)
        
        if db_service:
            formatter.print_info(translator.get("database.docker_service_using", service=db_service))
            
            docker_ops = DockerPostgresOperations(context.project_root, context.docker_compose_config, translator)
            
            if docker_ops.restore(service_name=db_service, environment=context.environment, database=conn_info["database"],
                                 username=conn_info["username"], backup_path=backup_path, formatter=formatter):
                return True
            
            formatter.print_warning(translator.get("database.docker_restore_failed_fallback"))
        else:
            formatter.print_warning(
                f"{translator.get('database.docker_service_not_found')} (environment: {context.environment}). "
                f"{translator.get('database.docker_service_start_hint')}"
            )
    
    return _try_native_pg_restore(conn_info, backup_path, formatter, translator)


def _try_native_pg_restore(conn_info: dict, backup_path: Path, formatter, translator) -> bool:
    """Try to restore using native pg_restore."""
    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = conn_info.get("password", "")
        
        cmd = [
            "pg_restore",
            "-h", str(conn_info.get("host", "localhost")),
            "-p", str(conn_info.get("port", 5432)),
            "-U", conn_info.get("username", "postgres"),
            "-d", conn_info.get("database", "core_db"),
            "--clean",
            "--if-exists",
            "--disable-triggers",
            "--no-owner",
            "--no-acl",
            str(backup_path),
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            formatter.print_success(f"✓ {translator.get('database.restore_success')}: {backup_path.name}")
            return True
        
        stderr = result.stderr or ""
        if "errors ignored on restore" in stderr:
            formatter.print_warning(
                f"⚠ {translator.get('database.restore_completed_with_warnings')}: {backup_path.name}\n{stderr}"
            )
            return True
        
        formatter.print_error(f"pg_restore failed: {stderr}")
        return False
        
    except FileNotFoundError:
        formatter.print_error(translator.get("database.pg_restore_not_found"))
        return False
    except Exception:
        return False
