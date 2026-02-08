"""
Scenario Processor - service for processing events by scenarios
"""

import asyncio
from typing import Any, Dict, Optional

from .core.scheduled_scenario_manager import ScheduledScenarioManager
from .parsers.scenario_parser import ScenarioParser
from .scenario_engine.scenario_engine import ScenarioEngine
from .utils.data_loader import DataLoader
from .utils.scheduler import ScenarioScheduler


class ScenarioProcessor:
    """
    Service for processing events by scenarios
    - Receives processed events from event_processor
    - Determines tenant_id and loads scenarios
    - Executes actions through ActionHub
    - Parses and synchronizes tenant scenarios
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.condition_parser = kwargs['condition_parser']
        
        # Create DataLoader to pass to ScenarioEngine
        self.data_loader = DataLoader(
            logger=self.logger,
            database_manager=self.database_manager
        )
        
        # Create scenario parser
        self.scenario_parser = ScenarioParser(
            logger=self.logger,
            settings_manager=self.settings_manager,
            condition_parser=self.condition_parser
        )
        
        # Create scenario processing engine
        self.scenario_engine = ScenarioEngine(
            data_loader=self.data_loader,
            logger=self.logger,
            action_hub=self.action_hub,
            condition_parser=kwargs['condition_parser'],
            placeholder_processor=kwargs['placeholder_processor'],
            cache_manager=kwargs['cache_manager'],
            settings_manager=self.settings_manager
        )
        
        # Create scheduler for working with cron (used for validation and in manager)
        self.scheduler = ScenarioScheduler(
            logger=self.logger,
            datetime_formatter=self.datetime_formatter
        )
        
        # Create scheduled scenarios manager
        self.scheduled_manager = ScheduledScenarioManager(
            scenario_engine=self.scenario_engine,
            data_loader=self.data_loader,
            scheduler=self.scheduler,
            logger=self.logger,
            datetime_formatter=self.datetime_formatter,
            database_manager=self.database_manager,
            task_manager=kwargs['task_manager'],
            cache_manager=kwargs['cache_manager']
        )
        
        # Register ourselves in ActionHub
        self.action_hub.register('scenario_processor', self)
        
        # Service state
        self.is_running = False
        self._run_task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Main service loop"""
        try:
            self.is_running = True
            
            # Start scheduled scenarios manager
            await self.scheduled_manager.run()
            
        except asyncio.CancelledError:
            self.logger.info("ScenarioProcessor stopped")
        except Exception as e:
            self.logger.error(f"Error in ScenarioProcessor main loop: {e}")
        finally:
            self.is_running = False
    
    def shutdown(self):
        """Synchronous graceful service shutdown"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop scheduled scenarios manager
        self.scheduled_manager.shutdown()
    
    # === Actions for ActionHub ===
    
    async def sync_tenant_scenarios(self, data: dict) -> Dict[str, Any]:
        """
        Synchronize tenant scenarios: parse scenarios/*.yaml + sync to database
        Called by Tenant Hub when scenarios/ files change
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Parse scenarios files
            parse_result = await self.scenario_parser.parse_scenarios(tenant_id)
            
            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = error_obj.get('message', 'Unknown error') if isinstance(error_obj, dict) else str(error_obj)
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
            
            # Synchronize scenarios to database
            scenarios_count = len(scenario_data.get("scenarios", []))
            if scenarios_count > 0:
                sync_result = await self.action_hub.execute_action('sync_scenarios', {
                    'tenant_id': tenant_id,
                    'scenarios': scenario_data['scenarios']
                })
                
                if sync_result.get('result') != 'success':
                    error_obj = sync_result.get('error', {})
                    error_msg = error_obj.get('message', 'Unknown error') if isinstance(error_obj, dict) else str(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Error synchronizing scenarios: {error_msg}")
                    return {"result": "error", "error": error_obj}
                
                self.logger.info(f"[Tenant-{tenant_id}] Scenarios successfully synchronized ({scenarios_count} scenarios)")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] No scenarios to synchronize")
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error synchronizing tenant scenarios: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def process_scenario_event(self, data: dict) -> Dict[str, Any]:
        """
        Process event by scenarios
        """
        try:
            # Validation is done centrally in ActionRegistry
            # Process event through scenario_engine
            success = await self.scenario_engine.process_event(data)
            
            if success:
                return {"result": "success"}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to process event by scenarios"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    
    async def sync_scenarios(self, data: dict) -> Dict[str, Any]:
        """
        Sync tenant scenarios: delete old → save new → reload cache
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            scenarios = data.get('scenarios', [])
            
            # 1. Delete old scenarios
            delete_success = await self.data_loader.delete_tenant_scenarios(tenant_id)
            if not delete_success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to delete old scenarios"
                    }
                }
            
            # 2. Save new scenarios
            saved_scenarios = 0
            
            for scenario_data in scenarios:
                    # Validate cron expression if schedule specified
                    schedule = scenario_data.get('schedule')
                    if schedule:
                        if not self.scheduler.is_valid_cron(schedule):
                            self.logger.error(f"Invalid cron expression '{schedule}' for scenario {scenario_data.get('scenario_name')}")
                            continue
                    
                    scenario_id = await self.data_loader.save_scenario(tenant_id, scenario_data)
                    if scenario_id is None:
                        self.logger.error(f"Failed to create scenario {scenario_data.get('scenario_name')}")
                        continue
                    
                    saved_scenarios += 1
                    
                    # Create scenario triggers
                    trigger = scenario_data.get('trigger', [])
                    for trigger_data in trigger:
                        await self.data_loader.save_trigger(scenario_id, trigger_data)
                    
                    # Create scenario steps
                    step = scenario_data.get('step', [])
                    for step_data in step:
                        await self.data_loader.save_step(scenario_id, step_data)
            
            # 3. Reload regular scenarios cache
            scenarios_reload_success = await self.scenario_engine.reload_tenant_scenarios(tenant_id)
            if not scenarios_reload_success:
                self.logger.warning(f"Failed to reload regular scenarios cache for tenant {tenant_id}")
            
            # 4. Reload scheduled metadata
            scheduled_reload_success = await self.scheduled_manager.reload_scheduled_metadata(tenant_id)
            if not scheduled_reload_success:
                self.logger.warning(f"Failed to reload scheduled metadata for tenant {tenant_id}")
            
            # Determine result based on reload success
            if scenarios_reload_success and scheduled_reload_success:
                # Both reloads successful
                return {"result": "success"}
            elif scenarios_reload_success or scheduled_reload_success:
                # Only one reload successful - partial success
                failed_parts = []
                if not scenarios_reload_success:
                    failed_parts.append("regular scenarios")
                if not scheduled_reload_success:
                    failed_parts.append("scheduled metadata")
                
                return {
                    "result": "partial_success",
                    "error": {
                        "code": "PARTIAL_SUCCESS",
                        "message": f"Partial success: failed to reload {', '.join(failed_parts)}"
                    }
                }
            else:
                # Both reloads failed
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to reload scenarios cache"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error syncing scenarios: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def execute_scenario(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute scenario or array of scenarios by name
        
        Note: _scenario_metadata is added to data in ScenarioExecutor.execute_scenario
        and passed through action_data to this action for event processing isolation
        """
        try:
            # Validation is done centrally in ActionRegistry
            scenario_param = data.get('scenario')
            
            # Get tenant_id (already passed from context)
            tenant_id = data.get('tenant_id')
            
            # Get scenario metadata from context (added in ScenarioExecutor.execute_scenario)
            # Used for processing isolation: updating scenario structure doesn't affect already running scenarios
            scenario_metadata = data.get('_scenario_metadata')
            
            # Get return_cache parameter (default true)
            return_cache = data.get('return_cache', True)
            if not isinstance(return_cache, bool):
                return_cache = True  # By default enable cache return
            
            if isinstance(scenario_param, str):
                # Single scenario
                result, cache = await self.scenario_engine._execute_scenario_by_name(
                    tenant_id=tenant_id,
                    scenario_name=scenario_param,
                    data=data,
                    scenario_metadata=scenario_metadata
                )
                
                response_data = {
                    'scenario_result': result
                }
                
                # If return_cache enabled and cache exists - return it in response_data
                # Cache will be added to _cache[action_name] automatically in scenario_engine
                # Return cache even on error if it was partially accumulated
                if return_cache and cache:
                    # Merge cache from executed scenario into response_data
                    # cache is entire _cache from executed scenario (dict with action_name keys)
                    # This allows using data from executed scenario through _cache[action_name]
                    response_data.update(cache)
                    # Restore scenario_result in case it was overwritten from cache
                    response_data['scenario_result'] = result
                
                return {
                    'result': 'success' if result != 'error' else 'error',
                    'response_data': response_data
                }
                
            elif isinstance(scenario_param, list):
                # Array of scenarios - execute sequentially
                # IMPORTANT: For scenario array cache return is disabled, as it's hard to determine merge logic
                # and this could break scenario isolation
                last_result = 'success'
                
                # Get scenario metadata from context (added in ScenarioExecutor.execute_scenario)
                scenario_metadata = data.get('_scenario_metadata')
                
                for scenario_name in scenario_param:
                    result, _ = await self.scenario_engine._execute_scenario_by_name(
                        tenant_id=tenant_id,
                        scenario_name=scenario_name,
                        data=data,
                        scenario_metadata=scenario_metadata
                    )
                    
                    # If technical error - interrupt
                    if result == 'error':
                        return {'result': 'error'}
                    
                    # If abort or stop - interrupt entire chain and pass result
                    if result in ['abort', 'stop']:
                        return {
                            'result': 'success',
                            'response_data': {
                                'scenario_result': result
                            }
                        }
                    
                    # Save result (success, break)
                    last_result = result
                
                # For scenario array cache is not returned (isolation preserved)
                return {
                    'result': 'success',
                    'response_data': {
                        'scenario_result': last_result
                    }
                }
            
            else:
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'scenario must be string or array'
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error executing scenario: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Internal error: {str(e)}'
                }
            }
    
    async def wait_for_action(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wait for async action completion by action_id
        Returns main action result AS IS (as if it executed directly)
        """
        try:
            # Validation is done centrally in ActionRegistry
            action_id = data.get('action_id')
            timeout = data.get('timeout')  # Optional timeout in seconds
            
            # Get scenario context from data
            async_action = data.get('_async_action', {})
            
            if action_id not in async_action:
                return {
                    'result': 'error',
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': f'Async action with action_id={action_id} not found'
                    }
                }
            
            future = async_action[action_id]
            
            # Check that it's a Future
            if not isinstance(future, asyncio.Future):
                return {
                    'result': 'error',
                    'error': {
                        'code': 'INVALID_STATE',
                        'message': f'Invalid Future type for action_id={action_id}'
                    }
                }
            
            # If action already completed - immediately return result AS IS
            if future.done():
                try:
                    result = future.result()
                    # Return main action result AS IS (fully copy structure)
                    # Result will get into data through merge response_data in scenario_engine
                    return result
                except Exception as e:
                    return {
                        'result': 'error',
                        'error': {
                            'code': 'INTERNAL_ERROR',
                            'message': str(e)
                        }
                    }
            
            # Wait for completion with timeout or without
            try:
                if timeout:
                    result = await asyncio.wait_for(future, timeout=float(timeout))
                else:
                    result = await future
                
                # Return main action result AS IS (fully copy structure)
                # Result will get into data through merge response_data in scenario_engine
                return result
                
            except asyncio.TimeoutError:
                # Timeout - this is wait_for_action error, return waiting error
                return {
                    'result': 'timeout',
                    'error': {
                        'code': 'TIMEOUT',
                        'message': f'Timeout exceeded for action_id={action_id}'
                    }
                }
            except Exception as e:
                # Error on wait - return wait_for_action error
                return {
                    'result': 'error',
                    'error': {
                        'code': 'INTERNAL_ERROR',
                        'message': str(e)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error waiting for async action: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Internal error: {str(e)}'
                }
            }