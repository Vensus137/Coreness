"""Models helper - get table class map without DI container."""

import importlib
from typing import Any, Dict


def get_table_class_map(models_path: str) -> Dict[str, Any]:
    """Get table name -> model class map by importing models module.
    
    models_path: Python import path (e.g. plugins.utilities.core.database_manager.models).
    """
    module = importlib.import_module(models_path)
    Base = getattr(module, "Base", None)
    if Base is None:
        raise AttributeError(f"Module {models_path} has no Base")

    table_class_map = {}
    for table_name, table in Base.metadata.tables.items():
        for model_class in Base.registry._class_registry.values():
            if hasattr(model_class, "__tablename__") and model_class.__tablename__ == table_name:
                table_class_map[table_name] = model_class
                break
    return table_class_map
