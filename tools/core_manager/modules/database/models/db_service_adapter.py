"""Lightweight db_service adapter - same interface as database_manager, no DI."""

from contextlib import contextmanager
from typing import Any, Dict, Generator, Tuple, TYPE_CHECKING

from sqlalchemy.orm import sessionmaker

from .models_helper import get_table_class_map
from .views_helper import drop_all_views, create_all_views

if TYPE_CHECKING:
    from ..connection.database_connection import DatabaseConnection


class DbServiceAdapter:
    """Adapter providing database_manager interface without DI container."""

    def __init__(self, connection: "DatabaseConnection", config: Dict[str, Any]):
        self.connection = connection
        self.config = config
        self._table_class_map = None
        self._session_factory = None

    @property
    def engine(self):
        """Return SQLAlchemy engine."""
        return self.connection.engine

    def get_table_class_map(self) -> Dict[str, Any]:
        """Return table name -> model class map."""
        if self._table_class_map is None:
            path = self.config.get("models_path", "plugins/utilities/core/database_manager/models")
            import_path = path.replace("/", ".").replace("\\", ".")
            self._table_class_map = get_table_class_map(import_path)
        return self._table_class_map

    def get_database_config(self) -> Dict[str, Any]:
        """Return database config dict."""
        return {
            'type': self.connection.db_type,
            'url': self.connection.get_connection_info().get('url', ''),
            **self.connection.get_connection_info()
        }

    def drop_all_views(self) -> bool:
        """Drop all PostgreSQL views."""
        path = self.config.get("view_operations_path")
        if not path:
            raise ValueError("view_operations_path not set in database config")
        return drop_all_views(
            self.connection.engine,
            self.connection.db_type,
            path.replace("/", ".").replace("\\", "."),
        )

    def create_all_views(self) -> bool:
        """Create all PostgreSQL views."""
        path = self.config.get("view_operations_path")
        if not path:
            raise ValueError("view_operations_path not set in database config")
        return create_all_views(
            self.connection.engine,
            self.connection.db_type,
            path.replace("/", ".").replace("\\", "."),
        )

    @contextmanager
    def session_scope(self) -> Generator[Tuple[Any, Any], None, None]:
        """Context manager for session (yields session, repos placeholder)."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.connection.engine)
        session = self._session_factory()
        try:
            yield (session, None)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
