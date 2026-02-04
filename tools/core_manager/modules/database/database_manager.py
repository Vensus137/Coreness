"""Database management module - entry point for all database operations."""

from pathlib import Path
from typing import List, Tuple, Callable, Dict, Any

from ..i18n.translator import Translator
from ..ui.colors import Colors
from .migration_handler import MigrationHandler
from .backup.backup_handler import run_backup
from .backup.restore_handler import run_restore, run_restore_latest


class DatabaseManager:
    """Manages database operations with modular structure for future expansion."""

    def __init__(self, project_root: Path, translator: Translator, config: Dict[str, Any], version_file, docker_compose_config: Dict[str, Any]):
        self.project_root = project_root
        self.translator = translator
        self.config = config
        self.version_file = version_file
        self.docker_compose_config = docker_compose_config
        # Pass self as config provider so MigrationHandler always gets fresh config
        self.migration_handler = MigrationHandler(project_root, translator, self)

    def _get_effective_config(self) -> Dict[str, Any]:
        """
        Build effective config by merging environment and deployment_mode from version_file.
        Always rebuilds to respect current version_file state (not cached).
        """
        effective = dict(self.config)
        effective.setdefault("environment", self.version_file.get("environment", "prod"))
        effective.setdefault("deployment_mode", self.version_file.get("deployment_mode", "docker"))
        # Add docker_compose config for compose file location
        effective["docker_compose"] = self.docker_compose_config
        return effective

    def get_menu_items(self) -> List[Tuple[str, str, Callable]]:
        """Get list of menu items (id, label, handler)."""
        return [
            ("1", self.translator.get("database.universal_migration"), self.migration_handler.run),
            ("2", self.translator.get("database.create_backup"), lambda: run_backup(self.project_root, self._get_effective_config(), self.translator)),
            ("3", self.translator.get("database.restore_backup"), lambda: run_restore(self.project_root, self._get_effective_config(), self.translator)),
        ]
    
    def run(self):
        """Run database management menu."""
        menu_items = self.get_menu_items()
        
        # If only one item, run it directly without submenu
        if len(menu_items) == 1:
            menu_items[0][2]()  # Call the handler
            return
        
        # Otherwise show submenu (for future expansion)
        while True:
            print("\n" + "="*60)
            print(Colors.bold(self.translator.get('database.menu_title').center(60)))
            print("="*60)
            print()
            
            for item_id, label, _ in menu_items:
                print(f"{item_id}. {label}")
            
            print(f"0. {self.translator.get('database.back')}")
            print()
            print("-" * 60)
            
            choice = input(f"\n{self.translator.get('database.select_action')}: ").strip()
            
            if choice == "0":
                break
            
            # Find and execute handler
            for item_id, _, handler in menu_items:
                if choice == item_id:
                    handler()
                    break
            else:
                print(Colors.error(f"✗ {self.translator.get('messages.invalid_choice')}"))
