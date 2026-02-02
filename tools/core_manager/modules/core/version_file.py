"""Version file management module."""

from pathlib import Path
from typing import Any


class VersionFile:
    """Manages reading and writing to config/.version file."""

    def __init__(self, utility_root: Path, project_root: Path, version_file_path: str = "config/.version"):
        self.utility_root = utility_root
        self.project_root = project_root
        self.version_file = project_root / version_file_path
        self.cache: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Load version file into cache. Empty cache if file does not exist."""
        self.cache = {}
        if not self.version_file.exists():
            return self.cache

        with open(self.version_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Convert boolean strings
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False

                    self.cache[key] = value

        return self.cache

    def save(self) -> None:
        """Save cache to version file. Creates parent directory if needed."""
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for key, value in self.cache.items():
            if isinstance(value, bool):
                value = str(value).lower()
            lines.append(f"{key}: {value}")

        with open(self.version_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        return self.cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self.cache[key] = value

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache
