"""Update handler - manages self-update UI flow."""

from pathlib import Path
from ..ui.colors import Colors
from ..ui.dialogs import confirm
from .self_updater import SelfUpdater


class UpdateHandler:
    """Handles self-update user interface and flow."""

    def __init__(self, self_updater: SelfUpdater, translator):
        self.updater = self_updater
        self.t = translator

    def handle_update(self) -> None:
        """Handle complete self-update flow with user interaction."""
        try:
            # Check dependencies before any update operations
            deps = self.updater.config.get('dependencies', [])
            if deps:
                from ..core.dependencies import ensure_dependencies
                if not ensure_dependencies(deps, self.t):
                    print(Colors.error(self.t.get('self_update.dependencies_missing')))
                    return

            print(Colors.info(f"\n{self.t.get('self_update.checking')}"))
            
            # Get current version
            current_version = self.updater.get_current_version()
            
            # Check for updates
            latest_version = self.updater.check_for_updates()
            
            if not latest_version:
                print(Colors.error(self.t.get('self_update.no_version')))
                return
            
            # Display versions
            current_color = Colors.unknown if current_version == "unknown" else Colors.version
            print(f"{self.t.get('self_update.current')}: {current_color(current_version)}")
            print(f"{self.t.get('self_update.latest')}: {Colors.version(latest_version)}")
            
            # Check if already up to date
            if current_version == latest_version:
                print(Colors.success(f"\n✓ {self.t.get('self_update.up_to_date')}"))
                return
            
            # Show update available
            print(Colors.warning(f"\n{self.t.get('self_update.update_available')}"))
            
            # Confirm update (default=False: Enter = no, safer for destructive action)
            message = f"{self.t.get('self_update.confirm')} {Colors.version(latest_version)}?"
            if not confirm(message, default=True, translator=self.t):
                print(Colors.info(self.t.get('messages.cancelled')))
                return
            
            # Perform update
            self.updater.perform_update()
            
        except KeyboardInterrupt:
            print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
        except Exception as e:
            print(Colors.error(f"\n{self.t.get('self_update.failed')}: {e}"))
