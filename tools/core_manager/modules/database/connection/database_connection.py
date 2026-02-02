"""Database connection manager - lightweight, no DI."""

import os
from pathlib import Path
from typing import Dict, Any

from ..config.database_config import DatabaseConfig
from ..config.database_context import DatabaseContext


def _running_inside_docker() -> bool:
    """Return True if process runs inside a Docker container."""
    return Path("/.dockerenv").exists()


class DatabaseConnection:
    """Manages SQLAlchemy database connection."""
    
    def __init__(self, context: DatabaseContext):
        self.context = context
        self.db_config = DatabaseConfig(
            context.project_root,
            context.db_config_path,
            context.settings_path
        )
        
        self._engine = None
        self._db_type = None
        self._db_path = None
        self._db_exists = False
    
    def _resolve_postgres_host_port(self, host: str, port_from_env: str = None) -> tuple:
        """Resolve host and port for PostgreSQL."""
        port = port_from_env
        if port is None:
            port = "5433" if self.context.is_test_environment() else "5432"
        else:
            port = str(port)
        
        # When running on host (not in container), Docker service names do not resolve
        if self.context.is_docker_mode() and not _running_inside_docker():
            docker_service_names = ("postgres-test", "postgres", "postgres-prod")
            if host in docker_service_names or (host and "postgres" in host.lower()):
                host = "127.0.0.1"
                port = "5433" if self.context.is_test_environment() else "5432"
        return host, port
    
    def _build_database_url(self) -> str:
        """Build SQLAlchemy database URL from config."""
        preset = self.db_config.get_preset()
        db = self.db_config.get_config()
        
        if preset == "sqlite":
            url = db.get("database_url", "sqlite:///data/core.db")
            if url.startswith("sqlite:///"):
                path = url[10:]
                if not Path(path).is_absolute():
                    path = self.context.project_root / path
                url = f"sqlite:///{path}"
            return url
        
        if preset == "postgresql":
            host = os.environ.get("POSTGRES_HOST", db.get("host", "localhost"))
            port_env = os.environ.get("POSTGRES_PORT")
            host, port = self._resolve_postgres_host_port(host, port_env)
            username = os.environ.get("POSTGRES_USER", db.get("username", "postgres"))
            password = os.environ.get("POSTGRES_PASSWORD", db.get("password", ""))
            database = os.environ.get("POSTGRES_DB", db.get("database", "core_db"))
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        raise ValueError(f"Unknown database preset: {preset}")
    
    def connect(self) -> None:
        """Create SQLAlchemy engine."""
        if self._engine is not None:
            return
        
        try:
            from sqlalchemy import create_engine
        except ImportError:
            raise ImportError("SQLAlchemy not installed. Run: pip install sqlalchemy")
        
        url = self._build_database_url()
        self._db_type = self.db_config.get_preset()
        self._engine = create_engine(url, echo=False, future=True)
        
        if self._db_type == "sqlite":
            self._db_path = self._engine.url.database
            self._db_exists = os.path.exists(self._db_path) if self._db_path else False
        else:
            try:
                from sqlalchemy import text
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                self._db_exists = True
            except Exception:
                self._db_exists = False
    
    @property
    def engine(self):
        """Return SQLAlchemy engine."""
        if self._engine is None:
            self.connect()
        return self._engine
    
    @property
    def db_type(self) -> str:
        """Return database type (sqlite/postgresql)."""
        if self._db_type is None:
            self.connect()
        return self._db_type
    
    @property
    def db_path(self) -> str:
        """Return database path (for SQLite)."""
        if self._db_path is None:
            self.connect()
        return self._db_path or ""
    
    @property
    def db_exists(self) -> bool:
        """Return True if database exists."""
        if self._db_type is None:
            self.connect()
        return self._db_exists
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Return connection info for backup/restore operations."""
        preset = self.db_config.get_preset()
        db = self.db_config.get_config()
        
        result = {"type": preset, "url": self._build_database_url()}
        
        if preset == "sqlite":
            result["db_path"] = self.db_path
        else:
            host = os.environ.get("POSTGRES_HOST", db.get("host", "localhost"))
            port_env = os.environ.get("POSTGRES_PORT")
            host, port = self._resolve_postgres_host_port(host, port_env)
            result["host"] = host
            result["port"] = int(port)
            result["database"] = os.environ.get("POSTGRES_DB", db.get("database", "core_db"))
            result["username"] = os.environ.get("POSTGRES_USER", db.get("username", "postgres"))
            result["password"] = os.environ.get("POSTGRES_PASSWORD", db.get("password", ""))
        
        return result
    
    @property
    def db_service(self):
        """Return lightweight db_service adapter."""
        from ..models.db_service_adapter import DbServiceAdapter
        temp_config = {
            "models_path": self.context.models_path,
            "view_operations_path": self.context.view_operations_path,
        }
        return DbServiceAdapter(self, temp_config)
    
    def cleanup(self) -> None:
        """Dispose engine."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
            self._db_type = None
            self._db_path = None
            self._db_exists = False
