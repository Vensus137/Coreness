"""
Module for working with temporary scenario cache data
"""

from typing import Any, Dict


class CacheManager:
    """
    Class for working with temporary scenario cache data
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def set_cache(self, data: dict) -> Dict[str, Any]:
        """
        Set temporary data in scenario cache.
        
        Data is taken from 'cache' key in params, which allows explicitly specifying
        what data needs to be cached, avoiding inclusion of entire scenario context.
        
        All passed parameters are returned in response_data in predefined `_cache` dictionary,
        which prevents accidental overwrite of system fields (bot_id, tenant_id, etc.).
        
        Data is automatically cleared after scenario execution completes.
        """
        try:
            # Get data from 'cache' key in params
            # This allows explicitly specifying what needs to be cached
            cache_data = data.get('cache', {})
            
            # If cache_data is not dict - error
            if not isinstance(cache_data, dict):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "'cache' parameter must be an object (dict)"
                    }
                }
            
            # Return data directly, it will automatically get into _cache[action_name] in scenario_engine
            return {
                "result": "success",
                "response_data": cache_data
            }
            
        except Exception as e:
            self.logger.error(f"Error setting cache: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
