"""
Scenario data cache manager
Manages data caching between steps, response_key processing and deep merging
"""

from typing import Any, Dict, Optional


class CacheManager:
    """
    Scenario data cache manager
    - Merge response_data into _cache
    - Process response_key for replacing replaceable fields
    - Deep dictionary merging
    - Find replaceable fields in configs
    """
    
    def __init__(self, logger, action_hub):
        self.logger = logger
        self.action_hub = action_hub
    
    def merge_response_data(self, response_data: Dict[str, Any], data: Dict[str, Any], action_name: str, params: Dict[str, Any]) -> None:
        """Merge response_data into _cache considering namespace and response_key"""
        if not response_data:
            return
        
        # Initialize _cache if it doesn't exist
        if '_cache' not in data:
            data['_cache'] = {}
        
        # Exception: _async_action must be available in flat data for async actions coordination
        async_action_data = response_data.pop('_async_action', None)
        if async_action_data is not None:
            # Merge _async_action into data for coordination
            if '_async_action' not in data:
                data['_async_action'] = {}
            if isinstance(async_action_data, dict):
                data['_async_action'].update(async_action_data)
        
        # Process _response_key for replacing replaceable field key
        response_key = params.get('_response_key')
        
        if response_key and action_name and response_data:
            try:
                # Get action configuration
                action_config = self.action_hub.get_action_config(action_name)
                if action_config:
                    output_config = action_config.get('output', {})
                    replaceable_field = self._find_replaceable_field(output_config)
                    
                    if replaceable_field and replaceable_field in response_data:
                        # Replace key: extract value and rename
                        value = response_data.pop(replaceable_field)
                        response_data[response_key] = value
                    elif replaceable_field:
                        # Field found in config but missing in response_data
                        self.logger.warning(f"[Action-{action_name}] Field '{replaceable_field}' with replaceable: true found in config but missing in response_data")
                    # If replaceable_field not found - just ignore _response_key (action may not support it)
            except Exception as e:
                self.logger.warning(f"[Action-{action_name}] Error processing _response_key: {e}")
        
        # Save data to _cache
        if response_data:  # If data remains after extracting _async_action
            namespace = params.get('_namespace')
            if namespace:
                # Nested caching - in _cache[namespace] (for overwrite control)
                if namespace in data['_cache']:
                    # Merge with existing data in this key
                    data['_cache'][namespace] = self.deep_merge(data['_cache'][namespace], response_data)
                else:
                    # Just save if key doesn't exist
                    data['_cache'][namespace] = response_data
            else:
                # Flat caching by default - merge directly into _cache
                data['_cache'] = self.deep_merge(data.get('_cache', {}), response_data)
    
    def extract_cache(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract cache from scenario data"""
        return data.get('_cache') if isinstance(data.get('_cache'), dict) else None
    
    def _find_replaceable_field(self, output_config: Dict[str, Any]) -> Optional[str]:
        """Find field with replaceable: true flag in action output configuration"""
        try:
            response_data = output_config.get('response_data', {})
            if not isinstance(response_data, dict):
                return None
            
            properties = response_data.get('properties', {})
            if not isinstance(properties, dict):
                return None
            
            # Search for field with replaceable: true
            for field_name, field_config in properties.items():
                if isinstance(field_config, dict) and field_config.get('replaceable', False):
                    return field_name
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error finding replaceable field: {e}")
            return None
    
    def deep_merge(self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Deep dictionary merging: override_dict overrides base_dict"""
        result = base_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self.deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result

