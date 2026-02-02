"""Platform updater - clone, backup, update files, restore on failure."""

import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

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

    def backup_files(self) -> Optional[Path]:
        """Create backup of files to be updated. Returns backup path or None."""
        if not self.files_to_update:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.project_root / f"{self.backup_dir}_{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)

        for rel_path in self.files_to_update:
            src = self.project_root / rel_path
            if not src.exists():
                continue

            dst = backup_path / rel_path
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
        """Update project files from repo by overwriting in place (Windows-safe, no delete)."""
        self.files_to_update = self._get_files_to_update(repo_path)
        if not self.files_to_update:
            return False

        for rel_path in self.files_to_update:
            src = repo_path / rel_path
            dst = self.project_root / rel_path
            if not src.exists():
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_file():
                shutil.copy2(src, dst)
            else:
                for item in src.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(src)
                        target = dst / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, target)

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
