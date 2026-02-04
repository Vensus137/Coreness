"""
GitHub Sync Base - basic GitHub synchronization operations
Repository cloning and tenant copying
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import Repo


class GitHubSyncBase:
    """
    Base class for synchronizing public tenants from GitHub repository
    Contains cloning and copying operations
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
    
    # === Public methods ===
    
    async def pull_tenant(self, tenant_id: int) -> Dict[str, Any]:
        """
        Downloads specific tenant from GitHub repository
        """
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
        """
        Downloads all public tenants from GitHub repository
        """
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
    
    # === Reusable methods ===
    
    async def clone_and_copy_tenants(self, tenant_ids: Optional[List[int]] = None, sync_all: bool = False) -> int:
        """
        Clones repository and copies specified tenants
        """
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
    
    # === Internal methods ===
    
    def _validate_github_config(self) -> Optional[str]:
        """
        Validates GitHub configuration
        Returns None if OK, or error description string
        """
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
    
    def _get_auth_url(self) -> str:
        """Forms URL with token for authentication"""
        return self.github_url.replace(
            "https://github.com/",
            f"https://{self.github_token}@github.com/"
        )
    
    def _delete_all_public_tenants(self):
        """
        Deletes all public tenants from local folder
        """
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
        """
        Clones repository and copies needed tenant folder
        """
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
    

