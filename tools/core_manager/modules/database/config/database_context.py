"""Database context - unified configuration object."""

from pathlib import Path
from typing import Dict, Any


class DatabaseContext:
    """Unified context for database operations with all configuration."""
    
    def __init__(self, project_root: Path, database_config: Dict[str, Any], docker_compose_config: Dict[str, Any], 
                 environment: str, deployment_mode: str):
        self.project_root = Path(project_root)
        self.database_config = database_config
        self.docker_compose_config = docker_compose_config
        self.environment = environment
        self.deployment_mode = deployment_mode
        
        # Paths from database config
        self.db_config_path = database_config["db_config_path"]
        self.settings_path = database_config["settings_path"]
        self.backup_dir = database_config["backup_dir"]
        self.models_path = database_config.get("models_path", "")
        self.view_operations_path = database_config.get("view_operations_path", "")
    
    def is_docker_mode(self) -> bool:
        """Check if running in Docker deployment mode."""
        return self.deployment_mode == "docker"
    
    def is_test_environment(self) -> bool:
        """Check if running in test environment."""
        return self.environment == "test"
    
    def get_backup_dir(self) -> Path:
        """Return base backup directory path."""
        path = self.project_root / self.backup_dir
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_backup_dir_for_type(self, db_type: str) -> Path:
        """Return backup directory for given db type."""
        path = self.project_root / self.backup_dir / db_type
        path.mkdir(parents=True, exist_ok=True)
        return path
