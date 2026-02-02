"""Configuration management module."""

import os
import yaml
from pathlib import Path
from typing import Any


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, utility_root: Path | None = None, config_path: Path | None = None):
        if utility_root is None:
            utility_root = Path(__file__).resolve().parent.parent.parent  # core_manager dir
        
        self.utility_root = Path(utility_root)
        self.project_root = self.utility_root.parent.parent  # project root
        
        if config_path is None:
            config_path = utility_root / "config.yaml"
        
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        self._load_env()
        self._load_config()

    def _load_env(self) -> None:
        """Load .env from project root."""
        try:
            from dotenv import load_dotenv
            load_dotenv(self.project_root / ".env")
        except ImportError:
            pass

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path."""
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_available_languages(self) -> list[str]:
        """Get list of available languages."""
        return self.get("i18n.available_languages", ["en"])

    def get_default_language(self) -> str:
        """Get default language."""
        return self.get("i18n.default_language", "en")

    def get_available_environments(self) -> list[str]:
        """Get list of available environments."""
        return self.get("environments.available", ["test", "prod"])

    def get_default_environment(self) -> str:
        """Get default environment."""
        return self.get("environments.default", "prod")

    def get_available_deployment_modes(self) -> list[str]:
        """Get list of available deployment modes."""
        return self.get("deployment.available_modes", ["docker", "native"])

    def get_default_deployment_mode(self) -> str:
        """Get default deployment mode."""
        return self.get("deployment.default", "docker")

    def get_version_file_path(self) -> str:
        """Get path to version file (relative to project root)."""
        return self.get("version_file.path", "config/.version")

    def get_github_token(self) -> str:
        """Get GitHub token from env (loaded from .env). Returns expanded value."""
        token_env = self.get("self_update.token_env", "GITHUB_TOKEN")
        return os.environ.get(token_env, "")

    def get_system_update_token(self) -> str:
        """Get token for system update from env (same as GitHub token typically)."""
        token_env = self.get("system_update.token_env", "GITHUB_TOKEN")
        return os.environ.get(token_env, "")
