"""Database configuration loader."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


class DatabaseConfig:
    """Loads and manages database configuration from YAML files."""
    
    def __init__(self, project_root: Path, db_config_path: str, settings_path: str):
        self.project_root = Path(project_root)
        self.db_config_path = db_config_path
        self.settings_path = settings_path
        self._cached_config = None
    
    def load(self) -> Dict[str, Any]:
        """Load database config from db_config_path and settings_path."""
        if self._cached_config is not None:
            return self._cached_config
        
        base_path = self.project_root / self.db_config_path
        if not base_path.exists():
            raise FileNotFoundError(f"Database config not found: {base_path}")
        
        with open(base_path, "r", encoding="utf-8") as f:
            base_config = yaml.safe_load(f)
        
        db_preset = base_config["settings"]["database_preset"]["default"]
        db_config = base_config["settings"]["database"][db_preset].copy()
        
        # Override from settings.yaml
        settings_path = self.project_root / self.settings_path
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = yaml.safe_load(f) or {}
            if "database_manager" in settings:
                dm = settings["database_manager"]
                db_preset = dm.get("database_preset", db_preset)
                if "database" in dm and db_preset in dm["database"]:
                    db_config.update(dm["database"][db_preset])
        
        self._cached_config = {"preset": db_preset, "config": db_config}
        return self._cached_config
    
    def get_preset(self) -> str:
        """Get database preset (sqlite/postgresql)."""
        return self.load()["preset"]
    
    def get_config(self) -> Dict[str, Any]:
        """Get database configuration dict."""
        return self.load()["config"]
