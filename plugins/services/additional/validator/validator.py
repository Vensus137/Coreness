"""
Validator - service for validating conditions in scenarios
"""

from typing import Any, Dict


class Validator:
    """
    Service for validating conditions in scenarios
    - Accepts condition and event data
    - Uses condition_parser for evaluation
    - Returns validation result
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.condition_parser = kwargs['condition_parser']
        
        # Register ourselves in ActionHub
        self.action_hub = kwargs['action_hub']
        self.action_hub.register('validator', self)
    
    # === Actions for ActionHub ===
    
    async def validate(self, data: dict) -> Dict[str, Any]:
        """
        Validate condition with result return
        """
        try:
            # Validation is done centrally in ActionRegistry
            condition = data.get('condition')
            
            # Remove condition data from context for passing to condition_parser
            context_data = data.copy()
            context_data.pop('condition', None)
            
            # Use condition_parser to evaluate condition
            result = await self.condition_parser.check_match(condition, context_data)
            
            if result is True:
                return {"result": "success"}
            elif result is False:
                return {"result": "failed"}
            else:
                # If condition_parser returned something unexpected
                self.logger.error(f"Unexpected condition evaluation result: {result} (type: {type(result)})")
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Unexpected evaluation result: {result}"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error validating condition: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
