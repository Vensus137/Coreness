"""
Module for execution delays (sleep)
"""

import asyncio
from typing import Any, Dict


class SleepManager:
    """
    Class for execution delays
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def sleep(self, data: dict) -> Dict[str, Any]:
        """
        Delay execution for specified number of seconds
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No data for delay"
                    }
                }
            
            seconds = data.get('seconds')
            
            # Parameter validation
            if seconds is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "seconds parameter is required"
                    }
                }
            
            if not isinstance(seconds, (int, float)):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "seconds parameter must be a number"
                    }
                }
            
            if seconds < 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "seconds parameter cannot be negative"
                    }
                }
            
            # Execute delay
            await asyncio.sleep(float(seconds))
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error executing delay: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
