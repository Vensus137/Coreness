"""
Module for working with arrays (modification, value checking)
"""

from typing import Any, Dict


class ArrayManager:
    """
    Class for working with arrays
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def modify_array(self, data: dict) -> Dict[str, Any]:
        """
        Modify array: add, remove elements or clear
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No data for modification"
                    }
                }
            
            array = data.get('array')
            operation = data.get('operation')
            value = data.get('value')
            skip_duplicates = data.get('skip_duplicates', True)  # By default skip duplicates
            
            # Parameter validation
            if array is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "array parameter is required"
                    }
                }
            
            if not isinstance(array, list):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "array parameter must be an array"
                    }
                }
            
            if operation is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "operation parameter is required"
                    }
                }
            
            if operation not in ['add', 'remove', 'clear']:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "operation parameter must be one of: 'add', 'remove', 'clear'"
                    }
                }
            
            # Create copy of array for modification
            modified_array = list(array)
            
            # Execute operation
            if operation == 'add':
                if value is None:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "value parameter is required for 'add' operation"
                        }
                    }
                
                # Check duplicates if needed
                if skip_duplicates and value in modified_array:
                    # Element already exists, return array unchanged
                    pass
                else:
                    modified_array.append(value)
            
            elif operation == 'remove':
                if value is None:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "value parameter is required for 'remove' operation"
                        }
                    }
                
                # Check if element exists in array
                if value not in modified_array:
                    # Element not found
                    return {
                        "result": "not_found",
                        "response_data": {
                            "modified_array": modified_array  # Return original array unchanged
                        }
                    }
                
                # Remove all occurrences of value
                modified_array = [item for item in modified_array if item != value]
            
            elif operation == 'clear':
                modified_array = []
            
            # Form result
            result = {
                "result": "success",
                "response_data": {
                    "modified_array": modified_array
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error modifying array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def check_value_in_array(self, data: dict) -> Dict[str, Any]:
        """
        Check if value exists in array
        Returns index of first occurrence of value in array
        result: "success" if found, "not_found" if not found
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No data for check"
                    }
                }
            
            array = data.get('array')
            value = data.get('value')
            
            # Parameter validation
            if array is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "array parameter is required"
                    }
                }
            
            if not isinstance(array, list):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "array parameter must be an array"
                    }
                }
            
            if value is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "value parameter is required"
                    }
                }
            
            # Check if value exists in array
            if value in array:
                # Find index of first occurrence
                index = array.index(value)
                
                # Form result - found
                return {
                    "result": "success",
                    "response_data": {
                        "response_index": index
                    }
                }
            else:
                # Value not found
                return {
                    "result": "not_found"
                }
            
        except Exception as e:
            self.logger.error(f"Error checking value in array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
