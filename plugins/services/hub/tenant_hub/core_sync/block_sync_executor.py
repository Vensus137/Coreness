"""
Block Sync Executor - executor for tenant block synchronization
Executes synchronization of separate blocks (bot/scenarios) for performance optimization
"""

from typing import Any, Dict


class BlockSyncExecutor:
    """
    Executor for tenant block synchronization
    Optimizes synchronization: synchronizes only changed blocks (bot/scenarios)
    """
    
    def __init__(self, logger, tenant_parser, action_hub, github_sync, settings_manager, tenant_cache, storage_manager):
        self.logger = logger
        self.tenant_parser = tenant_parser
        self.action_hub = action_hub
        self.github_sync = github_sync
        self.settings_manager = settings_manager
        self.tenant_cache = tenant_cache
        self.storage_manager = storage_manager
        
        # Get system tenant boundary once on initialization
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 100)
    
    def _extract_error_message(self, error: dict) -> str:
        """
        Extract error message from error object
        """
        return error.get('message', 'Unknown error') if error else 'Unknown error'
    
    async def _prepare_tenant_data(self, tenant_id: int, pull_from_github: bool = False) -> Dict[str, Any]:
        """
        Prepare tenant data: pull from GitHub (optional) + create tenant if it doesn't exist
        """
        try:
            # For system tenants always skip pull from GitHub
            if pull_from_github and tenant_id <= self.max_system_tenant_id:
                pull_from_github = False
            
            # Update data from GitHub (if needed)
            if pull_from_github:
                self.logger.info(f"[Tenant-{tenant_id}] Updating data from GitHub...")
                pull_result = await self.github_sync.pull_tenant(tenant_id)
                
                if pull_result.get("result") != "success":
                    error_msg = self._extract_error_message(pull_result.get('error', 'Unknown error'))
                    self.logger.warning(f"[Tenant-{tenant_id}] Error updating from GitHub: {error_msg}, continuing with local data")
                else:
                    self.logger.info(f"[Tenant-{tenant_id}] Data from GitHub updated")
            
            # Create tenant if it doesn't exist
            sync_tenant_result = await self.action_hub.execute_action('sync_tenant_data', {'tenant_id': tenant_id})
            
            if sync_tenant_result.get('result') != 'success':
                error_obj = sync_tenant_result.get('error', {})
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Error creating/synchronizing tenant: {error_msg}")
                return {"result": "error", "error": error_obj}
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error preparing tenant data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _sync_scenarios_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Internal scenarios block synchronization (without data preparation)
        """
        try:
            # Parse scenarios
            parse_result = await self.tenant_parser.parse_scenarios(tenant_id)

            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Error parsing scenarios: {error_msg}")
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Failed to parse scenarios for tenant {tenant_id}: {error_msg}"
                    }
                }

            scenario_data = parse_result.get('response_data')

            if not scenario_data:
                self.logger.error(f"[Tenant-{tenant_id}] No scenario data after parsing")
                return {"result": "error", "error": f"Failed to get scenario data for tenant {tenant_id}"}

            # Synchronize scenarios
            scenarios_count = len(scenario_data.get("scenarios", []))
            if scenarios_count > 0:

                sync_result = await self.action_hub.execute_action('sync_scenarios', {
                    'tenant_id': tenant_id,
                    'scenarios': scenario_data['scenarios']
                })

                if sync_result.get('result') != 'success':
                    error_obj = sync_result.get('error', {})
                    error_msg = self._extract_error_message(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing scenarios: {error_msg}")
                    return {"result": "error", "error": error_obj}

                self.logger.info(f"[Tenant-{tenant_id}] Scenarios successfully synchronized")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] No scenarios to synchronize")

            return {"result": "success"}

        except Exception as e:
            self.logger.error(f"Error synchronizing scenarios: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _sync_bot_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Internal bot block synchronization (without data preparation)
        """
        try:
            # Parse bot data
            parse_result = await self.tenant_parser.parse_bot(tenant_id)

            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Failed to parse bot data for tenant {tenant_id}: {error_msg}"
                    }
                }

            bot_data = parse_result.get('response_data')

            if not bot_data:
                return {"result": "error", "error": f"Failed to get bot data for tenant {tenant_id}"}

            # Synchronize bot configuration
            bot_id = None
            if bot_data.get("bot"):
                self.logger.info(f"[Tenant-{tenant_id}] Synchronizing bot configuration...")

                bot_config = bot_data.get('bot', {}).copy()
                bot_config['tenant_id'] = tenant_id

                sync_bot_result = await self.action_hub.execute_action('sync_bot_config', bot_config)

                if sync_bot_result.get('result') != 'success':
                    error_obj = sync_bot_result.get('error', {})
                    error_msg = self._extract_error_message(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing bot configuration: {error_msg}")
                    return {"result": "error", "error": error_obj}

                bot_id = sync_bot_result.get('response_data', {}).get('bot_id')
                self.logger.info(f"[Tenant-{tenant_id}] Bot configuration successfully synchronized")

                # Synchronize bot commands
                if bot_data.get("bot_commands"):
                    commands_count = len(bot_data.get("bot_commands", []))
                    if commands_count > 0:
                        sync_result = await self.action_hub.execute_action('sync_bot_commands', {
                            'bot_id': bot_id,
                            'command_list': bot_data['bot_commands']
                        })
                        if sync_result.get('result') != 'success':
                            error_msg = self._extract_error_message(sync_result.get('error', 'Unknown error'))
                            self.logger.warning(f"[Tenant-{tenant_id}] Error synchronizing bot commands: {error_msg}")
                        else:
                            self.logger.info(f"[Tenant-{tenant_id}] Bot commands successfully synchronized")
                    else:
                        self.logger.info(f"[Tenant-{tenant_id}] No bot commands to synchronize")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] No bot configuration to synchronize")

            return {"result": "success"}

        except Exception as e:
            self.logger.error(f"Error synchronizing bot: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_storage_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Internal storage block synchronization (without data preparation)
        """
        try:
            # Parse storage
            parse_result = await self.tenant_parser.parse_storage(tenant_id)
            
            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Error parsing storage: {error_msg}")
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Failed to parse storage for tenant {tenant_id}: {error_msg}"
                    }
                }
            
            storage_data = parse_result.get('response_data', {}).get('storage', {})
            
            if not storage_data:
                self.logger.info(f"[Tenant-{tenant_id}] No storage data to synchronize")
                return {"result": "success"}
            
            # Synchronize storage
            groups_count = len(storage_data)
            if groups_count > 0:

                success = await self.storage_manager.sync_storage(tenant_id, storage_data)
                
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing storage")
                    return {
                        "result": "error",
                        "error": {
                            "code": "SYNC_ERROR",
                            "message": "Failed to synchronize storage"
                        }
                    }
                
                self.logger.info(f"[Tenant-{tenant_id}] Storage successfully synchronized")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] No storage to synchronize")
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error synchronizing storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_config_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Internal tenant config block synchronization (without data preparation)
        """
        try:
            # Parse tenant config (config.yaml)
            parse_result = await self.tenant_parser.parse_tenant_config(tenant_id)
            
            config = None
            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                # config.yaml file is optional, so don't return error
                self.logger.warning(f"[Tenant-{tenant_id}] Error parsing tenant config: {error_msg}, updating cache from DB")
            else:
                config = parse_result.get('response_data', {})
            
            if not config:
                # No config in file - update cache from DB (will create empty config in cache if it doesn't exist)
                self.logger.info(f"[Tenant-{tenant_id}] No config in configuration, updating cache from DB")
                await self.tenant_cache.update_tenant_config_cache(tenant_id)
                return {"result": "success"}
            
            # Synchronize config through action (like in other blocks)
            update_data = {
                'tenant_id': tenant_id,
                **config
            }
            
            sync_result = await self.action_hub.execute_action('update_tenant_config', update_data)
            
            if sync_result.get('result') != 'success':
                error_obj = sync_result.get('error', {})
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing tenant config: {error_msg}")
                return {"result": "error", "error": error_obj}
            
            self.logger.info(f"[Tenant-{tenant_id}] Tenant config successfully synchronized")
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant config: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_blocks(self, tenant_id: int, blocks: Dict[str, bool], pull_from_github: bool = False) -> Dict[str, Any]:
        """
        Synchronize specified tenant blocks with optimization
        """
        try:
            bot_changed = blocks.get("bot", False)
            scenarios_changed = blocks.get("scenarios", False)
            storage_changed = blocks.get("storage", False)
            config_changed = blocks.get("config", False)
            
            if not bot_changed and not scenarios_changed and not storage_changed and not config_changed:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No blocks to synchronize"
                    }
                }
            
            self.logger.info(
                f"Synchronizing tenant [Tenant-{tenant_id}] "
                f"(bot: {'+' if bot_changed else '-'}, scenarios: {'+' if scenarios_changed else '-'}, "
                f"storage: {'+' if storage_changed else '-'}, config: {'+' if config_changed else '-'})..."
            )
            
            # Data preparation (pull + tenant creation) executed once
            prepare_result = await self._prepare_tenant_data(tenant_id, pull_from_github)
            if prepare_result.get("result") != "success":
                error_obj = prepare_result.get("error", {})
                await self.tenant_cache.set_last_failed(tenant_id, error_obj)
                return {"result": "error", "error": error_obj}

            # Synchronize blocks as needed
            # IMPORTANT: First synchronize scenarios, storage and config, then bot (which starts polling)
            # This guarantees all data is ready before event processing starts
            
            if scenarios_changed:
                scenarios_result = await self._sync_scenarios_block(tenant_id)
                if scenarios_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, scenarios_result.get("error"))
                    return scenarios_result
            
            if storage_changed:
                storage_result = await self._sync_storage_block(tenant_id)
                if storage_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, storage_result.get("error"))
                    return storage_result
            
            if config_changed:
                config_result = await self._sync_config_block(tenant_id)
                if config_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, config_result.get("error"))
                    return config_result
            
            # Bot synchronization at the end - starts polling/webhooks after all data is ready
            if bot_changed:
                bot_result = await self._sync_bot_block(tenant_id)
                if bot_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, bot_result.get("error"))
                    return bot_result
            
            await self.tenant_cache.set_last_updated(tenant_id)
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant blocks {tenant_id}: {e}")
            error_obj = {
                "code": "INTERNAL_ERROR",
                "message": f"Internal error: {str(e)}"
            }
            await self.tenant_cache.set_last_failed(tenant_id, error_obj)
            return {"result": "error", "error": error_obj}
