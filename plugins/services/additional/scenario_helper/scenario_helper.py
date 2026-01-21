"""
Scenario Helper Service - helper utilities for managing scenario execution
(random number generation, delays, array modification)
"""

from typing import Any, Dict

from .modules.array import ArrayManager
from .modules.cache import CacheManager
from .modules.format import DataFormatter
from .modules.random import RandomManager
from .modules.sleep import SleepManager


class ScenarioHelperService:
    """
    Helper utilities for managing scenario execution:
    - Random number generation with seed support
    - Execution delays (sleep)
    - Array modification (add, remove, clear)
    - Value checking in arrays
    - Setting temporary data in scenario cache
    - Formatting structured data to text format
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('scenario_helper')
        
        # Register ourselves in ActionHub
        self.action_hub.register('scenario_helper', self)
        
        # Get id_generator utility through DI
        self.id_generator = kwargs['id_generator']
        
        # Create managers
        self.data_formatter = DataFormatter(self.logger)
        self.sleep_manager = SleepManager(self.logger)
        self.random_manager = RandomManager(self.logger)
        self.array_manager = ArrayManager(self.logger)
        self.cache_manager = CacheManager(self.logger)
    
    # === Actions for ActionHub ===
    
    async def sleep(self, data: dict) -> Dict[str, Any]:
        """Delay execution for specified number of seconds"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.sleep_manager.sleep(data)
        except Exception as e:
            self.logger.error(f"Error in delay: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def generate_int(self, data: dict) -> Dict[str, Any]:
        """Generate random integer in specified range"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.random_manager.generate_int(data)
        except Exception as e:
            self.logger.error(f"Error generating number: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def generate_array(self, data: dict) -> Dict[str, Any]:
        """Generate array of random numbers in specified range"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.random_manager.generate_array(data)
        except Exception as e:
            self.logger.error(f"Error generating array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def choose_from_array(self, data: dict) -> Dict[str, Any]:
        """Choose random elements from array without repetition"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.random_manager.choose_from_array(data)
        except Exception as e:
            self.logger.error(f"Error choosing from array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def modify_array(self, data: dict) -> Dict[str, Any]:
        """Modify array: add, remove elements or clear"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.array_manager.modify_array(data)
        except Exception as e:
            self.logger.error(f"Error modifying array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def check_value_in_array(self, data: dict) -> Dict[str, Any]:
        """Check if value exists in array"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.array_manager.check_value_in_array(data)
        except Exception as e:
            self.logger.error(f"Error checking value in array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def generate_unique_id(self, data: dict) -> Dict[str, Any]:
        """Generate unique ID through autoincrement in DB (deterministic generation)"""
        try:
            # Validation is done centrally in ActionRegistry
            seed = data.get('seed')
            
            # Get or create unique ID
            unique_id = await self.id_generator.get_or_create_unique_id(seed=seed)
            
            if unique_id is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to generate unique ID"
                    }
                }
            
            return {
                "result": "success",
                "response_data": {
                    "unique_id": unique_id
                }
            }
        except Exception as e:
            self.logger.error(f"Error generating unique ID: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def set_cache(self, data: dict) -> Dict[str, Any]:
        """Set temporary data in scenario cache"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.cache_manager.set_cache(data)
        except Exception as e:
            self.logger.error(f"Error setting cache: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def format_data_to_text(self, data: dict) -> Dict[str, Any]:
        """Format structured data to text format"""
        try:
            # Validation is done centrally in ActionRegistry
            return await self.data_formatter.format_data_to_text(data)
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }

