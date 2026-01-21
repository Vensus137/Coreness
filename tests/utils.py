"""
Utilities for tests
"""
import os
from pathlib import Path


def find_project_root(start_path: Path = None) -> Path:
    """
    Reliably determines project root
    """
    # First check environment variable
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root and Path(env_root).exists():
        return Path(env_root)
    
    # Determine starting point
    if start_path is None:
        # Use current file as starting point
        start_path = Path(__file__)
    
    # Search for project root by key files/folders
    current = start_path.resolve()
    
    # If start_path is a file, start with its directory
    if current.is_file():
        current = current.parent
    
    # Go up until we find project root
    while current != current.parent:
        # Check for key project files
        if (current / "main.py").exists() and \
           (current / "plugins").exists() and \
           (current / "app").exists():
            return current
        current = current.parent
    
    # Fallback - if not found, return directory one level up from start_path
    # (for case when start_path is in tests/)
    if start_path.name == "tests" or "tests" in start_path.parts:
        # If we're in tests/, go up one level
        return start_path.parent if start_path.is_dir() else start_path.parent.parent
    
    return start_path.parent if start_path.is_file() else start_path

