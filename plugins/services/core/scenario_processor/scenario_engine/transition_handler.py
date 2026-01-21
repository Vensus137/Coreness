"""
Transition handler between scenario steps
Handles all transition types: stop, abort, break, jump_to_scenario, move_steps, jump_to_step
"""

from typing import Any, Dict, List, Optional, Tuple


class TransitionHandler:
    """
    Transition handler between scenario steps
    - Parse transitions by action result
    - Handle all transition types
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def process_transitions(self, action_result: str, transition: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process transitions by action result. Returns dictionary with keys action and value"""
        try:
            # First look for "any" transition - it's processed first
            any_transition = None
            matching_transition = None
            
            for transition_data in transition:
                if transition_data.get('action_result') == 'any':
                    any_transition = transition_data
                elif transition_data.get('action_result') == action_result:
                    matching_transition = transition_data
            
            # Use "any" transition if present, otherwise search by action result
            final_transition = any_transition if any_transition else matching_transition
            
            if not final_transition:
                return {'action': 'continue', 'value': None}
            
            transition_action = final_transition.get('transition_action', 'continue')
            transition_value = final_transition.get('transition_value')
            
            # Execute transition
            if transition_action == 'continue':
                # Continue to next step
                return {'action': 'continue', 'value': None}
                
            elif transition_action == 'stop':
                # Interrupt entire event processing (all scenarios)
                return {'action': 'stop', 'value': None}
                
            elif transition_action == 'break':
                # Interrupt only current scenario execution
                return {'action': 'break', 'value': None}
                
            elif transition_action == 'abort':
                # Interrupt entire execution chain of current scenario (including nested)
                return {'action': 'abort', 'value': None}
                
            elif transition_action == 'jump_to_scenario':
                # Jump to another scenario
                if not transition_value:
                    return {'action': 'continue', 'value': None}
                
                return {'action': 'jump_to_scenario', 'value': transition_value}
                
            elif transition_action == 'move_steps':
                # Move by specified number of steps
                return {'action': 'move_steps', 'value': transition_value}
            
            elif transition_action == 'jump_to_step':
                # Jump to specific step by index
                return {'action': 'jump_to_step', 'value': transition_value}
                
            else:
                return {'action': 'continue', 'value': None}
            
        except Exception as e:
            self.logger.error(f"Error processing transitions: {e}")
            return {'action': 'continue', 'value': None}
    
    async def handle_stop_abort_break(self, transition_action: str, data: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Handle stop, abort, break transitions. Returns tuple (result, cache)"""
        cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
        return (transition_action, cache)
    
    async def handle_jump_to_scenario(self, transition_value: Any, tenant_id: int, data: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Handle jump_to_scenario transition. Returns tuple (result, cache)"""
        if not transition_value:
            # transition_value is empty or None - continue execution
            return ('continue', None)
        
        if isinstance(transition_value, str):
            # Single scenario
            jump_data = data.copy()
            jump_result, jump_cache = await execute_scenario_by_name_func(
                tenant_id=tenant_id,
                scenario_name=transition_value,
                data=jump_data,
                scenario_metadata=scenario_metadata
            )
            
            # If transition scenario returned stop or abort - pass it further
            if jump_result in ['stop', 'abort']:
                cache = jump_cache if jump_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
                return (jump_result, cache)
            
            # Current scenario completed successfully - return cache from jump or from data
            cache = jump_cache if jump_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
            return ('success', cache)
            
        elif isinstance(transition_value, list):
            # Array of scenarios - execute sequentially
            last_cache = None
            jump_data = data.copy()
            
            for scenario_name in transition_value:
                jump_result, jump_cache = await execute_scenario_by_name_func(
                    tenant_id=tenant_id,
                    scenario_name=scenario_name,
                    data=jump_data,
                    scenario_metadata=scenario_metadata
                )
                
                # Save last cache
                if jump_cache:
                    last_cache = jump_cache
                
                # If any transition scenario returned stop or abort - interrupt entire chain
                if jump_result in ['stop', 'abort']:
                    cache = last_cache if last_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
                    return (jump_result, cache)
            
            # All scenarios completed successfully - return last cache or from data
            cache = last_cache if last_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
            return ('success', cache)
        else:
            # Invalid transition_value type - log and continue execution
            self.logger.warning(f"Invalid transition_value type for jump_to_scenario: {type(transition_value)}, expected str or list")
            return ('continue', None)
    
    async def handle_move_steps(self, transition_value: Any, current_index: int, sorted_step: List[Dict[str, Any]], data: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
        """Handle move_steps transition. Returns tuple (result, new_index, cache)"""
        # Move by specified number of steps (positive = forward, negative = backward)
        # Logic: moving by N steps means going to step i + N
        # move_steps: 1 = move 1 step forward (to next step)
        # move_steps: 2 = move 2 steps forward (skip 1 step)
        # move_steps: -1 = move 1 step backward
        step_count = transition_value or 1
        try:
            step_count = int(step_count)
        except (ValueError, TypeError):
            step_count = 1
        
        # Formula: i + step_count (simply move by N steps)
        new_index = current_index + step_count
        
        # Check bounds: index should be in range [0, len(sorted_step))
        if 0 <= new_index < len(sorted_step):
            return ('continue', new_index, None)
        elif new_index < 0:
            # If index became negative - start from beginning
            return ('continue', 0, None)
        else:
            # If index goes beyond bounds forward - finish scenario
            cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
            return ('success', None, cache)
    
    async def handle_jump_to_step(self, transition_value: Any, sorted_step: List[Dict[str, Any]], data: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
        """Handle jump_to_step transition. Returns tuple (result, new_index, cache)"""
        # Jump to specific step by index (steps numbered from 0)
        step_index = transition_value
        try:
            step_index = int(step_index)
        except (ValueError, TypeError):
            # If index is incorrect - continue execution
            return ('continue', None, None)
        
        # Check bounds: index should be in range [0, len(sorted_step))
        if 0 <= step_index < len(sorted_step):
            return ('continue', step_index, None)
        else:
            # If index goes beyond bounds - finish scenario
            cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
            return ('success', None, cache)

