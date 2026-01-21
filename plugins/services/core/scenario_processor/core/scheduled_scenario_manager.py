"""
Module for managing scheduled scenarios
- Cache scheduled scenario metadata
- Background loop for checking and launching
- Update metadata after execution
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional


class ScheduledScenarioManager:
    """
    Manager for scheduled scenarios
    - Cache scheduled scenario metadata
    - Check schedule and launch scenarios
    - Update metadata after execution
    """
    
    def __init__(self, scenario_engine, data_loader, scheduler, logger, datetime_formatter, database_manager, task_manager, cache_manager):
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        self.database_manager = database_manager
        self.task_manager = task_manager
        self.cache_manager = cache_manager
        
        self.scenario_engine = scenario_engine
        self.data_loader = data_loader
        self.scheduler = scheduler
        
        # Cache of scheduled scenario metadata
        # {scenario_id: {'cron': str, 'last_run': datetime | None, 'next_run': datetime, 'tenant_id': int, 'scenario_name': str, 'is_running': bool}}
        self._scheduled_metadata: Dict[int, Dict[str, Any]] = {}
        
        # Service state
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Main loop for scheduled scenario manager"""
        try:
            self.is_running = True
            
            # Load all scheduled scenarios on startup
            await self.load_all_scheduled_scenarios()
            
            # Start background loop for checking scheduled scenarios
            self._scheduler_task = asyncio.create_task(self._run_scheduler_loop())
            await self._scheduler_task
            
        except asyncio.CancelledError:
            self.logger.info("ScheduledScenarioManager stopped")
        except Exception as e:
            self.logger.error(f"Error in ScheduledScenarioManager main loop: {e}")
        finally:
            self.is_running = False
    
    def shutdown(self):
        """Synchronous graceful shutdown of manager"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping ScheduledScenarioManager...")
        self.is_running = False
        
        # Cancel background loop if running
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
        
        self.logger.info("ScheduledScenarioManager stopped")
    
    async def load_all_scheduled_scenarios(self):
        """Load all scheduled scenarios on service startup"""
        try:
            # Load all scheduled scenarios (no tenant filter)
            scheduled_scenarios = await self.data_loader.load_scheduled_scenarios()
            
            # Process loaded scenarios directly
            loaded_count = 0
            tenants_count = set()
            
            for scenario in scheduled_scenarios:
                scenario_id = scenario['id']
                cron = scenario['schedule']
                last_run = scenario.get('last_scheduled_run')
                tenant_id = scenario['tenant_id']
                
                tenants_count.add(tenant_id)
                
                # Calculate next_run
                if last_run:
                    next_run = await self.scheduler.get_next_run_time(cron, last_run)
                else:
                    # If no runs yet - from current local time
                    now = await self.datetime_formatter.now_local()
                    next_run = await self.scheduler.get_next_run_time(cron, now)
                
                if next_run is None:
                    self.logger.warning(f"Failed to calculate next_run for scenario {scenario_id} with cron '{cron}'")
                    continue
                
                # Update cache (bot_id obtained from DB on launch)
                self._scheduled_metadata[scenario_id] = {
                    'cron': cron,
                    'last_run': last_run,
                    'next_run': next_run,
                    'tenant_id': tenant_id,
                    'scenario_name': scenario['scenario_name'],
                    'is_running': False
                }
                loaded_count += 1
            
            if loaded_count > 0:
                self.logger.info(f"Loaded ({loaded_count} scheduled scenarios) for ({len(tenants_count)} tenants)")
            
        except Exception as e:
            self.logger.error(f"Error loading all scheduled scenarios on startup: {e}")
    
    async def reload_scheduled_metadata(self, tenant_id: int) -> bool:
        """
        Reload scheduled scenario metadata for tenant
        """
        try:
            # Remove all old scenario_id for this tenant_id from cache
            for sid in list(self._scheduled_metadata.keys()):
                if self._scheduled_metadata[sid]['tenant_id'] == tenant_id:
                    del self._scheduled_metadata[sid]
            
            # Load all scheduled scenarios from DB for tenant
            scheduled_scenarios = await self.data_loader.load_scheduled_scenarios(tenant_id)
            
            loaded_count = 0
            for scenario in scheduled_scenarios:
                scenario_id = scenario['id']
                cron = scenario['schedule']
                last_run = scenario.get('last_scheduled_run')
                
                # Calculate next_run
                if last_run:
                    next_run = await self.scheduler.get_next_run_time(cron, last_run)
                else:
                    # If no runs yet - from current local time
                    now = await self.datetime_formatter.now_local()
                    next_run = await self.scheduler.get_next_run_time(cron, now)
                
                if next_run is None:
                    self.logger.warning(f"Failed to calculate next_run for scenario {scenario_id} with cron '{cron}'")
                    continue
                
                # Update cache (bot_id obtained from DB on launch)
                self._scheduled_metadata[scenario_id] = {
                    'cron': cron,
                    'last_run': last_run,
                    'next_run': next_run,
                    'tenant_id': scenario['tenant_id'],
                    'scenario_name': scenario['scenario_name'],
                    'is_running': False
                }
                loaded_count += 1
            
            self.logger.info(f"[Tenant-{tenant_id}] Loaded ({loaded_count} scheduled scenarios)")
            return True
            
        except Exception as e:
            self.logger.error(f"Error reloading scheduled metadata for tenant {tenant_id}: {e}")
            return False
    
    async def _run_scheduler_loop(self):
        """Background loop for checking scheduled scenarios"""
        while True:
            try:
                await self._check_scheduled_scenarios()
                
                # Wait until start of next minute
                now = await self.datetime_formatter.now_local()
                seconds_to_wait = 60 - now.second
                await asyncio.sleep(seconds_to_wait)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduler loop stopped")
                break
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_scheduled_scenarios(self):
        """Check and launch scheduled scenarios"""
        try:
            # Get current local time
            now = await self.datetime_formatter.now_local()
            
            # Round to start of minute for accuracy
            now = now.replace(second=0, microsecond=0)
            
            # Filter scenarios that need to be launched
            scenarios_to_run = []
            
            for scenario_id, metadata in self._scheduled_metadata.items():
                # Check by next_run (faster than checking cron every time)
                # And check that scenario is not already running
                if metadata['next_run'] <= now and not metadata.get('is_running', False):
                    scenarios_to_run.append({
                        'scenario_id': scenario_id,
                        **metadata
                    })
            
            # Launch found scenarios through TaskManager
            # Use action queue for scheduled scenarios
            for scenario_info in scenarios_to_run:
                scenario_id = scenario_info['scenario_id']
                
                # Create async wrapper for TaskManager (like in ActionRegistry._create_action_wrapper)
                # Fix scenario_info via default parameter (evaluated at function creation)
                async def scenario_wrapper(sc_info=scenario_info):
                    await self._run_scheduled_scenario(sc_info)
                
                # Submit to action queue with fire_and_forget=True
                asyncio.create_task(
                    self.task_manager.submit_task(
                        task_id=f"scheduled_scenario_{scenario_id}",
                        coro=scenario_wrapper,
                        queue_name='action',
                        fire_and_forget=True
                    )
                )
                
        except Exception as e:
            self.logger.error(f"Error checking scheduled scenarios: {e}")
    
    async def _run_scheduled_scenario(self, scenario_info: Dict[str, Any]):
        """Launch scheduled scenario"""
        scenario_id = scenario_info['scenario_id']
        tenant_id = scenario_info['tenant_id']
        scenario_name = scenario_info['scenario_name']
        cron = scenario_info['cron']
        
        # Check again that scenario is not running (race condition protection)
        if self._scheduled_metadata.get(scenario_id, {}).get('is_running', False):
            return
        
        # Mark scenario as running
        self._scheduled_metadata[scenario_id]['is_running'] = True
        
        try:
            # Create synthetic event for scheduled scenario
            scheduled_at = await self.datetime_formatter.now_local()
            
            # Get bot_id through cache_manager (like in TenantCache)
            # Step 1: Try to get bot_id from mapping tenant:{tenant_id}:bot_id
            tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
            cached_bot_id = await self.cache_manager.get(tenant_bot_id_key)
            
            bot_id = None
            if cached_bot_id:
                # Mapping exists in cache
                bot_id = cached_bot_id
            else:
                # Mapping not found - get from DB
                master_repo = self.database_manager.get_master_repository()
                bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
                if not bot_data:
                    self.logger.error(f"[Tenant-{tenant_id}] Bot not found for scheduled scenario '{scenario_name}' (ID: {scenario_id})")
                    return
                # Raw data from DB uses 'id'
                bot_id = bot_data.get('id')
                if not bot_id:
                    self.logger.error(f"[Tenant-{tenant_id}] Bot found but bot_id missing for scheduled scenario '{scenario_name}' (ID: {scenario_id})")
                    return
                # Save mapping to cache (TTL from settings, but use large TTL for simplicity)
                await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=315360000)
            
            if not bot_id:
                self.logger.error(f"[Tenant-{tenant_id}] Failed to get bot_id for scheduled scenario '{scenario_name}' (ID: {scenario_id})")
                return
            
            if not bot_id:
                self.logger.error(f"[Tenant-{tenant_id}] Failed to get bot_id for scheduled scenario '{scenario_name}' (ID: {scenario_id})")
                return
            
            # Get tenant config from shared cache with DB fallback
            cache_key = f"tenant:{tenant_id}:config"
            tenant_config = await self.cache_manager.get(cache_key)
            
            # If cache not found - load from DB (fallback to solve desynchronization problem)
            if tenant_config is None:
                self.logger.warning(f"[Tenant-{tenant_id}] Tenant config not found in cache for scheduled scenario '{scenario_name}', loading from DB")
                
                try:
                    master_repo = self.database_manager.get_master_repository()
                    tenant_data = await master_repo.get_tenant_by_id(tenant_id)
                    
                    if tenant_data:
                        # Form config dictionary from all DB fields (exclude system fields)
                        config = {}
                        excluded_fields = {'id', 'processed_at'}
                        for key, value in tenant_data.items():
                            if key not in excluded_fields and value is not None:
                                config[key] = value
                        
                        # Don't save to cache - TenantCache manages it
                        # This is a rare case when cache is missing, so just return data from DB
                        tenant_config = config
                except Exception as e:
                    self.logger.error(f"[Tenant-{tenant_id}] Error loading tenant config from DB for scheduled scenario '{scenario_name}': {e}")
            
            # Form system fields (like in regular events)
            system_fields = {
                'tenant_id': tenant_id,
                'bot_id': bot_id
            }
            
            # Convert scheduled_at to ISO string of local time
            scheduled_at_iso = await self.datetime_formatter.to_iso_local_string(scheduled_at)
            
            synthetic_event = {
                'system': system_fields,
                'tenant_id': tenant_id,
                'bot_id': bot_id,
                'scheduled_at': scheduled_at_iso,  # ISO format of local time
                'scheduled_scenario_id': scenario_id,
                'scheduled_scenario_name': scenario_name
            }
            
            # Add tenant config to event (if present)
            if tenant_config:
                synthetic_event['_config'] = tenant_config
            
            # Launch through scenario_engine.execute_scenario_by_name
            result, _ = await self.scenario_engine._execute_scenario_by_name(
                tenant_id=tenant_id,
                scenario_name=scenario_name,
                data=synthetic_event
            )
            
            # Get completion time
            completion_time = await self.datetime_formatter.now_local()
            
            # Log error if present, but continue metadata update
            if result == 'error':
                self.logger.warning(f"[Tenant-{tenant_id}] Error executing scheduled scenario '{scenario_name}' (ID: {scenario_id})")
            
            # Update last_run always (both in cache and DB) - launch occurred regardless of result
            # This guarantees predictable behavior on service restart
            self._scheduled_metadata[scenario_id]['last_run'] = scheduled_at
            await self._update_last_run_in_db(scenario_id, scheduled_at)
            
            # Calculate next_run from completion time (standard cron behavior)
            # Missed launches are simply skipped, next will be in future
            # Update always, even on error, to avoid repeated launches
            next_run = await self.scheduler.get_next_run_time(cron, completion_time)
            if next_run:
                self._scheduled_metadata[scenario_id]['next_run'] = next_run
            else:
                self.logger.warning(f"Failed to calculate next_run for scenario {scenario_id}")
                
        except Exception as e:
            self.logger.error(f"Error launching scheduled scenario {scenario_id}: {e}")
        finally:
            # Clear running flag
            self._scheduled_metadata[scenario_id]['is_running'] = False
    
    async def _update_last_run_in_db(self, scenario_id: int, last_run: datetime):
        """Update last_scheduled_run in DB"""
        try:
            master_repo = self.database_manager.get_master_repository()
            await master_repo.update_scenario_last_run(scenario_id, last_run)
        except Exception as e:
            self.logger.error(f"Error updating last_scheduled_run for scenario {scenario_id}: {e}")

