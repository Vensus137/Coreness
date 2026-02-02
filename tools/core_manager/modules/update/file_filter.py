"""File filtering for system update using include/exclude patterns."""

import glob
import os
from pathlib import Path
from typing import List, Set


class FileFilter:
    """Filters files for system update using flat include/exclude lists."""

    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)

    def _expand_patterns(self, patterns: List[str]) -> Set[str]:
        """Expand include patterns to file list."""
        files = set()

        for pattern in patterns:
            if pattern == "*":
                for root, dirs, filenames in os.walk(self.base_path):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "venv")]
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, self.base_path)
                        files.add(rel_path.replace("\\", "/"))

            elif pattern.endswith("/"):
                folder_path = self.base_path / pattern[:-1]
                if folder_path.exists():
                    for root, dirs, filenames in os.walk(folder_path):
                        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__",)]
                        for filename in filenames:
                            file_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(file_path, self.base_path)
                            files.add(rel_path.replace("\\", "/"))

            else:
                pattern_path = self.base_path / pattern
                if pattern_path.exists():
                    if pattern_path.is_file():
                        files.add(pattern.replace("\\", "/"))
                    elif pattern_path.is_dir():
                        for root, dirs, filenames in os.walk(pattern_path):
                            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__",)]
                            for filename in filenames:
                                file_path = os.path.join(root, filename)
                                rel_path = os.path.relpath(file_path, self.base_path)
                                files.add(rel_path.replace("\\", "/"))
                else:
                    glob_pattern = str(self.base_path / pattern)
                    for file_path in glob.glob(glob_pattern, recursive=True):
                        if os.path.isfile(file_path):
                            rel_path = os.path.relpath(file_path, self.base_path)
                            files.add(rel_path.replace("\\", "/"))

        return files

    def _apply_excludes(self, files: Set[str], excludes: List[str]) -> Set[str]:
        """Apply exclusion patterns."""
        excluded = set()

        for exc in excludes:
            norm_exc = exc.replace("\\", "/")

            if norm_exc.startswith("**/"):
                suffix = norm_exc[3:]
                for fp in files:
                    nfp = fp.replace("\\", "/")
                    if suffix.endswith("/"):
                        folder = suffix[:-1]
                        if f"/{folder}/" in nfp or nfp.endswith(f"/{folder}") or nfp.startswith(f"{folder}/"):
                            excluded.add(fp)
                    elif nfp.endswith(suffix) or f"/{suffix}" in nfp:
                        excluded.add(fp)

            elif norm_exc.endswith("/"):
                folder = norm_exc[:-1]
                for fp in files:
                    nfp = fp.replace("\\", "/")
                    if nfp.startswith(folder + "/") or f"/{folder}/" in nfp or nfp.endswith(f"/{folder}"):
                        excluded.add(fp)

            elif norm_exc.endswith("*"):
                prefix = norm_exc[:-1]
                for fp in files:
                    if fp.replace("\\", "/").startswith(prefix):
                        excluded.add(fp)

            else:
                for fp in files:
                    if fp.replace("\\", "/") == norm_exc:
                        excluded.add(fp)

        return files - excluded

    def get_files_for_update(self, includes: List[str], excludes: List[str]) -> List[str]:
        """Get sorted list of files for update."""
        if not includes:
            return []

        included = self._expand_patterns(includes)
        if excludes:
            included = self._apply_excludes(included, excludes)

        return sorted(included)
