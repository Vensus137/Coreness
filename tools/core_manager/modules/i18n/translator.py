"""Internationalization module for Core Manager."""

import json
from pathlib import Path
from typing import Any


class Translator:
    """Handles translation loading and text retrieval."""

    def __init__(self, utility_root: Path, language: str = "en"):
        self.utility_root = utility_root
        self.language = language
        self.translations: dict[str, Any] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load translations for current language."""
        # i18n files are in utility_root/i18n, not in modules/i18n
        i18n_dir = self.utility_root / "i18n"
        translation_file = i18n_dir / f"{self.language}.json"

        if not translation_file.exists():
            raise FileNotFoundError(f"Translation file not found: {translation_file}")

        with open(translation_file, "r", encoding="utf-8") as f:
            self.translations = json.load(f)

    def get(self, key: str, **kwargs) -> str:
        """Get translation by dot-separated key path."""
        keys = key.split(".")
        value = self.translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, key)
            else:
                return key

        if isinstance(value, str) and kwargs:
            return value.format(**kwargs)

        return str(value) if not isinstance(value, dict) else key

    def change_language(self, language: str) -> None:
        """Change current language and reload translations."""
        self.language = language
        self._load_translations()
