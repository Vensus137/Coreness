"""Platform updater - clone, backup, update files, restore on failure."""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from .file_filter import FileFilter


class PlatformUpdater:
    """Handles platform file update: clone, backup, replace, restore."""

    def __init__(self, project_root: Path, config: dict):
        self.project_root = Path(project_root)
        self.config = config
        self.temp_dir: Optional[Path] = None
        self.files_to_update: list[str] = []

        server_config = config.get("system_update", {})
        self.repo_config = server_config.get("repository", {})
        self.settings = server_config.get("settings", {})
        self.files_config = server_config.get("files", {})

        self.backup_dir = self.settings.get("backup_dir", ".core_update_backup")

    def clone_repository(self, token: str) -> Optional[Path]:
        """Clone repository to temp dir. Uses token in URL for https (same as self-update). Returns repo_path or None."""
        repo_url = self.repo_config.get("url")
        if not repo_url:
            return None

        branch = self.repo_config.get("branch", "main")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="system_update_"))
        repo_path = self.temp_dir / "repo"

        clone_url = repo_url
        if token and repo_url.startswith("https://"):
            clone_url = repo_url.replace("https://", f"https://{token}@")

        try:
            env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
            cmd = [
                "git", "-c", "credential.helper=",
                "clone", "--depth", "1", "--branch", branch,
                clone_url, str(repo_path),
            ]
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return None
            return repo_path
        except Exception:
            return None

    def checkout_tag(self, repo_path: Path, version: str) -> bool:
        """Checkout to version tag. Fetches tag from origin first (shallow clone has no tags)."""
        try:
            from git import Repo
            repo = Repo(str(repo_path))

            tag_with_v = f"v{version}"
            tag_without_v = version

            # Shallow clone does not fetch tags; fetch the tag from origin first
            try:
                origin = repo.remote("origin")
                for tag_name in (tag_with_v, tag_without_v):
                    try:
                        origin.fetch(refspec=[f"refs/tags/{tag_name}:refs/tags/{tag_name}"])
                        break
                    except Exception:
                        continue
            except Exception:
                pass

            tag_name = None
            for tag in repo.tags:
                if tag.name == tag_with_v or tag.name == tag_without_v:
                    tag_name = tag.name
                    break

            if not tag_name:
                return False

            repo.git.checkout(tag_name)
            return True
        except Exception:
            return False

    def _get_files_to_update(self, repo_path: Path) -> list[str]:
        """Get list of files to update from cloned repo."""
        includes = self.files_config.get("include", [])
        excludes = self.files_config.get("exclude", [])
        ff = FileFilter(repo_path)
        return ff.get_files_for_update(includes, excludes)

    def _is_excluded(self, rel_path: str, excludes: List[str]) -> bool:
        """Check if path matches any exclude pattern."""
        norm_path = rel_path.replace("\\", "/")
        
        for exc in excludes:
            norm_exc = exc.replace("\\", "/")
            
            # Pattern: **/folder/ - any folder at any level
            if norm_exc.startswith("**/"):
                suffix = norm_exc[3:]
                if suffix.endswith("/"):
                    folder = suffix[:-1]
                    # Check if path contains this folder
                    if f"/{folder}/" in norm_path or norm_path.startswith(f"{folder}/") or norm_path.endswith(f"/{folder}"):
                        return True
                    # Check if path is inside this folder
                    parts = norm_path.split("/")
                    if folder in parts:
                        return True
                else:
                    # Pattern: **/file.ext
                    if norm_path.endswith(suffix) or f"/{suffix}" in norm_path:
                        return True
            
            # Pattern: folder/ - specific folder from root
            elif norm_exc.endswith("/"):
                folder = norm_exc[:-1]
                if norm_path.startswith(folder + "/") or f"/{folder}/" in norm_path or norm_path.endswith(f"/{folder}") or norm_path == folder:
                    return True
            
            # Pattern: exact match
            elif norm_path == norm_exc:
                return True
        
        return False

    def _sync_directory(self, src_dir: Path, dst_dir: Path, rel_base: str, excludes: List[str]) -> None:
        """Sync directory: copy new files, delete old files (except excluded)."""
        # Get all files in source directory
        src_files: Set[str] = set()
        if src_dir.exists():
            for item in src_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(src_dir)
                    rel_full = (Path(rel_base) / rel).as_posix()
                    if not self._is_excluded(rel_full, excludes):
                        src_files.add(str(rel))
        
        # Get all files in destination directory
        dst_files: Set[str] = set()
        if dst_dir.exists():
            for item in dst_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(dst_dir)
                    rel_full = (Path(rel_base) / rel).as_posix()
                    if not self._is_excluded(rel_full, excludes):
                        dst_files.add(str(rel))
        
        # Copy new/updated files from source
        for rel in src_files:
            src_file = src_dir / rel
            dst_file = dst_dir / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
        
        # Delete old files not in source (except excluded)
        for rel in dst_files:
            if rel not in src_files:
                rel_full = (Path(rel_base) / rel).as_posix()
                if not self._is_excluded(rel_full, excludes):
                    dst_file = dst_dir / rel
                    if dst_file.exists():
                        dst_file.unlink()
        
        # Clean up empty directories
        if dst_dir.exists():
            for item in sorted(dst_dir.rglob("*"), reverse=True):
                if item.is_dir() and not any(item.iterdir()):
                    try:
                        item.rmdir()
                    except Exception:
                        pass

    def backup_files(self) -> Optional[Path]:
        """Create backup of files/directories to be updated. Returns backup path or None."""
        includes = self.files_config.get("include", [])
        if not includes:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.project_root / f"{self.backup_dir}_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        for pattern in includes:
            src = self.project_root / pattern
            if not src.exists():
                continue

            dst = backup_path / pattern
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            except Exception:
                raise

        return backup_path

    def update_files(self, repo_path: Path) -> bool:
        """Update project files: copy files, sync directories with delete old files (except excluded)."""
        includes = self.files_config.get("include", [])
        excludes = self.files_config.get("exclude", [])
        
        if not includes:
            return False

        for pattern in includes:
            src = repo_path / pattern
            dst = self.project_root / pattern
            
            if not src.exists():
                continue
            
            # For files: simply copy
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            
            # For directories: sync with delete old files (except excluded)
            elif src.is_dir():
                rel_base = pattern.rstrip("/")
                self._sync_directory(src, dst, rel_base, excludes)

        return True

    def restore_backup(self, backup_path: Path) -> bool:
        """Restore files from backup. Returns True on success."""
        if not backup_path.exists():
            return False

        for item in backup_path.rglob("*"):
            if item.is_dir():
                continue

            rel_path = item.relative_to(backup_path)
            target = self.project_root / rel_path

            try:
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
            except Exception:
                pass

        return True

    def cleanup(self) -> None:
        """Remove temporary directory."""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
            self.temp_dir = None

    def remove_backup(self, backup_path: Path) -> None:
        """Remove backup directory after successful update."""
        if backup_path and backup_path.exists():
            try:
                shutil.rmtree(backup_path)
            except Exception:
                pass
