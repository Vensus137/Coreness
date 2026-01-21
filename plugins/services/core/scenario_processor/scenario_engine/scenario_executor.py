"""
Scenario executor
Executes scenarios, coordinates step execution and transition handling
"""

from typing import Any, Callable, Dict, Optional, Tuple


class ScenarioExecutor:
    """
    Scenario executor
    - Execute scenarios by ID and by name
    - Coordinate step execution
    - Handle transitions between steps
    """
    
    def __init__(self, logger, step_executor, transition_handler, cache_manager):
        self.logger = logger
        self.step_executor = step_executor
        self.transition_handler = transition_handler
        self.cache_manager = cache_manager
    
    async def execute_scenario(self, tenant_id: int, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Execute scenario by ID for specific tenant. Returns tuple (result, cache)"""
        try:
            # Use scenario metadata for isolated processing
            scenario_data = scenario_metadata['scenario_index'].get(scenario_id)
            if not scenario_data:
                self.logger.warning(f"Scenario {scenario_id} not found in index for tenant {tenant_id}")
                return ('error', None)
            
            # Get scenario steps (tuple)
            step = scenario_data.get('step', ())
            if not step:
                self.logger.warning(f"Scenario {scenario_id} has no steps for tenant {tenant_id}")
                return ('error', None)
            
            # Sort steps by order (sorted works with tuple, returns list)
            sorted_step = sorted(step, key=lambda x: x.get('step_order', 0))
            
            scenario_name = scenario_data.get('data', {}).get('name', f'Scenario {scenario_id}')
            
            # Create copy of event for accumulating data between steps
            data = event.copy()
            data['tenant_id'] = tenant_id  # Add tenant_id to data
            data['_scenario_metadata'] = scenario_metadata  # Add scenario metadata for use in execute_scenario action
            
            # Initialize scenario chain for debugging
            # If chain already exists (when jumping from another scenario), use it, otherwise create new one
            if 'scenario_chain' not in data or not isinstance(data.get('scenario_chain'), list):
                data['scenario_chain'] = [scenario_name]
            else:
                # Add current scenario to chain (copy array to avoid modifying original)
                data['scenario_chain'] = data['scenario_chain'].copy()
                data['scenario_chain'].append(scenario_name)
            
            # Execute each step
            # Use while instead of for to support negative move_steps values for going back
            i = 0
            while i < len(sorted_step):
                step_data = sorted_step[i]
                params = step_data.get('params', {})
                
                # Execute step
                step_result = await self.step_executor.execute_step(step_data, data)
                transition = step_data.get('transition', [])
                
                # Merge response_data into _cache
                response_data = step_result.get('response_data', {})
                if response_data:
                    self.cache_manager.merge_response_data(
                        response_data=response_data,
                        data=data,
                        action_name=step_data.get('action_name'),
                        params=params
                    )
                
                # Add error from action to last_error attribute (only if it's not None)
                error = step_result.get('error')
                if error is not None:
                    data['last_error'] = error
                
                # Add action execution result to last_result attribute (for debugging)
                result = step_result.get('result')
                if result is not None:
                    data['last_result'] = result
                
                # Check response_data for abort/stop from execute_scenario
                scenario_result = response_data.get('scenario_result')
                if scenario_result == 'abort':
                    # abort - interrupt entire execution chain of current scenario
                    cache = self.cache_manager.extract_cache(data)
                    return ('abort', cache)
                elif scenario_result == 'stop':
                    # stop - interrupt entire event processing
                    cache = self.cache_manager.extract_cache(data)
                    return ('stop', cache)
                
                # Process transitions based on step result
                transition_result = await self.transition_handler.process_transitions(
                    step_result.get('result'),
                    transition
                )
                transition_action = transition_result.get('action', 'continue')
                transition_value = transition_result.get('value')
                
                # Process transitions
                if transition_action == 'stop':
                    result, cache = await self.transition_handler.handle_stop_abort_break('stop', data)
                    return (result, cache)
                    
                elif transition_action == 'abort':
                    result, cache = await self.transition_handler.handle_stop_abort_break('abort', data)
                    return (result, cache)
                    
                elif transition_action == 'break':
                    result, cache = await self.transition_handler.handle_stop_abort_break('break', data)
                    return (result, cache)
                    
                elif transition_action == 'jump_to_scenario':
                    result, cache = await self.transition_handler.handle_jump_to_scenario(
                        transition_value=transition_value,
                        tenant_id=tenant_id,
                        data=data,
                        scenario_metadata=scenario_metadata,
                        execute_scenario_by_name_func=execute_scenario_by_name_func
                    )
                    
                    if result == 'continue':
                        # Continue with next step
                        i += 1
                        continue
                    else:
                        # stop, abort or success - return result
                        return (result, cache)
                    
                elif transition_action == 'move_steps':
                    result, new_index, cache = await self.transition_handler.handle_move_steps(
                        transition_value=transition_value,
                        current_index=i,
                        sorted_step=sorted_step,
                        data=data
                    )
                    
                    if result == 'continue':
                        # Continue with new index
                        i = new_index
                        continue
                    else:
                        # success - finish scenario
                        return ('success', cache)
                    
                elif transition_action == 'jump_to_step':
                    result, new_index, cache = await self.transition_handler.handle_jump_to_step(
                        transition_value=transition_value,
                        sorted_step=sorted_step,
                        data=data
                    )
                    
                    if result == 'continue':
                        # Continue with new index
                        i = new_index
                        continue
                    else:
                        # success - finish scenario
                        return ('success', cache)
                
                # Continue with next step (continue)
                i += 1
            
            # Return only _cache from final data
            cache = self.cache_manager.extract_cache(data)
            return ('success', cache)
                
        except Exception as e:
            self.logger.error(f"Error executing scenario {scenario_id} for tenant {tenant_id}: {e}")
            # Try to save partially accumulated cache if it exists
            try:
                cache = self.cache_manager.extract_cache(data)
            except (NameError, UnboundLocalError):
                cache = None
            return ('error', cache)
    
    async def execute_scenario_by_name(self, tenant_id: int, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Find and execute scenario by name for specific tenant. Returns tuple (result, cache)"""
        try:
            # Use scenario metadata for isolated processing
            if scenario_metadata is None:
                return ('error', None)
            
            scenario_name_index = scenario_metadata['scenario_name_index']
            
            # Fast O(1) search via index
            if scenario_name not in scenario_name_index:
                self.logger.warning(f"Scenario '{scenario_name}' not found for tenant {tenant_id}")
                return ('error', None)
            
            target_scenario_id = scenario_name_index[scenario_name]
            
            # Create copy of data for passing to scenario (to avoid modifying original)
            # Scenario chain will be updated in execute_scenario
            data = data.copy()
            
            result, cache = await execute_scenario_func(
                tenant_id=tenant_id,
                scenario_id=target_scenario_id,
                event=data,
                scenario_metadata=scenario_metadata
            )
            
            # Return result and only _cache
            return (result, cache)
            
        except Exception as e:
            self.logger.error(f"Error executing scenario '{scenario_name}' for tenant {tenant_id}: {e}")
            return ('error', None)

