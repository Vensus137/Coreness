"""
Action Registry - service registry and action routing
"""

import asyncio
from typing import Any, Dict, Optional, Union


class ActionRegistry:
    """
    Service registry and action routing
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.task_manager = kwargs['task_manager']
        # Get validators from parameters
        self.access_validator = kwargs['access_validator']
        self.action_validator = kwargs['action_validator']
        
        # Service registry
        self._services: Dict[str, Any] = {}
        
        # Action to service mapping with full information
        self._action_mapping: Dict[str, Dict[str, Any]] = {}
        
        # Add special ActionHub actions to mapping manually
        self._add_internal_actions()
    
    def _add_internal_actions(self):
        """Add special ActionHub actions to mapping from configuration"""
        try:
            # Get ActionHub plugin info through proxy method
            plugin_info = self.settings_manager.get_plugin_info('action_hub')
            
            if not plugin_info:
                self.logger.warning("ActionHub plugin not found")
                return
            
            # Extract actions block from configuration
            actions = plugin_info.get('actions', {})
            
            # Add special actions to mapping
            special_actions = ['get_available_actions']
            
            for action_name in special_actions:
                if action_name in actions:
                    action_config = actions[action_name]
                    
                    self._action_mapping[action_name] = {
                        'service': 'action_hub',
                        'description': action_config.get('description', ''),
                        'input': action_config.get('input', {}),
                        'output': action_config.get('output', {}),
                        'config': action_config
                    }
                    
            
            # Internal actions added
            
        except Exception as e:
            self.logger.error(f"Error adding internal actions: {e}")
    
    def register(self, service_name: str, service_instance: Any) -> bool:
        """Register service with automatic action mapping construction"""
        try:
            # Register service
            self._services[service_name] = service_instance
            
            # Build action mapping for this service
            self._build_action_mapping_for_service(service_name)
            
            return True
        except Exception as e:
            self.logger.error(f"Error registering service '{service_name}': {e}")
            return False
    
    def unregister(self, service_name: str) -> bool:
        """Unregister service with action mapping cleanup"""
        try:
            if service_name in self._services:
                # Remove service
                del self._services[service_name]
                
                # Clear action mapping for this service
                self._remove_action_mapping_for_service(service_name)
                
                return True
            else:
                self.logger.warning(f"Service '{service_name}' not found")
                return False
        except Exception as e:
            self.logger.error(f"Error unregistering service '{service_name}': {e}")
            return False
    
    def _build_action_mapping_for_service(self, service_name: str):
        """Build action mapping for service from its configuration"""
        try:
            # Get full service configuration through SettingsManager
            plugin_info = self.settings_manager.get_plugin_info(service_name)
            
            if not plugin_info:
                self.logger.warning(f"Service configuration '{service_name}' not found")
                return
            
            # Extract actions block
            actions = plugin_info.get('actions', {})
            
            if not actions:
                self.logger.info(f"Service '{service_name}' has no actions")
                return
            
            # Add each action to mapping with full information
            for action_name, action_config in actions.items():
                if action_name in self._action_mapping:
                    self.logger.warning(f"Action '{action_name}' already mapped to '{self._action_mapping[action_name]['service']}', overwriting with '{service_name}'")
                
                # Save full action information
                self._action_mapping[action_name] = {
                    'service': service_name,
                    'description': action_config.get('description', ''),
                    'input': action_config.get('input', {}),
                    'output': action_config.get('output', {}),
                    'config': action_config  # Full action configuration
                }
            
            # Mapping built
            
        except Exception as e:
            self.logger.error(f"Error building mapping for service '{service_name}': {e}")
    
    def _remove_action_mapping_for_service(self, service_name: str):
        """Remove action mapping for service"""
        try:
            # Find all actions mapped to this service
            actions_to_remove = [
                action_name for action_name, mapped_service in self._action_mapping.items()
                if mapped_service == service_name
            ]
            
            # Remove them from mapping
            for action_name in actions_to_remove:
                del self._action_mapping[action_name]
            
                
        except Exception as e:
            self.logger.error(f"Error removing mapping for service '{service_name}': {e}")
    
    def route_action(self, action_name: str, params: Dict[str, Any]) -> str:
        """Determine which service should handle the action"""
        if action_name in self._action_mapping:
            service_name = self._action_mapping[action_name]['service']
            return service_name
        else:
            self.logger.warning(f"Action '{action_name}' not found in mapping")
            return 'unknown'
    
    def get_action_config(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full action configuration
        
        Returns action configuration from mapping or None if action not found
        """
        if action_name in self._action_mapping:
            return self._action_mapping[action_name].get('config')
        return None
    
    def _validate_access(self, action_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate access based on action rules"""
        try:
            # Get action configuration
            action_info = self._action_mapping.get(action_name)
            if not action_info:
                return {"result": "success"}  # No configuration - skip
            
            action_config = action_info.get('config', {})
            
            # Use AccessValidator to check access
            return self.access_validator.validate_action_access(action_name, action_config, data)
            
        except Exception as e:
            self.logger.error(f"Error validating access for action '{action_name}': {e}")
            return {
                "result": "error",
                "error": f"Access validation error: {str(e)}"
            }
    
    async def execute_action(self, action_name: str, data: dict = None, queue_name: str = None, 
                            fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Execute action on corresponding service through queues
        """
        # If data not provided, use empty dict
        if data is None:
            data = {}
        
        # Send to specified queue or common by default
        target_queue = queue_name if queue_name else "common"
        
        # submit_task returns Dict or Future depending on parameters
        result = await self.task_manager.submit_task(
            task_id=f"action_{action_name}",
            coro=self._create_action_wrapper(action_name, data),
            queue_name=target_queue,
            fire_and_forget=fire_and_forget,
            return_future=return_future
        )
        
        return result
    
    async def _execute_action_direct(self, action_name: str, data: dict = None) -> Dict[str, Any]:
        """Internal method for executing action (used in wrapper for TaskManager)"""
        # If data not provided, use empty dict
        if data is None:
            data = {}
        
        # Special ActionHub actions (don't require service registration)
        if action_name == 'get_available_actions':
            result = self._get_available_actions()
            self._log_action_result(action_name, 'action_hub', result)
            return result
        
        # Regular actions through registered services
        # Determine service for action
        service_name = self.route_action(action_name, data)
        
        if service_name == 'unknown':
            error_result = {"result": "error", "error": f"Action '{action_name}' not found"}
            self._log_action_result(action_name, 'unknown', error_result)
            return error_result
        
        # Get service
        service = self._services.get(service_name)
        if not service:
            error_result = {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Service '{service_name}' not registered"
                }
            }
            self._log_action_result(action_name, service_name, error_result)
            return error_result
        
        # Input data validation (if validator available)
        validated_data = data
        if self.action_validator:
            validation_result = self.action_validator.validate_action_input(
                service_name, action_name, data
            )
            if validation_result.get("result") != "success":
                self._log_action_result(action_name, service_name, validation_result)
                return validation_result
            
            # Get validated data with converted types
            validated_data = validation_result.get("validated_data", data)
        
        # Execute action on service
        try:
            # Get action method from service
            action_method = getattr(service, action_name, None)
            if not action_method:
                error_result = {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Method '{action_name}' not found in service '{service_name}'"
                    }
                }
                self._log_action_result(action_name, service_name, error_result)
                return error_result
            
            # Pass validated data as data dict
            result = await action_method(data=validated_data)
            
            # Centralized error logging
            self._log_action_result(action_name, service_name, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
            self._log_action_result(action_name, service_name, error_result)
            return error_result
    
    async def execute_action_secure(self, action_name: str, data: dict = None, queue_name: str = None, 
                                   fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Secure action execution with tenant_access check
        Checks access by tenant_id and calls regular execute_action
        """
        
        # If data not provided, use empty dict
        if data is None:
            data = {}
        
        # Check access before execution
        access_result = self._validate_access(action_name, data)
        if access_result.get("result") != "success":
            # If return_future - create Future with access error
            if return_future:
                error_future = asyncio.Future()
                error_future.set_result(access_result)
                return error_future
            return access_result
        
        # Call regular execute_action with queue_name="action" by default for secure
        target_queue = queue_name if queue_name else "action"
        
        return await self.execute_action(
            action_name=action_name,
            data=data,
            queue_name=target_queue,
            fire_and_forget=fire_and_forget,
            return_future=return_future
        )
    
    def _create_action_wrapper(self, action_name: str, data: dict):
        """Create wrapper for executing action in TaskManager"""
        async def wrapper():
            return await self._execute_action_direct(action_name, data)
        return wrapper
    
    def _log_action_result(self, action_name: str, service_name: str, result: Dict[str, Any]):
        """Centralized logging of action results"""
        try:
            result_status = result.get('result', 'unknown')
            
            if result_status == 'error':
                error_obj = result.get('error', {})
                error_msg = error_obj.get('message', 'Unknown error')
                error_code = error_obj.get('code', '')
                if error_code:
                    error_msg = f"[{error_code}] {error_msg}"
                self.logger.error(f"Action {{{action_name}}} ({service_name}) completed with error: {error_msg}")
            
            elif result_status == 'timeout':
                error_obj = result.get('error', {})
                timeout_msg = error_obj.get('message', 'Timeout')
                self.logger.warning(f"Action {{{action_name}}} ({service_name}) completed with timeout: {timeout_msg}")
            
            elif result_status == 'not_found':
                pass

            elif result_status == 'success':
                # Don't log successful actions (to avoid spam)
                pass
            
            elif result_status == 'failed':
                # Failed validation - don't log (this is normal behavior)
                pass
            
            else:
                # Unknown status
                self.logger.warning(f"Action {{{action_name}}} ({service_name}) completed with unknown status: {result_status}")
                
        except Exception as e:
            self.logger.error(f"Error logging action result '{action_name}': {e}")
    
    def _get_available_actions(self) -> Dict[str, Any]:
        """Get all available actions with their metadata"""
        try:
            actions = self._action_mapping.copy()
            return {
                "result": "success",
                "response_data": actions
            }
        except Exception as e:
            self.logger.error(f"Error getting available actions: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                },
                "response_data": {}
            }

