"""
Utilities for working with objects (dictionaries, lists)
"""
from typing import Dict


def deep_merge(base: Dict, updates: Dict) -> Dict:
    """
    Recursively merges two dictionaries, preserving all fields from base and updating them with values from updates
    """
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Update value (or add new)
            result[key] = value
    
    return result
