"""Main menu module."""

from typing import Callable
from ..i18n.translator import Translator
from ..core.version_file import VersionFile
from .colors import Colors


class Menu:
    """Main menu handler."""

    def __init__(self, translator: Translator, version_file: VersionFile, input_func: Callable[[str], str] | None = None):
        self.t = translator
        self.version_file = version_file
        self.input_func = input_func or input

    def display(self) -> str:
        """Display main menu and return user choice."""
        width = 50
        print("\n" + "=" * width)
        print(Colors.bold(self.t.get('menu.title').center(width)))
        print("=" * width)
        
        # Display current settings with colors
        version = self.version_file.get("version") or self.t.get("messages.version_unknown")
        environment = self.version_file.get("environment", "N/A")
        deployment_mode = self.version_file.get("deployment_mode", "N/A")

        version_unknown = self.t.get("messages.version_unknown")
        version_color = Colors.unknown if version in ("unknown", version_unknown) else Colors.version
        env_color = Colors.unknown if environment == "N/A" else Colors.environment
        dep_color = Colors.unknown if deployment_mode == "N/A" else Colors.deployment

        print(f"\n  {self.t.get('messages.version')}: {version_color(version)}")
        print(f"  {self.t.get('messages.environment')}: {env_color(environment)}")
        print(f"  {self.t.get('messages.deployment_mode')}: {dep_color(deployment_mode)}")
        
        print("\n" + "-" * 50)
        print()
        print(f"1. {self.t.get('menu.update_platform')}")
        print(f"2. {self.t.get('database.menu_option')}")
        print(f"3. {self.t.get('self_update.menu_option')}")
        print(f"4. {self.t.get('menu.change_language')}")
        print(f"0. {self.t.get('menu.exit')}")
        print()
        print("-" * 50)

        while True:
            try:
                choice = self.input_func(f"{self.t.get('menu.select_action')}: ").strip()
                
                if choice in ["0", "1", "2", "3", "4"]:
                    return choice
                else:
                    print(Colors.error(f"✗ {self.t.get('messages.invalid_choice')}"))
            except (ValueError, KeyboardInterrupt):
                print(Colors.error(f"\n{self.t.get('messages.invalid_choice')}"))
            except EOFError:
                print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
                return "0"  # Exit on EOF

    def show_stub_message(self) -> None:
        """Show stub message for unimplemented features."""
        print(f"\n{self.t.get('menu.stub')}")
        self.input_func(self.t.get("messages.press_enter"))
