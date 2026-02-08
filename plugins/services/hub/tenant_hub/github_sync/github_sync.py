"""
GitHub Sync - complete GitHub synchronization module
Combines basic operations (cloning, copying) with smart API-based synchronization
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
from git import Repo


class GitHubSync:
    """
    Complete GitHub synchronization for tenant configurations.
    Provides both basic operations and smart API-based incremental sync.
    """
    
    def __init__(self, logger, settings_manager):
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Get settings from tenant_hub
        plugin_settings = self.settings_manager.get_plugin_settings("tenant_hub")
        
        # GitHub settings
        self.github_url = plugin_settings.get('github_url', '')
        self.github_token = plugin_settings.get('github_token', '')
        
        # Get global settings
        global_settings = self.settings_manager.get_global_settings()
        
        # Boundary between system and public tenants
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 99)
        
        # Path to tenants
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = project_root / tenants_config_path
        
        # Smart sync state (stored in memory)
        self.last_processed_sha: Optional[str] = None
        self.last_etag: Optional[str] = None
        
        # Extract owner and repo from URL
        self.repo_owner, self.repo_name = self._parse_github_url()
    
    # === Basic operations ===
    
    async def pull_tenant(self, tenant_id: int) -> Dict[str, Any]:
        """Downloads specific tenant from GitHub repository"""
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id not specified"
                    }
                }
            
            # Check GitHub configuration
            validation_error = self._validate_github_config()
            if validation_error:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": validation_error
                    }
                }
            
            # Check that this is a public tenant (not system)
            if tenant_id <= self.max_system_tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": f"Tenant {tenant_id} is system (ID <= {self.max_system_tenant_id}). Synchronization prohibited."
                    }
                }
            
            tenant_name = f"tenant_{tenant_id}"
            tenant_local_path = self.tenants_path / tenant_name
            
            # Delete old tenant folder
            if tenant_local_path.exists():
                shutil.rmtree(tenant_local_path)
            
            # Clone repository and copy needed folder
            success = await self._clone_and_copy_tenant(tenant_id, tenant_local_path)
            if not success:
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": f"Failed to download tenant {tenant_id} from GitHub"
                    }
                }
            
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant {tenant_id}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def pull_all(self) -> Dict[str, Any]:
        """Downloads all public tenants from GitHub repository"""
        try:
            # Check GitHub configuration
            validation_error = self._validate_github_config()
            if validation_error:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": validation_error
                    }
                }
            
            # Delete all public tenants before loading new ones
            self._delete_all_public_tenants()
            
            # Clone repository and copy all public tenants
            updated_count = await self.clone_and_copy_tenants(sync_all=True)
            if updated_count == 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": "Failed to download repository from GitHub"
                    }
                }
            
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Error synchronizing all public tenants: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def clone_and_copy_tenants(self, tenant_ids: Optional[List[int]] = None, sync_all: bool = False) -> int:
        """Clones repository and copies specified tenants"""
        try:
            # Form URL with token
            auth_url = self._get_auth_url()
            
            # Create temporary folder for cloning
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                repo_path = temp_path / "repo"
                
                # Clone repository (only last commit for speed)
                self.logger.info("Cloning repository...")
                Repo.clone_from(auth_url, str(repo_path), depth=1)
                
                # Path to tenant folder in cloned repository
                tenant_repo_path = repo_path / "tenant"
                
                if not tenant_repo_path.exists():
                    self.logger.warning("Tenant folder not found in repository")
                    return 0
                
                # Determine which tenants to update
                if sync_all:
                    # Update all public tenants from repository
                    tenant_ids_to_sync = []
                    for tenant_folder in tenant_repo_path.iterdir():
                        if tenant_folder.is_dir() and tenant_folder.name.startswith("tenant_"):
                            try:
                                tenant_id_str = tenant_folder.name.replace("tenant_", "")
                                tenant_id = int(tenant_id_str)
                                # Filter only public (repository should only have them, but just in case)
                                if tenant_id > self.max_system_tenant_id:
                                    tenant_ids_to_sync.append(tenant_id)
                            except ValueError:
                                continue
                elif tenant_ids:
                    # Use provided list
                    tenant_ids_to_sync = tenant_ids
                else:
                    # Nothing to synchronize
                    return 0
                
                # Copy each tenant directly to config/tenant/
                updated_count = 0
                for tenant_id in tenant_ids_to_sync:
                    tenant_name = f"tenant_{tenant_id}"
                    source = tenant_repo_path / tenant_name
                    destination = self.tenants_path / tenant_name
                    
                    if not source.exists():
                        self.logger.warning(f"[Tenant-{tenant_id}] Not found in repository")
                        continue
                    
                    try:
                        # Delete old version if exists
                        if destination.exists():
                            shutil.rmtree(destination)
                        
                        # Copy directly from temporary repository
                        shutil.copytree(source, destination)
                        
                        self.logger.info(f"[Tenant-{tenant_id}] Updated")
                        updated_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"[Tenant-{tenant_id}] Error copying: {e}")
                
                return updated_count
                
        except Exception as e:
            self.logger.error(f"Error cloning and copying tenants: {e}")
            return 0
    
    # === Smart synchronization (API-based) ===
    
    def update_processed_sha(self, sha: str) -> None:
        """Updates last processed SHA"""
        self.last_processed_sha = sha
    
    async def get_changed_tenants(self) -> Dict[str, Any]:
        """
        Determines which tenants changed through GitHub Compare API.
        WITH PROTECTION: automatically filters system tenants.
        """
        try:
            # No URL = sync disabled by design, system uses only system tenants
            if not (self.github_url or "").strip():
                self.logger.info(
                    "GitHub sync not configured (github_url empty); synchronization skipped, system will use only system tenants"
                )
                return {
                    "result": "success",
                    "response_data": {
                        "changed_tenants": {},
                        "sync_all": False,
                        "has_changes": False,
                        "current_sha": None
                    }
                }
            
            validation_error = self._validate_github_config_for_api()
            if validation_error:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": validation_error
                    }
                }
            
            # Get current HEAD commit through API (with ETag optimization)
            current_sha = await self.get_latest_commit_sha()
            
            # If current_sha is None and last_processed_sha exists - this is 304 Not Modified (no changes)
            if not current_sha:
                # Check if saved SHA exists (means this is not an error, but 304)
                if self.last_processed_sha:
                    # No changes (304 Not Modified)
                    return {
                        "result": "success",
                        "response_data": {
                            "changed_tenants": {},
                            "sync_all": False,
                            "has_changes": False,
                            "current_sha": self.last_processed_sha
                        }
                    }
                else:
                    # This is an error - failed to get commit and no saved SHA
                    return {
                        "result": "error",
                        "error": {
                            "code": "API_ERROR",
                            "message": "Failed to get current commit"
                        }
                    }
            
            # Use SHA from memory (or None if this is first run)
            last_sha = self.last_processed_sha
            
            # If SHA match - no changes
            if last_sha and last_sha == current_sha:
                return {
                    "result": "success",
                    "response_data": {
                        "changed_tenants": {},
                        "sync_all": False,
                        "has_changes": False,
                        "current_sha": current_sha
                    }
                }
            
            # If this is first run (no saved SHA)
            if not last_sha:
                self.logger.info("First synchronization - all public tenants will be updated")
                return {
                    "result": "success",
                    "response_data": {
                        "changed_tenants": {},  # Empty dictionary, as list is unknown until cloning
                        "sync_all": True,  # Explicit flag - need to update all public tenants
                        "has_changes": True,
                        "current_sha": current_sha
                    }
                }
            
            # Use Compare API to get ALL changed files
            compare_result = await self._compare_commits(last_sha, current_sha)
            
            if compare_result.get("result") != "success":
                return compare_result
            
            # Extract tenant_id and change blocks from file paths WITH PROTECTION
            changed_tenants_data = self._extract_tenant_changes_with_protection(
                compare_result.get('files', [])
            )
            
            return {
                "result": "success",
                "response_data": {
                    "changed_tenants": changed_tenants_data,  # {tenant_id: {"bots": [...], "scenarios": bool}}
                    "sync_all": False,  # Explicitly indicate this is not full synchronization
                    "has_changes": len(changed_tenants_data) > 0,
                    "current_sha": current_sha
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error determining changed tenants: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_changed_tenants(self, changed_tenant_ids: Optional[List[int]] = None, current_sha: str = None, sync_all: bool = False) -> Dict[str, Any]:
        """
        Synchronizes changed tenants directly to config/tenant/.
        WITH PROTECTION: double check for system tenants.
        """
        try:
            if not current_sha:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "current_sha is required"
                    }
                }
            
            # PROTECTION LEVEL 2: Filter system tenants
            if sync_all:
                # Synchronize all public tenants
                public_tenants = None
            elif changed_tenant_ids:
                # Filter only public from provided list
                public_tenants = [
                    tenant_id for tenant_id in changed_tenant_ids
                    if tenant_id > self.max_system_tenant_id
                ]
                
                if len(public_tenants) < len(changed_tenant_ids):
                    blocked_count = len(changed_tenant_ids) - len(public_tenants)
                    self.logger.warning(
                        f"[SECURITY] Blocked {blocked_count} system tenants from synchronization"
                    )
                
                if not public_tenants:
                    self.logger.info("No public tenants to synchronize")
                    # Update SHA in memory even if nothing to update
                    self.update_processed_sha(current_sha)
                    return {
                        "result": "success",
                        "response_data": {
                            "updated_tenants": 0
                        }
                    }
            else:
                # Neither tenants nor sync_all flag provided
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Tenants not specified for synchronization or sync_all=False"
                    }
                }
            
            # Use base method for cloning and copying
            if sync_all:
                updated_count = await self.clone_and_copy_tenants(sync_all=True)
            else:
                updated_count = await self.clone_and_copy_tenants(tenant_ids=public_tenants)
            
            # Update SHA in memory after successful synchronization
            self.update_processed_sha(current_sha)
            
            return {
                "result": "success",
                "response_data": {
                    "updated_tenants": updated_count
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error synchronizing changed tenants: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_latest_commit_sha(self) -> Optional[str]:
        """
        Gets SHA of latest commit through GitHub Events API with ETag optimization.
        Uses ETag to minimize traffic: if no changes, gets 304 Not Modified.
        """
        try:
            # Use Events API - more efficient for tracking changes
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/events"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Add ETag to check without downloading data
            if self.last_etag:
                headers['If-None-Match'] = self.last_etag
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={"per_page": 5}) as response:
                    # If no changes - return None (no need to process)
                    if response.status == 304:
                        # No changes, return current SHA (if exists) for comparison
                        return self.last_processed_sha
                    
                    if response.status == 200:
                        # Save ETag for next request
                        etag = response.headers.get('ETag')
                        if etag:
                            self.last_etag = etag
                        
                        events = await response.json()
                        
                        # Find last PushEvent (push to repository)
                        for event in events:
                            if event.get('type') == 'PushEvent':
                                payload = event.get('payload', {})
                                commits = payload.get('commits', [])
                                if commits:
                                    # Return SHA of last commit from push
                                    return commits[-1].get('sha')
                        
                        # If no PushEvent in recent events, use Commits API as fallback
                        return await self._get_sha_via_commits_api()
                    
                    elif response.status == 404:
                        self.logger.error(f"Repository not found: {self.repo_owner}/{self.repo_name}")
                    else:
                        self.logger.error(f"Error getting events: HTTP {response.status}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting latest commit: {e}")
            return None
    
    # === Internal methods ===
    
    def _validate_github_config(self) -> Optional[str]:
        """Validates GitHub configuration. Returns None if OK, or error description string."""
        # Check URL and token presence
        if not self.github_url or not self.github_token:
            return "GitHub not configured or token missing"
        
        # Check that URL and token are strings
        if not isinstance(self.github_url, str):
            self.logger.error(f"GitHub URL must be string, got: {type(self.github_url)}")
            return "GitHub URL has invalid type"
        
        if not isinstance(self.github_token, str):
            self.logger.error(f"GitHub token must be string, got: {type(self.github_token)}")
            return "GitHub token has invalid type"
        
        return None
    
    def _validate_github_config_for_api(self) -> Optional[str]:
        """Validates GitHub configuration for API operations (extended check)"""
        # Use base check
        base_error = self._validate_github_config()
        if base_error:
            return base_error
        
        # Additional check for API
        if not self.repo_owner or not self.repo_name:
            return "Failed to extract owner and repo from GitHub URL"
        
        return None
    
    def _get_auth_url(self) -> str:
        """Forms URL with token for authentication"""
        return self.github_url.replace(
            "https://github.com/",
            f"https://{self.github_token}@github.com/"
        )
    
    def _parse_github_url(self) -> tuple:
        """Extracts owner and repo from GitHub URL"""
        try:
            # Format: https://github.com/owner/repo or https://github.com/owner/repo.git
            url = self.github_url.replace('.git', '').rstrip('/')
            parts = url.split('/')
            if len(parts) >= 2:
                owner = parts[-2]
                repo = parts[-1]
                return owner, repo
            return None, None
        except Exception as e:
            self.logger.error(f"Error parsing GitHub URL: {e}")
            return None, None
    
    def _delete_all_public_tenants(self):
        """Deletes all public tenants from local folder"""
        if not self.tenants_path.exists():
            return
        
        deleted_count = 0
        for tenant_folder in self.tenants_path.iterdir():
            if tenant_folder.is_dir() and tenant_folder.name.startswith("tenant_"):
                try:
                    tenant_id_str = tenant_folder.name.replace("tenant_", "")
                    tenant_id = int(tenant_id_str)
                    
                    # Check that this is a public tenant (not system)
                    if tenant_id > self.max_system_tenant_id:
                        shutil.rmtree(tenant_folder)
                        deleted_count += 1
                        
                except ValueError:
                    self.logger.warning(f"Invalid tenant folder name: {tenant_folder.name}")
                    continue
        
        if deleted_count > 0:
            self.logger.info(f"Deleted {deleted_count} public tenants before loading")
    
    async def _clone_and_copy_tenant(self, tenant_id: int, local_path: Path) -> bool:
        """Clones repository and copies needed tenant folder"""
        try:
            tenant_name = f"tenant_{tenant_id}"
            
            # Form URL with token
            auth_url = self._get_auth_url()
            
            # Create temporary folder for cloning
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                repo_path = temp_path / "repo"
                
                # Clone repository (only last commit for speed)
                Repo.clone_from(auth_url, repo_path, depth=1)
                
                # Check tenant folder existence in repository
                tenant_repo_path = repo_path / "tenant" / tenant_name
                if not tenant_repo_path.exists():
                    self.logger.warning(f"Tenant {tenant_name} not found in repository")
                    return False
                
                # Copy tenant folder to local directory
                shutil.copytree(tenant_repo_path, local_path)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error cloning and copying tenant {tenant_id}: {e}")
            return False
    
    async def _get_sha_via_commits_api(self) -> Optional[str]:
        """Fallback method: gets SHA through Commits API (if Events API didn't return PushEvent)"""
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={"per_page": 1}) as response:
                    if response.status == 200:
                        commits = await response.json()
                        if commits and len(commits) > 0:
                            return commits[0].get("sha")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting commit via Commits API: {e}")
            return None
    
    async def _compare_commits(self, base_sha: str, head_sha: str) -> Dict[str, Any]:
        """Compares two commits through GitHub Compare API. Returns list of all changed files between commits."""
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/compare/{base_sha}...{head_sha}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        compare_data = await response.json()
                        files = compare_data.get("files", [])
                        
                        return {
                            "result": "success",
                            "files": files
                        }
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Compare API error: HTTP {response.status}, {error_text}")
                        return {
                            "result": "error",
                            "error": {
                                "code": "API_ERROR",
                                "message": f"Compare API error: HTTP {response.status}"
                            }
                        }
            
        except Exception as e:
            self.logger.error(f"Error comparing commits: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def _extract_tenant_changes_with_protection(self, files: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Extracts tenant_id and information about changed blocks from file paths.
        PROTECTION LEVEL 1: Filter system tenants at extraction stage.
        
        Returns structure: {tenant_id: {"bots": ["telegram", "whatsapp"], "scenarios": False, "storage": False}}
        """
        changed_tenants: Dict[int, Dict[str, Any]] = {}
        
        for file_info in files:
            file_path = file_info.get('filename', '')
            
            # Extract tenant_id from path
            tenant_id = self._extract_tenant_id_from_path(file_path)
            
            if tenant_id is None:
                continue  # Not a tenant file
            
            # PROTECTION: Filter system tenants
            if tenant_id <= self.max_system_tenant_id:
                self.logger.warning(
                    f"[SECURITY] Detected system tenant {tenant_id} in GitHub repository - ignoring"
                )
                continue  # DON'T add to list
            
            # Initialize tenant blocks if not exists
            if tenant_id not in changed_tenants:
                changed_tenants[tenant_id] = {"bots": [], "scenarios": False, "storage": False}
            
            # Determine change type by path
            block_result = self._determine_block_type(file_path)
            if block_result:
                block_type = block_result.get("type")
                if block_type == "bot":
                    # Add bot name to list (avoid duplicates)
                    bot_name = block_result.get("bot_name")
                    if bot_name and bot_name not in changed_tenants[tenant_id]["bots"]:
                        changed_tenants[tenant_id]["bots"].append(bot_name)
                elif block_type == "scenarios":
                    changed_tenants[tenant_id]["scenarios"] = True
                elif block_type == "storage":
                    changed_tenants[tenant_id]["storage"] = True
        
        return changed_tenants
    
    def _determine_block_type(self, file_path: str) -> Optional[Dict[str, str]]:
        """
        Determines block type by file path.
        
        Returns:
        - {"type": "bot", "bot_name": "telegram"} for bots/telegram.yaml
        - {"type": "scenarios"} for scenarios/*.yaml
        - {"type": "storage"} for storage/*.yaml
        - None if not a valid block
        """
        # Path format: tenant/tenant_XXX/...
        if not file_path.startswith('tenant/tenant_'):
            return None
        
        parts = file_path.split('/')
        if len(parts) < 3:
            return None
        
        # Check for bots: tenant/tenant_XXX/bots/[bot_name].yaml
        if parts[2] == "bots" and len(parts) >= 4:
            # Extract bot name from filename (e.g., telegram.yaml -> telegram)
            bot_file = parts[3]
            if bot_file.endswith('.yaml') or bot_file.endswith('.yml'):
                bot_name = bot_file.rsplit('.', 1)[0]  # Remove extension
                return {"type": "bot", "bot_name": bot_name}
        
        # Check for scenarios: tenant/tenant_XXX/scenarios/*.yaml
        if parts[2] == "scenarios" and len(parts) > 3:
            return {"type": "scenarios"}
        
        # Check for storage: tenant/tenant_XXX/storage/*.yaml
        if parts[2] == "storage" and len(parts) > 3:
            return {"type": "storage"}
        
        return None
    
    def _extract_tenant_id_from_path(self, file_path: str) -> Optional[int]:
        """Extracts tenant_id from file path"""
        try:
            # Path format: tenant/tenant_XXX/...
            if not file_path.startswith('tenant/tenant_'):
                return None
            
            # Extract tenant_XXX part
            parts = file_path.split('/')
            if len(parts) < 2:
                return None
            
            tenant_folder = parts[1]  # tenant_XXX
            if not tenant_folder.startswith('tenant_'):
                return None
            
            # Extract ID
            tenant_id_str = tenant_folder.replace('tenant_', '')
            tenant_id = int(tenant_id_str)
            return tenant_id
            
        except (ValueError, IndexError):
            return None
