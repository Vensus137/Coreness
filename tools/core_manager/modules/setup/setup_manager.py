"""Initial setup module for language, environment, and deployment mode selection."""

from typing import Callable
from ..i18n.translator import Translator
from ..core.version_file import VersionFile
from ..core.config import ConfigManager
from ..ui.colors import Colors


class SetupManager:
    """Manages initial setup and configuration selection."""

    def __init__(
        self,
        translator: Translator,
        version_file: VersionFile,
        config: ConfigManager,
        input_func: Callable[[str], str] | None = None,
    ):
        self.t = translator
        self.version_file = version_file
        self.config = config
        self.input_func = input_func or input

    def ensure_language(self) -> bool:
        """Ensure language is set. Prompts if missing, saves when changed. Returns True if changed."""
        if self.version_file.has("language"):
            return False
        language = self.select_language(
            self.config.get_available_languages(),
            self.config.get_default_language(),
            allow_cancel=False,
        )
        lang = language or self.config.get_default_language()
        self.version_file.set("language", lang)
        self.version_file.save()
        self.t.change_language(lang)
        return True

    def ensure_environment(self) -> bool:
        """Ensure environment is set. Prompts if missing, saves when changed. Returns True if changed."""
        if self.version_file.has("environment"):
            return False
        environment = self.select_environment(
            self.config.get_available_environments(),
            self.config.get_default_environment(),
            allow_cancel=False,
        )
        env = environment or self.config.get_default_environment()
        self.version_file.set("environment", env)
        self.version_file.save()
        return True

    def ensure_deployment_mode(self) -> bool:
        """Ensure deployment mode is set. Prompts if missing, saves when changed. Returns True if changed."""
        if self.version_file.has("deployment_mode"):
            return False
        deployment_mode = self.select_deployment_mode(
            self.config.get_available_deployment_modes(),
            self.config.get_default_deployment_mode(),
            allow_cancel=False,
        )
        mode = deployment_mode or self.config.get_default_deployment_mode()
        self.version_file.set("deployment_mode", mode)
        self.version_file.save()
        return True

    def ensure_all(self) -> None:
        """Ensure all settings are set. Prompts for missing, saves each when changed."""
        needs_any = (
            not self.version_file.has("language") or
            not self.version_file.has("environment") or
            not self.version_file.has("deployment_mode")
        )
        if needs_any:
            print(Colors.warning(f"\n{self.t.get('init.setup_required')}"))
        changed = self.ensure_language()
        changed = self.ensure_environment() or changed
        changed = self.ensure_deployment_mode() or changed
        if changed:
            print(Colors.success(f"\n✓ {self.t.get('init.setup_complete')}"))

    def change_language(self) -> None:
        """Change language from menu. Prompts, updates version_file and translator, saves."""
        language = self.select_language(
            self.config.get_available_languages(),
            self.version_file.get("language")
        )
        if language:
            self.version_file.set("language", language)
            self.version_file.save()
            self.t.change_language(language)

    def select_language(self, available_languages: list[str], default_language: str | None = None, allow_cancel: bool = True) -> str | None:
        """Prompt user to select language. Returns None if cancelled (0) when allow_cancel."""
        print(f"\n{self.t.get('messages.select_language')}:")
        print("-" * 40)

        for idx, lang in enumerate(available_languages, 1):
            lang_name = self.t.get(f"languages.{lang}")
            print(f"{idx}. {lang_name}")
        if allow_cancel:
            print(f"0. {self.t.get('messages.cancel')}")

        print("-" * 40)

        prompt_range = f"0-{len(available_languages)}" if allow_cancel else f"1-{len(available_languages)}"
        while True:
            try:
                choice = self.input_func(f"{self.t.get('messages.choice')} ({prompt_range}): ").strip()
                choice_idx = int(choice)

                if choice_idx == 0 and allow_cancel:
                    return default_language
                elif 1 <= choice_idx <= len(available_languages):
                    selected = available_languages[choice_idx - 1]
                    print(Colors.success(f"\n✓ {self.t.get('messages.language_changed')}: {self.t.get(f'languages.{selected}')}"))
                    return selected
                else:
                    print(Colors.error(f"✗ {self.t.get('messages.invalid_choice')}"))
            except (ValueError, KeyboardInterrupt):
                print(Colors.error(f"\n{self.t.get('messages.invalid_choice')}"))
            except EOFError:
                print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
                raise

    def select_environment(self, available_environments: list[str], default_env: str | None = None, allow_cancel: bool = True) -> str | None:
        """Prompt user to select environment. Returns None if cancelled (0) when allow_cancel."""
        print(f"\n{self.t.get('messages.select_environment')}:")
        print("-" * 40)

        for idx, env in enumerate(available_environments, 1):
            env_name = self.t.get(f"environments.{env}")
            print(f"{idx}. {env_name}")
        if allow_cancel:
            print(f"0. {self.t.get('messages.cancel')}")

        print("-" * 40)

        prompt_range = f"0-{len(available_environments)}" if allow_cancel else f"1-{len(available_environments)}"
        while True:
            try:
                choice = self.input_func(f"{self.t.get('messages.choice')} ({prompt_range}): ").strip()
                choice_idx = int(choice)

                if choice_idx == 0 and allow_cancel:
                    return default_env
                elif 1 <= choice_idx <= len(available_environments):
                    selected = available_environments[choice_idx - 1]
                    print(Colors.success(f"\n✓ {self.t.get('messages.environment_set')}: {self.t.get(f'environments.{selected}')}"))
                    return selected
                else:
                    print(Colors.error(f"✗ {self.t.get('messages.invalid_choice')}"))
            except (ValueError, KeyboardInterrupt):
                print(Colors.error(f"\n{self.t.get('messages.invalid_choice')}"))
            except EOFError:
                print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
                raise

    def select_deployment_mode(self, available_modes: list[str], default_mode: str | None = None, allow_cancel: bool = True) -> str | None:
        """Prompt user to select deployment mode. Returns None if cancelled (0) when allow_cancel."""
        print(f"\n{self.t.get('messages.select_deployment_mode')}:")
        print("-" * 40)

        for idx, mode in enumerate(available_modes, 1):
            mode_name = self.t.get(f"deployment_modes.{mode}")
            print(f"{idx}. {mode_name}")
        if allow_cancel:
            print(f"0. {self.t.get('messages.cancel')}")

        print("-" * 40)

        prompt_range = f"0-{len(available_modes)}" if allow_cancel else f"1-{len(available_modes)}"
        while True:
            try:
                choice = self.input_func(f"{self.t.get('messages.choice')} ({prompt_range}): ").strip()
                choice_idx = int(choice)

                if choice_idx == 0 and allow_cancel:
                    return default_mode
                elif 1 <= choice_idx <= len(available_modes):
                    selected = available_modes[choice_idx - 1]
                    print(Colors.success(f"\n✓ {self.t.get('messages.deployment_mode_set')}: {self.t.get(f'deployment_modes.{selected}')}"))
                    return selected
                else:
                    print(Colors.error(f"✗ {self.t.get('messages.invalid_choice')}"))
            except (ValueError, KeyboardInterrupt):
                print(Colors.error(f"\n{self.t.get('messages.invalid_choice')}"))
            except EOFError:
                print(Colors.warning(f"\n{self.t.get('messages.interrupted')}"))
                raise
