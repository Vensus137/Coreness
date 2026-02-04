"""Database backup handler - refactored."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from ..config.database_context import DatabaseContext
from ..connection.database_connection import DatabaseConnection
from ..docker.compose_finder import get_postgres_service_name_from_config
from ..docker.docker_operations import DockerPostgresOperations
from ..migration.output import MigrationFormatter


def run_backup(project_root: Path, config: dict, translator) -> bool:
    """Create database backup."""
    formatter = MigrationFormatter()
    formatter.print_section(translator.get("database.section_create_backup"))
    
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        
        if db_type == "sqlite":
            return _backup_sqlite(db_conn, backup_dir, backup_name, formatter, translator)
        elif db_type == "postgresql":
            return _backup_postgresql(db_conn, context, backup_dir, backup_name, formatter, translator)
        
        return False
        
    except Exception as e:
        formatter.print_error(f"{translator.get('database.backup_failed')}: {e}")
        return False


def _backup_sqlite(db_conn, backup_dir: Path, backup_name: str, formatter, translator) -> bool:
    """Backup SQLite database with gzip compression."""
    import gzip
    
    sqlite_path = Path(db_conn.db_path)
    if not sqlite_path.exists():
        formatter.print_error(translator.get("database.sqlite_not_found"))
        return False
    
    backup_file = backup_dir / f"{backup_name}.db.gz"
    formatter.print_info(translator.get("database.creating_backup"))
    
    # Compress SQLite file with maximum compression level
    with open(sqlite_path, 'rb') as f_in:
        with gzip.open(backup_file, 'wb', compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    size_mb = backup_file.stat().st_size / (1024 * 1024)
    formatter.print_success(
        f"✓ {translator.get('database.backup_created')}: {backup_file.name} ({size_mb:.2f} MB)"
    )
    return True


def _backup_postgresql(db_conn, context: DatabaseContext, backup_dir: Path, backup_name: str, formatter, translator) -> bool:
    """Backup PostgreSQL database."""
    backup_file = backup_dir / f"{backup_name}.dump"
    conn_info = db_conn.get_connection_info()
    
    formatter.print_info(translator.get("database.creating_backup"))
    
    if context.is_docker_mode():
        db_service = get_postgres_service_name_from_config(context.project_root, context.environment, context.docker_compose_config)
        
        if db_service:
            formatter.print_info(translator.get("database.docker_service_using", service=db_service))
            
            docker_ops = DockerPostgresOperations(context.project_root, context.docker_compose_config, translator)
            
            if docker_ops.backup(service_name=db_service, environment=context.environment, database=conn_info["database"],
                                username=conn_info["username"], backup_file=backup_file, formatter=formatter):
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                formatter.print_success(
                    f"✓ {translator.get('database.backup_created')}: {backup_file.name} ({size_mb:.2f} MB)"
                )
                return True
            
            formatter.print_warning(translator.get("database.docker_backup_failed_fallback"))
        else:
            formatter.print_warning(
                f"{translator.get('database.docker_service_not_found')} (environment: {context.environment}). "
                f"{translator.get('database.docker_service_start_hint')}"
            )
    
    if _try_native_pg_dump(conn_info, backup_file, formatter, translator):
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        formatter.print_success(
            f"✓ {translator.get('database.backup_created')}: {backup_file.name} ({size_mb:.2f} MB)"
        )
        return True
    
    return False


def _try_native_pg_dump(conn_info: dict, backup_file: Path, formatter, translator) -> bool:
    """Try to create backup using native pg_dump with compression."""
    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = conn_info.get("password", "")
        
        cmd = [
            "pg_dump",
            "-h", str(conn_info.get("host", "localhost")),
            "-p", str(conn_info.get("port", 5432)),
            "-U", conn_info.get("username", "postgres"),
            "-d", conn_info.get("database", "core_db"),
            "-F", "c",  # Custom format (already compressed)
            "-Z", "9",  # Maximum compression level
            "-f", str(backup_file),
        ]
        
        subprocess.run(cmd, env=env, check=True, capture_output=True, timeout=300)
        return backup_file.exists() and backup_file.stat().st_size > 0
        
    except subprocess.CalledProcessError as e:
        formatter.print_error(f"pg_dump failed: {e.stderr.decode()}")
        return False
    except FileNotFoundError:
        formatter.print_error(translator.get("database.pg_dump_not_found"))
        return False
    except Exception:
        return False
