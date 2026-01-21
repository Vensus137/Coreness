"""
Extraction of equality conditions from condition string for building search tree
"""

import re
from typing import Any, Dict


class ConditionExtractor:
    """Extraction of equality conditions for search tree"""
    
    def __init__(self):
        # Precompiled regex for extracting equality conditions (for search_path)
        # Look for fields with $name marker
        self._pattern_string_condition = re.compile(r'\$([\w\.]+)\s*==\s*["\']([^"\']*)["\']')
        self._pattern_number_condition = re.compile(r'\$([\w\.]+)\s*==\s*(\d+(?:\.\d+)?)')
        self._pattern_bool_condition = re.compile(r'\$([\w\.]+)\s*==\s*(True|False)')
        self._pattern_none_condition = re.compile(r'\$([\w\.]+)\s*==\s*(None)')
    
    def extract_equal_conditions(self, condition_string: str) -> Dict[str, Any]:
        """Extracts only explicit conditions with == operator for flat fields with $name marker"""
        equal_conditions = {}
        
        # Look for strings in quotes (only fields with $name marker)
        string_matches = self._pattern_string_condition.findall(condition_string)
        for field, value in string_matches:
            if '.' not in field:
                equal_conditions[field] = value
        
        # Look for numbers
        number_matches = self._pattern_number_condition.findall(condition_string)
        for field, value in number_matches:
            if '.' not in field:
                if '.' in value:
                    equal_conditions[field] = float(value)
                else:
                    equal_conditions[field] = int(value)
        
        # Look for boolean values
        bool_matches = self._pattern_bool_condition.findall(condition_string)
        for field, value in bool_matches:
            if '.' not in field:
                equal_conditions[field] = value == 'True'
        
        # Look for None
        none_matches = self._pattern_none_condition.findall(condition_string)
        for field, _value in none_matches:
            if '.' not in field:
                equal_conditions[field] = None
        
        return equal_conditions

