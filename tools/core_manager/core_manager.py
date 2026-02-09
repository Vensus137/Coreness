#!/usr/bin/env python3
"""Core Manager - Main entry point for platform management."""

import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Critical deps: exit on failure. Non-critical: warn only.
_CRITICAL_DEPS = [("pyyaml", "yaml")]
_OPTIONAL_DEPS = [
    ("python-dotenv", "dotenv", ".env will not be loaded"),
    ("colorama", "colorama", "colors may not work on Windows"),
]


def _install_package(package: str) -> bool:
    """Install package via pip. Returns True if successful."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode == 0
    except Exception:
        return False


def _ensure_dependencies() -> None:
    """Force-install dependencies. Exit only if critical ones fail."""
    for pip_name, import_name in _CRITICAL_DEPS:
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {pip_name}...")
            if not _install_package(pip_name):
                print(f"Error: {pip_name} is required. Install failed. Run: pip install {pip_name}")
                sys.exit(1)
            try:
                __import__(import_name)
            except ImportError:
                print(f"Error: {pip_name} is required. Install failed. Run: pip install {pip_name}")
                sys.exit(1)

    for item in _OPTIONAL_DEPS:
        pip_name, import_name = item[0], item[1]
        msg = item[2] if len(item) > 2 else ""
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {pip_name}...")
            if not _install_package(pip_name):
                extra = f" {msg}." if msg else ""
                print(f"Warning: {pip_name} not installed.{extra} Run: pip install {pip_name}")


_ensure_dependencies()

from tools.core_manager.modules.core.config import ConfigManager
from tools.core_manager.modules.core.restart_manager import RestartManager
from tools.core_manager.modules.i18n.translator import Translator
from tools.core_manager.modules.core.version_file import VersionFile
from tools.core_manager.modules.setup.setup_manager import SetupManager
from tools.core_manager.modules.ui.menu import Menu
from tools.core_manager.modules.update.self_updater import SelfUpdater
from tools.core_manager.modules.update.update_handler import UpdateHandler
from tools.core_manager.modules.update.system_update_handler import SystemUpdateHandler
from tools.core_manager.modules.database.database_manager import DatabaseManager
from tools.core_manager.modules.ui.colors import Colors


class CoreManager:
    """Main application class."""

    def __init__(self):
        self.utility_root = Path(__file__).resolve().parent
        self.project_root = PROJECT_ROOT

        self.config = ConfigManager(self.utility_root)
        self.version_file = VersionFile(
            self.utility_root,
            self.project_root,
            self.config.get_version_file_path()
        )
        
        # Load version file into cache
        self.version_file.load()
        
        # Initialize translator with language from cache or default
        language = self.version_file.get("language") or self.config.get_default_language()
        self.translator = Translator(self.utility_root, language)
        
        # Initialize modules
        self.setup = SetupManager(self.translator, self.version_file, self.config)
        self.menu = Menu(self.translator, self.version_file)
        
        # Initialize update system (single RestartManager for restart+resume and markers)
        self.restart_manager = RestartManager(self.utility_root, self.project_root)
        self.self_updater = SelfUpdater(
            self.utility_root,
            self.project_root,
            self.config.get("self_update", {}),
            self.config,
            self.version_file,
            self.translator,
            self.restart_manager,
        )
        self.update_handler = UpdateHandler(self.self_updater, self.translator)
        self.system_update_handler = SystemUpdateHandler(
            self.utility_root,
            self.project_root,
            self.config,
            self.translator,
            self.version_file,
            self.restart_manager,
        )

        # Initialize database manager (pass version_file for environment/deployment_mode in DB config)
        self.database_manager = DatabaseManager(
            self.project_root,
            self.translator,
            self.config.get("database", {}),
            self.version_file,
            self.config.get("docker_compose", {}),
        )

        self.restart_manager.register_resume(
            self.system_update_handler.RESUME_UPDATE_ARG,
            self.system_update_handler.handle_resume,
        )
        self.restart_manager.register_resume(
            self.self_updater.RESUME_SELF_UPDATE_ARG,
            self.self_updater.handle_resume,
        )

    def initialize(self) -> None:
        """Perform initial setup checks and configuration."""
        print(f"\n{Colors.info(self.translator.get('init.loading_config'))}")
        print(Colors.info(self.translator.get("init.checking_settings")))
        self.setup.ensure_all()

    def run(self) -> None:
        """Main application loop."""
        try:
            self.initialize()

            if self.restart_manager.handle_resume(sys.argv):
                pass

            while True:
                choice = self.menu.display()

                if choice == "1":
                    # System update
                    self.system_update_handler.run()

                elif choice == "2":
                    # Database migrations
                    self.database_manager.run()

                elif choice == "3":
                    # Self-update - delegate to update handler
                    self.update_handler.handle_update()

                elif choice == "4":
                    # Change language
                    self.setup.change_language()
                    self.menu.t = self.translator
                    self.setup.t = self.translator

                elif choice == "0":
                    # Exit
                    print(Colors.info(f"\n{self.translator.get('menu.goodbye')}"))
                    break

        except KeyboardInterrupt:
            print(Colors.warning(f"\n\n{self.translator.get('messages.interrupted')}"))
            sys.exit(0)
        except Exception as e:
            print(Colors.error(f"\nError: {e}"))
            sys.exit(1)


def main():
    """Entry point. Update module may use --resume-update to land back in update flow after restart."""
    app = CoreManager()
    app.run()


if __name__ == "__main__":
    main()
