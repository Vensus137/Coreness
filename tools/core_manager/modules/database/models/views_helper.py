"""Views helper - delegates to view_operations via config path (no hardcoded imports)."""

import importlib
from typing import Callable, Optional


class _LogAdapter:
    """Adapter: log_func(string) -> logger.info/warning/error(msg)."""

    def __init__(self, log_func: Optional[Callable[[str], None]] = None):
        self._log = log_func or (lambda _: None)

    def info(self, msg: str) -> None:
        self._log(msg)

    def warning(self, msg: str) -> None:
        self._log(msg)

    def error(self, msg: str) -> None:
        self._log(msg)


def drop_all_views(engine, db_type: str, view_operations_path: str, log_func: Optional[Callable[[str], None]] = None) -> bool:
    """Drop all system views (PostgreSQL only). Uses ViewOperations from config path."""
    module = importlib.import_module(view_operations_path)
    ViewOperations = getattr(module, "ViewOperations")
    logger = _LogAdapter(log_func)
    view_ops = ViewOperations(engine, db_type, logger)
    return view_ops.drop_all_views()


def create_all_views(engine, db_type: str, view_operations_path: str, log_func: Optional[Callable[[str], None]] = None) -> bool:
    """Create all views (PostgreSQL only). Uses ViewOperations from config path."""
    module = importlib.import_module(view_operations_path)
    ViewOperations = getattr(module, "ViewOperations")
    logger = _LogAdapter(log_func)
    view_ops = ViewOperations(engine, db_type, logger)
    return view_ops.create_all_views()
