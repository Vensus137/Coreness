"""Self-update mechanism for Core Manager."""

import os
import stat
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..ui.colors import Colors
from ..core.dependencies import ensure_dependencies
from ..core.restart_manager import RestartManager
from .version_fetcher import get_latest_stable_and_prerelease


def _remove_readonly(func, path, excinfo):
    """Error handler for shutil.rmtree to remove readonly files on Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class SelfUpdater:
    """Handles self-update of Core Manager utility."""

    # Parameter to restart utility and land back in self-update flow
    RESUME_SELF_UPDATE_ARG = "--resume-self-update"
    TEMP_DIR_MARKER = ".core_manager_update_temp"
    BACKUP_DIR_MARKER = ".core_manager_update_backup"

    def __init__(self, utility_root: Path, project_root: Path, config: dict, config_manager, version_file, translator, restart_manager):
        self.utility_root = utility_root
        self.project_root = project_root
        self.config = config
        self.config_manager = config_manager
        self.version_file = version_file
        self.t = translator
        self.restart_manager = restart_manager

    def get_current_version(self) -> Optional[str]:
        """Get current utility version from version file first, then git tag. Returns 'unknown' if neither available."""
        if self.version_file:
            v = self.version_file.get("version")
            if v:
                return v.strip()
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--abbrev=0'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    def check_for_updates(self) -> Optional[dict]:
        """Check for updates. Returns dict with current, latest_stable, latest_prerelease (each str or None)."""
        try:
            repo_url = self.config.get('repository', {}).get('url', '')
            if not repo_url:
                print(Colors.error(self.t.get('self_update.repo_not_configured')))
                return None

            token = self.config_manager.get_github_token()
            latest_stable, latest_prerelease = get_latest_stable_and_prerelease(repo_url, token)

            if not latest_stable and not latest_prerelease and not token:
                token_env = self.config.get('token_env', 'GITHUB_TOKEN')
                print(Colors.error(self.t.get('self_update.repo_not_found', token_env=token_env)))

            current = self.get_current_version()
            return {
                "current": current,
                "latest_stable": latest_stable,
                "latest_prerelease": latest_prerelease,
            }
        except ImportError:
            print(Colors.error(self.t.get('self_update.requests_not_installed')))
            return None
        except Exception as e:
            print(Colors.error(f"{self.t.get('self_update.check_failed')}: {e}"))
            return None

    def download_update(self, temp_dir: Path, version: Optional[str] = None) -> bool:
        """Download specified version from GitHub to temp_dir/core_manager. If version is None, clone default branch."""
        try:
            repo_url = self.config.get('repository', {}).get('url', '')
            branch = self.config.get('repository', {}).get('branch', 'main')
            ref = (version if version and version.startswith('v') else f"v{version}") if version else branch

            if not repo_url:
                print(Colors.error(self.t.get('self_update.repo_not_configured')))
                return False

            token = self.config_manager.get_github_token()

            print(Colors.info(f"{self.t.get('self_update.downloading')}"))

            repo_temp = temp_dir / "repo"
            env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

            # Add token to URL for private repos
            clone_url = repo_url
            if token and repo_url.startswith('https://'):
                clone_url = repo_url.replace('https://', f'https://{token}@')

            cmd = ["git", "-c", "credential.helper=", "clone", "--depth", "1", "--branch", ref, clone_url, str(repo_temp)]

            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                # If ref is a tag, try without 'v' prefix (e.g. 1.2.0b)
                if version and ref.startswith('v'):
                    ref_alt = ref.lstrip('v')
                    cmd_alt = ["git", "-c", "credential.helper=", "clone", "--depth", "1", "--branch", ref_alt, clone_url, str(repo_temp)]
                    result = subprocess.run(cmd_alt, env=env, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    print(Colors.error(f"{self.t.get('self_update.clone_failed')}: {result.stderr}"))
                    return False
            
            # Extract core_manager from repo to temp_dir/core_manager
            utility_path = self.config.get('utility_path', 'tools/core_manager')
            source_utility = repo_temp / utility_path
            if not source_utility.exists():
                print(Colors.error(self.t.get('self_update.source_not_found')))
                return False
            
            dest_utility = temp_dir / "core_manager"
            shutil.copytree(source_utility, dest_utility)
            
            # Cleanup repo (handle readonly files on Windows)
            shutil.rmtree(repo_temp, onerror=_remove_readonly)
            
            print(Colors.success(f"✓ {self.t.get('self_update.downloaded')}"))
            return True
            
        except Exception as e:
            print(Colors.error(f"{self.t.get('self_update.download_failed')}: {e}"))
            return False

    def handle_resume(self, argv: list) -> None:
        """If RESUME_SELF_UPDATE_ARG is in argv OR markers exist, continue self-update flow."""
        # Check if resume parameter passed
        has_param = self.RESUME_SELF_UPDATE_ARG in argv
        if has_param:
            while self.RESUME_SELF_UPDATE_ARG in argv:
                argv.remove(self.RESUME_SELF_UPDATE_ARG)
        
        # Check if markers exist (fallback if parameter not passed)
        temp_marker = self.utility_root.parent / self.TEMP_DIR_MARKER
        backup_marker = self.utility_root.parent / self.BACKUP_DIR_MARKER
        has_markers = temp_marker.exists() and backup_marker.exists()
        
        # Resume if parameter passed OR markers exist
        if has_param or has_markers:
            self._run_resume_steps()

    def _run_resume_steps(self) -> None:
        """Steps to run when resuming self-update after restart (replace all files, cleanup)."""
        temp_marker = self.utility_root.parent / self.TEMP_DIR_MARKER
        backup_marker = self.utility_root.parent / self.BACKUP_DIR_MARKER
        
        if not temp_marker.exists() or not backup_marker.exists():
            print(Colors.warning(self.t.get('self_update.no_resume_data')))
            return
        
        # Read paths from markers
        temp_dir = Path(temp_marker.read_text().strip())
        backup_dir = Path(backup_marker.read_text().strip())
        
        if not temp_dir.exists():
            print(Colors.error(self.t.get('self_update.temp_not_found')))
            self._cleanup_markers()
            return
        
        downloaded_utility = temp_dir / "core_manager"
        if not downloaded_utility.exists():
            print(Colors.error(self.t.get('self_update.source_not_found')))
            self._cleanup_markers()
            if temp_dir.exists():
                shutil.rmtree(temp_dir, onerror=_remove_readonly)
            return
        
        try:
            print(Colors.info(self.t.get('self_update.completing_update')))
            
            # Replace ALL files (now unlocked after restart)
            for item in downloaded_utility.iterdir():
                dst_item = self.utility_root / item.name
                try:
                    if item.is_dir():
                        if dst_item.exists():
                            shutil.rmtree(dst_item)
                        shutil.copytree(item, dst_item)
                    else:
                        shutil.copy2(item, dst_item)
                except Exception as e:
                    print(Colors.error(f"Failed to copy {item.name}: {e}"))
                    raise
            
            print(Colors.success(f"✓ {self.t.get('self_update.files_updated')}"))
            
            # Cleanup temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir, onerror=_remove_readonly)
            
            # Remove backup on success
            if backup_dir.exists():
                shutil.rmtree(backup_dir, onerror=_remove_readonly)
            
            # Remove markers
            self._cleanup_markers()
            
            print(Colors.success(f"\n✓ {self.t.get('self_update.update_complete')}"))
            
        except Exception as e:
            print(Colors.error(f"{self.t.get('self_update.resume_failed')}: {e}"))
            import traceback
            traceback.print_exc()
            
            # Try to restore from backup
            if backup_dir.exists():
                print(Colors.info(self.t.get('self_update.restoring_backup')))
                try:
                    for item in self.utility_root.iterdir():
                        try:
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                        except Exception:
                            pass
                    
                    for item in backup_dir.iterdir():
                        dst_item = self.utility_root / item.name
                        if item.is_dir():
                            shutil.copytree(item, dst_item)
                        else:
                            shutil.copy2(item, dst_item)
                    
                    print(Colors.success(f"✓ {self.t.get('self_update.backup_restored')}"))
                    shutil.rmtree(backup_dir, onerror=_remove_readonly)
                except Exception as restore_error:
                    print(Colors.error(f"{self.t.get('self_update.restore_failed')}: {restore_error}"))
                    print(Colors.warning(f"{self.t.get('self_update.backup_location')}: {backup_dir}"))
            
            # Cleanup markers and temp
            self._cleanup_markers()
            if temp_dir.exists():
                shutil.rmtree(temp_dir, onerror=_remove_readonly)

    def _cleanup_markers(self) -> None:
        """Remove marker files."""
        temp_marker = self.utility_root.parent / self.TEMP_DIR_MARKER
        backup_marker = self.utility_root.parent / self.BACKUP_DIR_MARKER
        
        if temp_marker.exists():
            temp_marker.unlink()
        if backup_marker.exists():
            backup_marker.unlink()

    def perform_update(self, version: Optional[str]) -> bool:
        """Perform self-update of Core Manager to the given version (e.g. 1.2.0b or v1.2.0b)."""
        temp_dir = None
        backup_dir = None

        if not version:
            print(Colors.error(self.t.get('self_update.no_version')))
            return False

        try:
            # Check dependencies first
            deps = self.config.get('dependencies', [])
            if deps and not ensure_dependencies(deps, self.t):
                print(Colors.error(self.t.get('self_update.dependencies_missing')))
                return False

            print(Colors.info(self.t.get('self_update.preparing')))

            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="core_manager_update_"))

            # Download update
            if not self.download_update(temp_dir, version):
                if temp_dir and temp_dir.exists():
                    shutil.rmtree(temp_dir, onerror=_remove_readonly)
                return False
            
            # Verify downloaded files
            downloaded_utility = temp_dir / "core_manager"
            if not downloaded_utility.exists():
                print(Colors.error(self.t.get('self_update.source_not_found')))
                if temp_dir and temp_dir.exists():
                    shutil.rmtree(temp_dir, onerror=_remove_readonly)
                return False
            
            # Create backup
            backup_dir = self.utility_root.parent / "core_manager.backup"
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(self.utility_root, backup_dir)
            print(Colors.success(f"✓ {self.t.get('self_update.backup_created')}"))
            
            # Save markers for resume (before restart)
            temp_marker = self.utility_root.parent / self.TEMP_DIR_MARKER
            backup_marker = self.utility_root.parent / self.BACKUP_DIR_MARKER
            temp_marker.write_text(str(temp_dir))
            backup_marker.write_text(str(backup_dir))
            
            # Restart to complete update (files will be replaced after restart when unlocked)
            print(Colors.info(self.t.get('self_update.restarting')))
            self.restart_manager.restart_with_resume(self.RESUME_SELF_UPDATE_ARG)
            
        except Exception as e:
            print(Colors.error(f"{self.t.get('self_update.failed')}: {e}"))
            
            # Cleanup on failure
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, onerror=_remove_readonly)
            if backup_dir and backup_dir.exists():
                shutil.rmtree(backup_dir, onerror=_remove_readonly)
            self._cleanup_markers()
            
            return False
