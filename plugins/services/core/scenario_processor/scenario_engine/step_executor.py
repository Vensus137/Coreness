"""
Step executor for scenarios
Executes scenario steps, processes placeholders and async actions
"""

import asyncio
from typing import Any, Dict


class StepExecutor:
    """
    Step executor for scenarios
    - Execute steps with placeholder processing
    - Handle synchronous and asynchronous actions
    """
    
    def __init__(self, logger, action_hub, placeholder_processor):
        self.logger = logger
        self.action_hub = action_hub
        self.placeholder_processor = placeholder_processor
    
    async def execute_step(self, step: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scenario step with placeholder processing"""
        try:
            # Validate step
            if not step or not isinstance(step, dict):
                self.logger.warning("Received invalid step")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid step'
                    }
                }
            
            action_name = step.get('action_name')
            if not action_name:
                self.logger.warning("Step does not contain action_name")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Missing action_name'
                    }
                }
            
            params = step.get('params', {})
            
            # Check async flag
            is_async = step.get('async', False)
            action_id = step.get('action_id')  # Unique ID for tracking async actions
            
            # Process placeholders in step parameters
            processed_params = self.placeholder_processor.process_placeholders_full(
                data_with_placeholders=params,
                values_dict=data  # Use accumulated data as value source
            )
            
            # Merge accumulated data with processed step parameters
            action_data = {**data, **processed_params}
            
            # Protect system attributes from overwriting (injection protection)
            if 'system' in data:
                action_data['system'] = data['system']  # Restore original system data
            
            # If async - start asynchronously and save Future
            if is_async:
                if not action_id:
                    self.logger.warning("Async action requires action_id")
                    return {
                        'result': 'error',
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': 'Missing action_id for async action'
                        }
                    }
                
                return await self.execute_action_async(action_name, action_data, action_id)
            else:
                # Regular synchronous execution
                return await self.execute_action(action_name, action_data)
            
        except Exception as e:
            self.logger.error(f"Error executing step {step.get('step_id', 'unknown')}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Internal error: {str(e)}'
                }
            }
    
    async def execute_action(self, action_name: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific action through ActionHub with secure execution"""
        try:
            result = await self.action_hub.execute_action_secure(action_name, data=action_data)
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing action {action_name}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Internal error: {str(e)}'
                }
            }
    
    async def execute_action_async(self, action_name: str, action_data: Dict[str, Any], action_id: str) -> Dict[str, Any]:
        """Start action asynchronously with Future return for tracking"""
        try:
            # Initialize async actions storage if it doesn't exist
            # Use action_data to get current state (may already be initialized)
            current_async_action = action_data.get('_async_action', {})
            
            # Start action through ActionHub with return_future=True
            future = await self.action_hub.execute_action_secure(
                action_name=action_name,
                data=action_data,
                fire_and_forget=True,  # Don't wait for execution
                return_future=True     # But get Future for tracking
            )
            
            # Check that we got Future
            if not isinstance(future, asyncio.Future):
                self.logger.error(f"Expected Future for async action {action_name}, got {type(future)}")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'INTERNAL_ERROR',
                        'message': 'Failed to get Future for async action'
                    }
                }
            
            # Save Future to storage (copy current state and add new one)
            current_async_action[action_id] = future
            
            # Return success without waiting for result
            # IMPORTANT: Add _async_action to response_data so it goes into _cache
            # Don't add action_id and status - they may overwrite user data
            return {
                'result': 'success',
                'response_data': {
                    '_async_action': current_async_action  # Save Future in response_data for adding to _cache
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error starting async action {action_name}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Internal error: {str(e)}'
                }
            }

