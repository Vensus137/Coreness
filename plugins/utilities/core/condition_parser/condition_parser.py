"""
Universal condition parser for scenarios
New version with support for $name marker for fields
"""

from typing import Any, Dict, List, Union

from .core.compiler import ConditionCompiler
from .core.extractor import ConditionExtractor
from .core.tokenizer import ConditionTokenizer


class ConditionParser:
    """Universal condition expression parser with support for $name marker for fields"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
        # Initialize components
        self.tokenizer = ConditionTokenizer()
        self.compiler = ConditionCompiler(self.logger, self.tokenizer)
        self.extractor = ConditionExtractor()
    
    async def parse_condition_string(self, condition_string: str) -> Dict[str, Any]:
        """Parse condition string with extraction of all == conditions for search tree"""
        try:
            result = {
                'search_path': {},
                'compiled_function': None,
                'condition_hash': None
            }
            
            # Extract all == conditions (only for flat fields with $name marker)
            equal_conditions = self.extractor.extract_equal_conditions(condition_string)
            
            # Sort fields for consistency
            sorted_conditions = dict(sorted(equal_conditions.items()))
            
            # Build search path
            result['search_path'] = sorted_conditions
            
            # Compile all conditions
            result['compiled_function'] = self.compiler.compile(condition_string)
            
            # Create hash of original condition for duplicate comparison
            result['condition_hash'] = hash(condition_string.strip())
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing condition '{condition_string}': {e}")
            return {
                'search_path': {},
                'compiled_function': None,
                'condition_hash': None
            }
    
    async def check_match(self, condition: Union[str, Dict[str, Any]], data: Dict[str, Any]) -> bool:
        """Universal check for data matching condition"""
        try:
            if isinstance(condition, str):
                parsed_condition = await self.parse_condition_string(condition)
                return await self._check_parsed_condition(parsed_condition, data)
            elif isinstance(condition, dict):
                return await self._check_parsed_condition(condition, data)
            else:
                self.logger.error(f"Unsupported condition type: {type(condition)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error checking condition: {e}")
            return False
    
    async def _check_parsed_condition(self, parsed_condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Internal method for checking parsed condition"""
        try:
            compiled_function = parsed_condition.get('compiled_function')
            if compiled_function:
                try:
                    return compiled_function(data)
                except Exception as e:
                    self.logger.error(f"Error executing condition: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking parsed condition: {e}")
            return False
    
    async def add_to_tree(self, search_tree: Dict[str, Any], parsed_condition: Dict[str, Any], item_name: str, item_value: Any) -> bool:
        """Adds element to search tree with conditions in leaves"""
        try:
            search_path = parsed_condition['search_path']
            compiled_function = parsed_condition['compiled_function']
            
            # If no == conditions, add to root
            if not search_path:
                if 'conditions' not in search_tree:
                    search_tree['conditions'] = []
                
                condition_hash = parsed_condition.get('condition_hash')
                new_item = {
                    item_name: item_value,
                    'compiled_function': compiled_function,
                    'condition_hash': condition_hash
                }
                
                is_duplicate = any(
                    existing_item.get('condition_hash') == condition_hash and 
                    existing_item.get(item_name) == item_value
                    for existing_item in search_tree['conditions']
                )
                
                if not is_duplicate:
                    search_tree['conditions'].append(new_item)
                    return True
                else:
                    return False
            
            # Build tree by search_path
            current_level = search_tree
            sorted_fields = sorted(search_path.items())
            
            # Create intermediate nodes
            for field_name, field_value in sorted_fields:
                if field_name not in current_level:
                    current_level[field_name] = {}
                current_level = current_level[field_name]
                
                if field_value not in current_level:
                    current_level[field_value] = {}
                current_level = current_level[field_value]
            
            # In final node create conditions if it doesn't exist
            if 'conditions' not in current_level:
                current_level['conditions'] = []
            
            condition_hash = parsed_condition.get('condition_hash')
            new_item = {
                item_name: item_value,
                'compiled_function': compiled_function,
                'condition_hash': condition_hash
            }
            
            is_duplicate = any(
                existing_item.get('condition_hash') == condition_hash and 
                existing_item.get(item_name) == item_value
                for existing_item in current_level['conditions']
            )
            
            if not is_duplicate:
                current_level['conditions'].append(new_item)
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding element {item_name}={item_value} to tree: {e}")
            return False
    
    async def search_in_tree(self, search_tree: Dict[str, Any], data: Dict[str, Any]) -> List[Any]:
        """Fast search for values in tree by event data - O(m) where m is tree depth"""
        try:
            found_values = []
            await self._search_tree_by_path(search_tree, data, found_values)
            return found_values
            
        except Exception as e:
            self.logger.error(f"Error searching in tree: {e}")
            return []
    
    async def _check_items(self, items: List[Dict[str, Any]], data: Dict[str, Any], found_values: List[Any]):
        """Check list items for condition matching"""
        try:
            for item in items:
                if isinstance(item, dict):
                    compiled_function = item.get('compiled_function')
                    if compiled_function:
                        try:
                            if compiled_function(data):
                                for item_key, item_value in item.items():
                                    if item_key not in ['compiled_function', 'condition_hash']:
                                        if item_value not in found_values:
                                            found_values.append(item_value)
                        except Exception as e:
                            self.logger.error(f"Error checking condition: {e}")
        except Exception as e:
            self.logger.error(f"Error checking items: {e}")
    
    async def _search_tree_by_path(self, tree_node: Dict[str, Any], data: Dict[str, Any], found_values: List[Any]):
        """Fast tree search - check conditions in each node while descending"""
        try:
            # First check conditions in current node
            if 'conditions' in tree_node:
                await self._check_items(tree_node['conditions'], data, found_values)
            
            # Then go further along all matching paths
            for key, value in tree_node.items():
                if key == 'conditions':
                    continue
                
                if isinstance(value, dict):
                    if key in data:
                        data_value = data[key]
                        if data_value in value:
                            await self._search_tree_by_path(value[data_value], data, found_values)
                        else:
                            continue
                    else:
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error searching by path in tree: {e}")
    
    async def build_condition(self, configs: List[Dict[str, Any]]) -> str:
        """Build condition from array of structures with simple fields and custom conditions"""
        try:
            all_conditions = []
            
            for config in configs:
                config_conditions = []
                
                # Process simple fields (except 'condition')
                for field, value in config.items():
                    if field == 'condition':
                        continue
                    
                    # Add $name marker for fields
                    if isinstance(value, str):
                        escaped_value = f"'{value}'"
                    else:
                        escaped_value = str(value)
                    
                    config_conditions.append(f"${field} == {escaped_value}")
                
                # Add custom condition if exists
                if 'condition' in config:
                    custom_condition = config['condition'].strip()
                    if custom_condition:
                        config_conditions.append(custom_condition)
                
                # Join configuration conditions with AND
                if config_conditions:
                    config_condition = " and ".join(config_conditions)
                    all_conditions.append(f"({config_condition})")
            
            # Join all configurations with OR (each configuration is an alternative)
            if all_conditions:
                return " or ".join(all_conditions)
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Error building condition from configurations: {e}")
            return ""
