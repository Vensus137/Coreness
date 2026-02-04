"""
Smart GitHub Sync - smart synchronization with GitHub repository
- Determines changes through GitHub Compare API
- Uses basic operations from base.py for cloning and copying
- Three-level protection against system tenants
- Incremental synchronization of only changed tenants
"""

from typing import Any, Dict, List, Optional

import aiohttp

from .base import GitHubSyncBase


class SmartGitHubSync(GitHubSyncBase):
    """
    Smart synchronization of public tenants from GitHub repository
    Uses GitHub API to determine changes and basic operations for updating
    """
    
    def __init__(self, logger, settings_manager):
        # Initialize base class
        super().__init__(logger, settings_manager)
        
        # Last processed SHA (stored in memory, updated after synchronization)
        self.last_processed_sha: Optional[str] = None
        
        # ETag for request optimization (304 Not Modified)
        self.last_etag: Optional[str] = None
        
        # Extract owner and repo from URL
        self.repo_owner, self.repo_name = self._parse_github_url()
    
    # === Public methods ===
    
    def update_processed_sha(self, sha: str) -> None:
        """Updates last processed SHA"""
        self.last_processed_sha = sha
    
    async def get_changed_tenants(self) -> Dict[str, Any]:
        """
        Determines which tenants changed through GitHub Compare API
        WITH PROTECTION: automatically filters system tenants
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
            validation_error = self._validate_github_config()
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
                # Return empty dictionary + sync_all flag for explicit full synchronization indication
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
            
            changed_tenants = sorted(changed_tenants_data.keys())
            
            return {
                "result": "success",
                "response_data": {
                    "changed_tenants": changed_tenants_data,  # {tenant_id: {"bot": bool, "scenarios": bool}}
                    "sync_all": False,  # Explicitly indicate this is not full synchronization
                    "has_changes": len(changed_tenants) > 0,
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
        Synchronizes changed tenants directly to config/tenant/
        Uses basic operations from GitHubSyncBase
        WITH PROTECTION: double check for system tenants
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
    
    # === Internal methods ===
    
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
    
    def _validate_github_config(self) -> Optional[str]:
        """
        Validates GitHub configuration (extended check for API)
        """
        # Use base check
        base_error = super()._validate_github_config()
        if base_error:
            return base_error
        
        # Additional check for API
        if not self.repo_owner or not self.repo_name:
            return "Failed to extract owner and repo from GitHub URL"
        
        return None
    
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
        """
        Compares two commits through GitHub Compare API
        Returns list of all changed files between commits
        """
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
    
    def _extract_tenant_changes_with_protection(self, files: List[Dict[str, Any]]) -> Dict[int, Dict[str, bool]]:
        """
        Extracts tenant_id and information about changed blocks from file paths WITH PROTECTION against system tenants
        
        PROTECTION LEVEL 1: Filter system tenants at extraction stage
        """
        changed_tenants: Dict[int, Dict[str, bool]] = {}
        
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
            
            # Determine which blocks changed
            if tenant_id not in changed_tenants:
                changed_tenants[tenant_id] = {"bot": False, "scenarios": False, "storage": False}
            
            # Determine change type by path
            block_type = self._determine_block_type(file_path)
            if block_type == "bot":
                changed_tenants[tenant_id]["bot"] = True
            elif block_type == "scenarios":
                changed_tenants[tenant_id]["scenarios"] = True
            elif block_type == "storage":
                changed_tenants[tenant_id]["storage"] = True
        
        return changed_tenants
    
    def _determine_block_type(self, file_path: str) -> Optional[str]:
        """
        Determines block type by file path
        """
        # Path format: tenant/tenant_XXX/...
        if not file_path.startswith('tenant/tenant_'):
            return None
        
        parts = file_path.split('/')
        if len(parts) < 3:
            return None
        
        # Strict check:
        # - bot: only exact change of tg_bot.yaml file in tenant root
        # - scenarios: any changes inside scenarios folder
        # - storage: any changes inside storage folder
        if parts[2] == "tg_bot.yaml":
            return "bot"
        
        if parts[2] == "scenarios" and len(parts) > 3:
            return "scenarios"
        
        if parts[2] == "storage" and len(parts) > 3:
            return "storage"
        
        return None
    
    def _extract_tenant_id_from_path(self, file_path: str) -> Optional[int]:
        """
        Extracts tenant_id from file path
        """
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

