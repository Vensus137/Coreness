import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# New import for finding bot.yaml
from pathlib import Path

import yaml

# Import formatters
from .formatters import ColoredFormatter, TimezoneFormatter


class Logger:
    """System logger for the project"""
    
    def __init__(self):
        """Logger initialization"""
        # Determine project root
        self.project_root = self._find_project_root(Path(__file__))
        
        # Path to global settings
        self.global_settings_path = self.project_root / 'config' / 'settings.yaml'
        
        # Load logger settings
        self.settings = self._load_logger_settings()
        
        # Cache main logger
        self._main_logger = None
    
    @staticmethod
    def _find_project_root(start_path: Path) -> Path:
        """Reliably determine project root"""
        # First check environment variable
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and os.path.exists(env_root):
            return Path(env_root)
        
        # Search for project root by presence of config/settings.yaml
        current_path = start_path.resolve()
        while current_path != current_path.parent:
            config_file = current_path / 'config' / 'settings.yaml'
            if config_file.exists():
                return current_path
            current_path = current_path.parent
        
        # If not found, return current directory
        return Path.cwd()
    
    # --- Helper conversions for safe settings merging ---
    def _to_bool(self, value, fallback: bool) -> bool:
        if value is None:
            return fallback
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", ""}:
                return False
        return fallback

    def _to_int(self, value, fallback: int) -> int:
        try:
            return int(value) if value is not None else fallback
        except Exception:
            return fallback

    def _to_str(self, value, fallback: str) -> str:
        try:
            return str(value) if value is not None else fallback
        except Exception:
            return fallback
    
    def _load_logger_settings(self) -> dict:
        """Read logger section from global settings"""
        # Load global settings
        global_settings = {}
        if self.global_settings_path.exists():
            try:
                with open(self.global_settings_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    global_settings = config.get('logger', {})
            except Exception:
                pass
        
        return global_settings

    def _deep_merge(self, base_dict: dict, override_dict: dict) -> dict:
        """Deep merge dictionaries: override_dict overrides base_dict"""
        result = base_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result

    def _load_logging_config(self) -> dict:
        """Load logging config"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

        if not os.path.exists(config_path):
            local_config = {}
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    config = yaml.safe_load(file)
                local_config = config.get('settings', {}) if config else {}
            except Exception:
                local_config = {}

        # Extract values and defaults from local config (plugins/.../config.yaml)
        level = local_config.get('level', {}).get('default', 'DEBUG')
        file_enabled = local_config.get('file_enabled', {}).get('default', True)
        file_path = local_config.get('file_path', {}).get('default', 'logs/core.log')
        max_file_size_mb = local_config.get('max_file_size_mb', {}).get('default', 10)
        backup_count = local_config.get('backup_count', {}).get('default', 5)
        local_console_enabled = local_config.get('console_enabled', {}).get('default', True)
        timezone = local_config.get('timezone', {}).get('default', 'Europe/Moscow')

        # Global overrides from preset settings (priority over local)
        global_logger_settings = self._load_logger_settings()

        # console_enabled: priority console_enabled, then local
        if 'console_enabled' in global_logger_settings:
            console_enabled = self._to_bool(global_logger_settings.get('console_enabled'), local_console_enabled)
        else:
            console_enabled = local_console_enabled

        # Other fields: take global if specified, with careful type conversion
        file_enabled = self._to_bool(global_logger_settings.get('file_enabled', file_enabled), file_enabled)
        level = self._to_str(global_logger_settings.get('level', level), level)
        file_path = self._to_str(global_logger_settings.get('file_path', file_path), file_path)
        max_file_size_mb = self._to_int(global_logger_settings.get('max_file_size_mb', max_file_size_mb), max_file_size_mb)
        backup_count = self._to_int(global_logger_settings.get('backup_count', backup_count), backup_count)
        timezone = self._to_str(global_logger_settings.get('timezone', timezone), timezone)

        return {
            'level': level,
            'file_enabled': file_enabled,
            'file_path': file_path,
            'max_file_size_mb': max_file_size_mb,
            'backup_count': backup_count,
            'console_enabled': console_enabled,
            'timezone': timezone
        }

    def setup_logger(self, name: str = "logger") -> logging.Logger:
        """Setup main logger"""
        # Setup main logger
        config = self._load_logging_config()
        level = config.get('level', 'DEBUG').upper()
        file_enabled = config.get('file_enabled', True)
        file_path = config.get('file_path', 'logs/core.log')
        max_file_size_mb = config.get('max_file_size_mb', 10)
        backup_count = config.get('backup_count', 5)
        buffer_size = config.get('buffer_size', 8192)
        console_enabled = config.get('console_enabled', True)

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Always DEBUG, filter on handlers

        # Clear existing handlers
        logger.handlers.clear()

        # Get timezone setting
        timezone = config.get('timezone', 'Europe/Moscow')
        
        # Create formatters
        # For file - formatter with correct timezone (without colors)
        file_formatter = TimezoneFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S", timezone=timezone)
        
        # For console - colored formatter with smart formatting
        console_formatter = ColoredFormatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S",
            use_colors=True,
            smart_format=True,
            timezone=timezone
        )

        # Create file handler
        if file_enabled:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create file handler with buffering
            if buffer_size > 0:
                # Use BufferingHandler for buffering
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                # Enable buffering at OS level
                import io
                buffered_handler = logging.StreamHandler(
                    io.TextIOWrapper(
                        io.BufferedWriter(
                            io.FileIO(file_path, 'ab'),
                            buffer_size=buffer_size
                        ),
                        encoding='utf-8'
                    )
                )
                file_handler = buffered_handler
            else:
                # Regular handler without buffering
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
            
            file_handler.setLevel(getattr(logging, level))
            file_handler.setFormatter(file_formatter)  # Without colors
            logger.addHandler(file_handler)

        # Create console handler
        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)  # With colors
            console_handler.setLevel(getattr(logging, level))  # Use same level as for file
            logger.addHandler(console_handler)

        return logger

    def get_logger(self, name: str) -> 'Logger':
        """Get logger for module"""
        # Create new instance of our Logger class
        logger_instance = Logger()
        # Use same internal logger with new name
        logger_instance._main_logger = self.setup_logger(name)
        # Set correct logger name
        logger_instance.set_logger_name(name)
        return logger_instance
    
    def _get_main_logger(self) -> logging.Logger:
        """Get cached main logger"""
        if self._main_logger is None:
            self._main_logger = self.setup_logger("logger")
        return self._main_logger
    
    def set_logger_name(self, new_name: str):
        """Change main logger name"""
        if self._main_logger is None:
            self._main_logger = self.setup_logger("logger")
        self._main_logger.name = new_name
    
    # Methods for compatibility with logging.Logger (for use in DI)
    def info(self, message: str):
        """Log info message"""
        self._get_main_logger().info(message)
    
    def debug(self, message: str):
        """Log debug message"""
        self._get_main_logger().debug(message)
    
    def warning(self, message: str):
        """Log warning message"""
        self._get_main_logger().warning(message)
    
    def error(self, message: str):
        """Log error message"""
        self._get_main_logger().error(message)
    
    def critical(self, message: str):
        """Log critical error message"""
        self._get_main_logger().critical(message)