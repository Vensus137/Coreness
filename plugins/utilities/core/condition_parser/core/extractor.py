"""
Извлечение условий равенства из строки условия для построения дерева поиска
"""

import re
from typing import Any, Dict


class ConditionExtractor:
    """Извлечение условий равенства для дерева поиска"""
    
    def __init__(self):
        # Предкомпилированные regex для извлечения условий равенства (для search_path)
        # Ищем поля с маркером $name
        self._pattern_string_condition = re.compile(r'\$([\w\.]+)\s*==\s*["\']([^"\']*)["\']')
        self._pattern_number_condition = re.compile(r'\$([\w\.]+)\s*==\s*(\d+(?:\.\d+)?)')
        self._pattern_bool_condition = re.compile(r'\$([\w\.]+)\s*==\s*(True|False)')
        self._pattern_none_condition = re.compile(r'\$([\w\.]+)\s*==\s*(None)')
    
    def extract_equal_conditions(self, condition_string: str) -> Dict[str, Any]:
        """Извлекает только явные условия с оператором == для плоских полей с маркером $name"""
        equal_conditions = {}
        
        # Ищем строки в кавычках (только поля с маркером $name)
        string_matches = self._pattern_string_condition.findall(condition_string)
        for field, value in string_matches:
            if '.' not in field:
                equal_conditions[field] = value
        
        # Ищем числа
        number_matches = self._pattern_number_condition.findall(condition_string)
        for field, value in number_matches:
            if '.' not in field:
                if '.' in value:
                    equal_conditions[field] = float(value)
                else:
                    equal_conditions[field] = int(value)
        
        # Ищем булевы значения
        bool_matches = self._pattern_bool_condition.findall(condition_string)
        for field, value in bool_matches:
            if '.' not in field:
                equal_conditions[field] = value == 'True'
        
        # Ищем None
        none_matches = self._pattern_none_condition.findall(condition_string)
        for field, _value in none_matches:
            if '.' not in field:
                equal_conditions[field] = None
        
        return equal_conditions

