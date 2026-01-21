"""
Module for random number generation and element selection
"""

import random
from typing import Any, Dict


class RandomManager:
    """
    Class for random number generation and element selection
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def generate_int(self, data: dict) -> Dict[str, Any]:
        """
        Generate random integer in specified range
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No data for generation"
                    }
                }
            
            min_val = data.get('min')
            max_val = data.get('max')
            seed = data.get('seed')
            
            # Parameter validation
            if min_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min parameter is required"
                    }
                }
            
            if max_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "max parameter is required"
                    }
                }
            
            if not isinstance(min_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min parameter must be an integer"
                    }
                }
            
            if not isinstance(max_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "max parameter must be an integer"
                    }
                }
            
            if min_val > max_val:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min cannot be greater than max"
                    }
                }
            
            # Create generator with seed or without
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            
            # Generate random number
            value = rng.randint(min_val, max_val)
            
            # Form result
            result = {
                "result": "success",
                "response_data": {
                    "random_value": value
                }
            }
            
            # Add seed to response if provided (convert to string for consistency)
            if seed is not None:
                result["response_data"]["random_seed"] = str(seed)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating random number: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def generate_array(self, data: dict) -> Dict[str, Any]:
        """
        Generate array of random numbers in specified range
        By default without repetitions, can allow repetitions via allow_duplicates=True
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No data for generation"
                    }
                }
            
            min_val = data.get('min')
            max_val = data.get('max')
            count = data.get('count')
            seed = data.get('seed')
            allow_duplicates = data.get('allow_duplicates', False)  # By default without repetitions
            
            # Parameter validation
            if min_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min parameter is required"
                    }
                }
            
            if max_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "max parameter is required"
                    }
                }
            
            if count is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "count parameter is required"
                    }
                }
            
            if not isinstance(min_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min parameter must be an integer"
                    }
                }
            
            if not isinstance(max_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "max parameter must be an integer"
                    }
                }
            
            if not isinstance(count, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "count parameter must be an integer"
                    }
                }
            
            if min_val > max_val:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min cannot be greater than max"
                    }
                }
            
            if count < 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "count parameter cannot be negative"
                    }
                }
            
            if count == 0:
                return {
                    "result": "success",
                    "response_data": {
                        "random_list": []
                    }
                }
            
            # Check possibility of generation without repetitions
            range_size = max_val - min_val + 1
            if not allow_duplicates and count > range_size:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Cannot generate {count} unique numbers in range [{min_val}, {max_val}] (only {range_size} unique values available). Use allow_duplicates=True to allow repetitions"
                    }
                }
            
            # Create generator with seed or without
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            
            # Generate array of random numbers
            if allow_duplicates:
                # With repetitions - normal generation
                values = [rng.randint(min_val, max_val) for _ in range(count)]
            else:
                # Without repetitions - use sample to guarantee uniqueness
                all_possible_values = list(range(min_val, max_val + 1))
                values = rng.sample(all_possible_values, count)
            
            # Form result
            result = {
                "result": "success",
                "response_data": {
                    "random_list": values
                }
            }
            
            # Add seed to response if provided (convert to string for consistency)
            if seed is not None:
                result["response_data"]["random_seed"] = str(seed)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating random number array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def choose_from_array(self, data: dict) -> Dict[str, Any]:
        """
        Choose random elements from array without repetition
        Returns selected elements and their ordinal numbers (indices) in original array
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "No data for selection"
                    }
                }
            
            array = data.get('array')
            count = data.get('count')
            seed = data.get('seed')
            
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
            
            if count is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "count parameter is required"
                    }
                }
            
            if not isinstance(count, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "count parameter must be an integer"
                    }
                }
            
            if count < 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "count parameter cannot be negative"
                    }
                }
            
            # Check if enough elements in array
            if count > len(array):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Not enough elements in array: requested {count}, available {len(array)}"
                    }
                }
            
            # If 0 elements requested, return empty array
            if count == 0:
                return {
                    "result": "success",
                    "response_data": {
                        "random_list": []
                    }
                }
            
            # Create generator with seed or without
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            
            # Choose random elements without repetition
            # Use sample to guarantee no repetition
            selected_values = rng.sample(array, count)
            
            # Form result
            result = {
                "result": "success",
                "response_data": {
                    "random_list": selected_values
                }
            }
            
            # Add seed to response if provided (convert to string for consistency)
            if seed is not None:
                result["response_data"]["random_seed"] = str(seed)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error choosing elements from array: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
