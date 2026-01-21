"""
Core module for event processing by scenarios
Orchestrator - coordinates all components for event processing by scenarios
"""

from typing import Any, Dict, Optional

from .cache_manager import CacheManager
from .scenario_cache import ScenarioCache
from .scenario_executor import ScenarioExecutor
from .scenario_finder import ScenarioFinder
from .scenario_loader import ScenarioLoader
from .step_executor import StepExecutor
from .transition_handler import TransitionHandler


class ScenarioEngine:
    """
    Event processing engine by scenarios for multiple tenants
    Orchestrator - coordinates all components:
    - ScenarioCache - scenario caching
    - ScenarioLoader - load scenarios from database
    - ScenarioFinder - find scenarios by events
    - ScenarioExecutor - execute scenarios
    """
    
    def __init__(self, data_loader, logger, action_hub, condition_parser, placeholder_processor, cache_manager, settings_manager):
        self.logger = logger
        self.action_hub = action_hub
        self.condition_parser = condition_parser
        self.placeholder_processor = placeholder_processor
        self.data_loader = data_loader
        
        # Initialize components
        self.cache = ScenarioCache(self.logger, cache_manager, settings_manager)
        self.loader = ScenarioLoader(self.logger, self.data_loader, self.condition_parser)
        self.finder = ScenarioFinder(self.logger, self.condition_parser)
        
        # Create execution components
        cache_manager = CacheManager(self.logger, self.action_hub)
        step_executor = StepExecutor(self.logger, self.action_hub, self.placeholder_processor)
        transition_handler = TransitionHandler(self.logger)
        
        self.executor = ScenarioExecutor(
            self.logger,
            step_executor,
            transition_handler,
            cache_manager
        )
    
    async def process_event(self, event: Dict[str, Any]) -> bool:
        """Process event by scenarios"""
        try:
            # Determine tenant_id from event
            tenant_id = self.finder.extract_tenant_id(event)
            if not tenant_id:
                self.logger.warning("Failed to determine tenant_id from event")
                return False
            
            # Load tenant scenarios (if not yet loaded)
            if not await self.cache.has_tenant_cache(tenant_id):
                cache_data = await self.loader.load_tenant_scenarios(tenant_id)
                await self.cache.set_tenant_cache(tenant_id, cache_data)
            
            # Get scenario metadata for isolated event processing
            scenario_metadata = await self.cache.get_scenario_metadata(tenant_id)
            if not scenario_metadata:
                self.logger.warning(f"Failed to get scenario metadata for tenant {tenant_id}")
                return False
            
            # Find matching scenarios (use metadata)
            scenario_ids = await self.finder.find_scenarios_by_event(tenant_id, event, scenario_metadata)
            
            if scenario_ids:
                # Execute found scenarios (use metadata)
                for scenario_id in scenario_ids:
                    result, _ = await self.executor.execute_scenario(
                        tenant_id=tenant_id,
                        scenario_id=scenario_id,
                        event=event,
                        scenario_metadata=scenario_metadata,
                        execute_scenario_by_name_func=self._execute_scenario_by_name_wrapper
                    )
                    
                    # Check scenario execution result
                    if result == 'stop':
                        # stop - interrupt entire event processing (all scenarios)
                        return True
                    elif result == 'abort':
                        # abort - interrupt entire execution chain of current scenario (including nested)
                        # but continue with other scenarios from other triggers
                        continue
                    elif result == 'break':
                        # break - interrupt only current scenario, continue with others
                        continue
                    elif result == 'error':
                        self.logger.warning(f"Error executing scenario {scenario_id}")
                        continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            return False
    
    async def _execute_scenario_by_name_wrapper(self, tenant_id: int, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
        """Wrapper for executing scenario by name. Used for passing to ScenarioExecutor for jump_to_scenario transitions"""
        return await self.executor.execute_scenario_by_name(
            tenant_id=tenant_id,
            scenario_name=scenario_name,
            data=data,
            scenario_metadata=scenario_metadata,
            execute_scenario_func=self._execute_scenario_wrapper
        )
    
    async def _execute_scenario_wrapper(self, tenant_id: int, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
        """Wrapper for executing scenario by ID. Used for passing to ScenarioExecutor"""
        return await self.executor.execute_scenario(
            tenant_id=tenant_id,
            scenario_id=scenario_id,
            event=event,
            scenario_metadata=scenario_metadata,
            execute_scenario_by_name_func=self._execute_scenario_by_name_wrapper
        )
    
    async def _execute_scenario_by_name(self, tenant_id: int, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any] = None) -> tuple[str, Optional[Dict[str, Any]]]:
        """Find and execute scenario by name for specific tenant. Public method for external use"""
        if scenario_metadata is None:
            # If metadata not provided, get it
            scenario_metadata = await self.cache.get_scenario_metadata(tenant_id)
            if not scenario_metadata:
                self.logger.warning(f"Failed to get scenario metadata for tenant {tenant_id}")
                return ('error', None)
        
        return await self.executor.execute_scenario_by_name(
            tenant_id=tenant_id,
            scenario_name=scenario_name,
            data=data,
            scenario_metadata=scenario_metadata,
            execute_scenario_func=self._execute_scenario_wrapper
        )
    
    async def reload_tenant_scenarios(self, tenant_id: int) -> bool:
        """Reload scenario cache for specific tenant"""
        try:
            # Clear cache
            if not await self.cache.reload_tenant_scenarios(tenant_id):
                return False
            
            # Reload
            cache_data = await self.loader.load_tenant_scenarios(tenant_id)
            await self.cache.set_tenant_cache(tenant_id, cache_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error reloading scenarios for tenant {tenant_id}: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            await self.cache.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up: {e}")
