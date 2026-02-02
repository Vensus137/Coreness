"""Dependency checking and installation for feature blocks."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..ui.colors import Colors


def check_package(package: str) -> bool:
    """Check if package can be imported. Package name may differ from import name."""
    import_map = {"requests": "requests", "pyyaml": "yaml", "gitpython": "git"}
    import_name = import_map.get(package.lower(), package)
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def install_package(package: str) -> bool:
    """Install package via pip."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_dependencies(
    packages: list[str],
    translator,
    auto_install: bool = True
) -> bool:
    """Check and optionally install dependencies. Returns True if all satisfied."""
    missing = []
    for pkg in packages:
        if not check_package(pkg):
            missing.append(pkg)

    if not missing:
        return True

    for pkg in missing:
        if auto_install:
            print(Colors.info(f"Installing {pkg}..."))
            if install_package(pkg):
                print(Colors.success(f"✓ {pkg} installed"))
            else:
                print(Colors.error(f"Failed to install {pkg}. Run: pip install {pkg}"))
                return False
        else:
            print(Colors.error(f"Missing dependency: {pkg}. Run: pip install {pkg}"))
            return False

    return True
