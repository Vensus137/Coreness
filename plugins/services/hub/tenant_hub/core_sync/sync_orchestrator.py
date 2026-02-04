"""
Sync Orchestrator - orchestrator for tenant synchronization
Manages synchronization of system and public tenants through GitHub API
"""

from typing import Any, Dict


class SyncOrchestrator:
    """
    Tenant synchronization orchestrator
    Coordinates synchronization of system (locally) and public (from GitHub) tenants
    """
    
    def __init__(self, logger, smart_github_sync, github_sync, block_sync_executor, settings_manager, task_manager):
        self.logger = logger
        self.smart_github_sync = smart_github_sync
        self.github_sync = github_sync
        self.block_sync_executor = block_sync_executor
        self.settings_manager = settings_manager
        self.task_manager = task_manager
        
        # Get settings once on initialization
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 99)
        
        # Get path to tenants folder (already created in tenant_hub)
        tenants_config_path = global_settings.get('tenants_config_path', 'config/tenant')
        from pathlib import Path
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
        
        # Flag to prevent parallel synchronizations
        self._sync_in_progress = False
    
    async def sync_all_tenants(self) -> Dict[str, Any]:
        """
        Synchronize all tenants: system (locally) + public (from GitHub)
        """
        try:
            # Block 1: Synchronize system tenants from local folder
            system_result = await self.sync_system_tenants()
            
            # Block 2: Synchronize public tenants from GitHub
            # Use smart synchronization - it will determine if full synchronization is needed
            # If SHA is missing - it will automatically do full synchronization of all public tenants
            public_result = await self.sync_public_tenants()
            
            # Determine overall result based on results of both blocks
            if system_result.get("result") == "error" or public_result.get("result") == "error":
                # If at least one block returned error - return error with summary
                errors = []
                if system_result.get("result") == "error":
                    error_obj = system_result.get('error', {})
                    errors.append(f"System: {error_obj.get('message', 'Unknown error')}")
                if public_result.get("result") == "error":
                    error_obj = public_result.get('error', {})
                    errors.append(f"Public: {error_obj.get('message', 'Unknown error')}")
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": "; ".join(errors)
                    }
                }
            
            # Both blocks completed successfully
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error synchronizing all tenants: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_system_tenants(self) -> Dict[str, Any]:
        """
        Synchronize system tenants from local folder (without GitHub, fire-and-forget, without waiting for execution)
        """
        try:
            system_tenant_ids = []
            for tenant_dir in self.tenants_path.iterdir():
                if tenant_dir.is_dir() and tenant_dir.name.startswith('tenant_'):
                    try:
                        tenant_id = int(tenant_dir.name.replace('tenant_', ''))
                        if tenant_id <= self.max_system_tenant_id:
                            system_tenant_ids.append(tenant_id)
                    except ValueError:
                        continue

            if not system_tenant_ids:
                self.logger.info("No system tenants to synchronize")
                return {"result": "success", "response_data": {"updated_tenants": 0}}

            self.logger.info(f"Starting synchronization of {len(system_tenant_ids)} system tenants in background...")
            errors = []
            for tenant_id in system_tenant_ids:
                res = await self.task_manager.submit_task(
                    task_id=f"sync_tenant_{tenant_id}",
                    coro=(lambda t=tenant_id: self.block_sync_executor.sync_blocks(
                        t, {"bot": True, "scenarios": True, "storage": True, "config": True}, pull_from_github=False)),
                    fire_and_forget=True
                )
                if res.get('result') != 'success':
                    error_obj = res.get('error', {})
                    error_msg = error_obj.get('message', 'Unknown error') if isinstance(error_obj, dict) else str(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Failed to submit synchronization task: {error_msg}")
                    errors.append(tenant_id)

            if not errors:
                return { "result": "success" }
            else:
                return {
                    "result": "partial_success",
                    "error": f"Tasks not submitted for: {errors}"
                }
        except Exception as e:
            self.logger.error(f"Error in bulk synchronization task distribution: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_tenant(self, tenant_id: int, pull_from_github: bool = True) -> Dict[str, Any]:
        """
        Synchronize single tenant (all blocks: bot + scenarios + storage)
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
            
            # Synchronize all blocks
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": True, "scenarios": True, "storage": True, "config": True},
                pull_from_github=pull_from_github
            )
            
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant {tenant_id}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_public_tenants(self) -> Dict[str, Any]:
        """
        Synchronize public tenants from GitHub with protection against parallel runs
        """
        
        
        if self._sync_in_progress:
            self.logger.warning("Synchronization already in progress, skipping")
            return {"result": "success"}
        
        try:
            self._sync_in_progress = True
            
            # Use smart synchronization through GitHub API
            # If SHA is missing - it will automatically do full synchronization
            sync_result = await self._sync_public_tenants_incremental()          
            if sync_result.get("result") == "success":
                response_data = sync_result.get("response_data", {})
                updated_count = response_data.get("updated_tenants", 0)
                if updated_count > 0:
                    self.logger.info(f"Synchronized {updated_count} tenants")
            elif sync_result.get("result") == "partial_success":
                self.logger.warning("Synchronization completed with partial errors")
            else:
                # For temporary connection errors (DNS, network) log as warning, not error
                error_obj = sync_result.get('error', {})
                error_msg = error_obj.get('message', '') if isinstance(error_obj, dict) else str(error_obj)
                if 'Failed to get current commit' in error_msg or 'Failed to determine changes via API' in error_msg:
                    # This is a temporary network/GitHub API issue - not critical
                    # Detailed error already logged at lower level
                    pass  # Don't log again, warning already logged at medium level
                else:
                    # Other errors log as error
                    self.logger.error(f"Error synchronizing tenants: {error_msg}")
            
            return sync_result
                
        except Exception:
            raise
        finally:
            self._sync_in_progress = False

    async def _sync_public_tenants_incremental(self) -> Dict[str, Any]:
        """
        Performs incremental synchronization: determines changes through GitHub API and synchronizes only changed tenants
        """
        try:
            # 1. Determine changed tenants through GitHub Compare API
            changed_result = await self.smart_github_sync.get_changed_tenants()

            if changed_result.get("result") != "success":
                # If failed to determine changes - just skip
                self.logger.warning("Failed to determine changes via API, skipping synchronization")
                error_obj = changed_result.get("error", {})
                if isinstance(error_obj, dict):
                    return {
                        "result": "error",
                        "error": error_obj
                    }
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": str(error_obj) if error_obj else "Failed to determine changes via API"
                    }
                }
            
            response_data = changed_result.get("response_data", {})
            current_sha = response_data.get("current_sha")
            changed_tenants_data = response_data.get("changed_tenants", {})
            sync_all = response_data.get("sync_all", False)  # Explicit full synchronization flag
            has_changes = response_data.get("has_changes", False)
            
            # 2. If no changes and this is not first synchronization - return success
            if not has_changes and not sync_all:
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # 3. Handle first synchronization (sync_all = True)
            if sync_all:
                return await self._sync_all_public_tenants(current_sha)
            
            # 4. Update files from GitHub (only changed tenants)
            changed_tenant_ids = list(changed_tenants_data.keys())
            
            sync_files_result = await self.smart_github_sync.sync_changed_tenants(
                changed_tenant_ids=changed_tenant_ids, 
                current_sha=current_sha
            )
            
            if sync_files_result.get("result") != "success":
                return sync_files_result
            
            sync_response_data = sync_files_result.get("response_data", {})
            updated_files_count = sync_response_data.get("updated_tenants", 0)
            
            # 5. If no changed tenants to synchronize - finish
            if updated_files_count == 0:
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # 6. Synchronize only changed blocks for each tenant
            return await self.sync_changed_blocks(changed_tenants_data)
                
        except Exception as e:
            self.logger.error(f"Error in smart synchronization: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def sync_changed_blocks(self, changed_tenants_data: Dict[int, Dict[str, bool]]) -> Dict[str, Any]:
        """
        Synchronizes only changed blocks for specified tenants with DB
        Optimization: if only scenarios changed - don't restart polling
        """
        try:
            errors: list[int] = []
            for tenant_id, blocks in changed_tenants_data.items():
                res = await self.task_manager.submit_task(
                    task_id=f"sync_changed_tenant_{tenant_id}",
                    coro=(lambda t=tenant_id, b=blocks: self.block_sync_executor.sync_blocks(
                        t, b, pull_from_github=False
                    )),
                    fire_and_forget=True
                )
                if res.get("result") != "success":
                    self.logger.error(f"[Tenant-{tenant_id}] Failed to submit synchronization task: {res.get('error')}")
                    errors.append(tenant_id)

            if not errors:
                return {"result": "success"}
            else:
                return {"result": "partial_success", "error": f"Tasks not submitted for: {errors}"}
        except Exception as e:
            self.logger.error(f"Error synchronizing specific tenants: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _sync_all_public_tenants(self, current_sha: str) -> Dict[str, Any]:
        """
        Full synchronization of all public tenants (for first synchronization)
        """
        try:
            # 1. Update all public tenants from GitHub (clone and copy)
            self.logger.info("First synchronization - updating all public tenants from GitHub...")
            updated_files_count = await self.github_sync.clone_and_copy_tenants(sync_all=True)
            
            if updated_files_count == 0:
                self.logger.info("No public tenants to synchronize")
                # Update SHA even if nothing to update
                self.smart_github_sync.update_processed_sha(current_sha)
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # Update SHA in memory after successful synchronization
            self.smart_github_sync.update_processed_sha(current_sha)
            
            # 2. Get list of all public tenants from local folder
            # Folder already created on initialization, no check needed
            
            # Collect list of IDs of all public tenants
            public_tenant_ids = []
            max_system_id = self.max_system_tenant_id
            
            for tenant_dir in self.tenants_path.iterdir():
                if tenant_dir.is_dir() and tenant_dir.name.startswith('tenant_'):
                    try:
                        tenant_id = int(tenant_dir.name.replace('tenant_', ''))
                        # Filter only public tenants
                        if tenant_id > max_system_id:
                            public_tenant_ids.append(tenant_id)
                    except ValueError:
                        continue
            
            if not public_tenant_ids:
                self.logger.info("No public tenants to synchronize")
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # 3. Synchronize all public tenants with DB (asynchronously - fire_and_forget)
            self.logger.info(f"Starting synchronization of {len(public_tenant_ids)} public tenants in background...")
            errors = []
            for tenant_id in public_tenant_ids:
                blocks = {"bot": True, "scenarios": True, "storage": True, "config": True}
                res = await self.task_manager.submit_task(
                    task_id=f"sync_public_tenant_{tenant_id}",
                    coro=(lambda t=tenant_id, b=blocks: self.block_sync_executor.sync_blocks(
                        t, b, pull_from_github=False)),
                    fire_and_forget=True
                )
                if res.get("result") != "success":
                    self.logger.error(f"[Tenant-{tenant_id}] Failed to submit sync task: {res.get('error')}")
                    errors.append(tenant_id)

            if not errors:
                return {
                    "result": "success"
                }
            else:
                return {
                    "result": "partial_success",
                    "error": f"Tasks not submitted for: {errors}"
                }
            
        except Exception as e:
            self.logger.error(f"Error in full tenant synchronization: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }


