"""
Универсальный парсер условий для сценариев
Новая версия с поддержкой маркера $name для полей
"""

from typing import Any, Dict, List, Union

from .core.compiler import ConditionCompiler
from .core.extractor import ConditionExtractor
from .core.tokenizer import ConditionTokenizer


class ConditionParser:
    """Универсальный парсер выражений условий с поддержкой маркера $name для полей"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
        # Инициализируем компоненты
        self.tokenizer = ConditionTokenizer()
        self.compiler = ConditionCompiler(self.logger, self.tokenizer)
        self.extractor = ConditionExtractor()
    
    async def parse_condition_string(self, condition_string: str) -> Dict[str, Any]:
        """Парсинг строки условий с извлечением всех условий с == для дерева поиска"""
        try:
            result = {
                'search_path': {},
                'compiled_function': None,
                'condition_hash': None
            }
            
            # Извлекаем все условия с == (только для плоских полей с маркером $name)
            equal_conditions = self.extractor.extract_equal_conditions(condition_string)
            
            # Сортируем поля для консистентности
            sorted_conditions = dict(sorted(equal_conditions.items()))
            
            # Строим путь поиска
            result['search_path'] = sorted_conditions
            
            # Компилируем все условия
            result['compiled_function'] = self.compiler.compile(condition_string)
            
            # Создаем хеш исходного условия для сравнения дубликатов
            result['condition_hash'] = hash(condition_string.strip())
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга условия '{condition_string}': {e}")
            return {
                'search_path': {},
                'compiled_function': None,
                'condition_hash': None
            }
    
    async def check_match(self, condition: Union[str, Dict[str, Any]], data: Dict[str, Any]) -> bool:
        """Универсальная проверка соответствия данных условию"""
        try:
            if isinstance(condition, str):
                parsed_condition = await self.parse_condition_string(condition)
                return await self._check_parsed_condition(parsed_condition, data)
            elif isinstance(condition, dict):
                return await self._check_parsed_condition(condition, data)
            else:
                self.logger.error(f"Неподдерживаемый тип условия: {type(condition)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки условия: {e}")
            return False
    
    async def _check_parsed_condition(self, parsed_condition: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Внутренний метод проверки распарсенного условия"""
        try:
            compiled_function = parsed_condition.get('compiled_function')
            if compiled_function:
                try:
                    return compiled_function(data)
                except Exception as e:
                    self.logger.error(f"Ошибка выполнения условия: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки распарсенного условия: {e}")
            return False
    
    async def add_to_tree(self, search_tree: Dict[str, Any], parsed_condition: Dict[str, Any], item_name: str, item_value: Any) -> bool:
        """Добавляет элемент в дерево поиска с условиями в листах"""
        try:
            search_path = parsed_condition['search_path']
            compiled_function = parsed_condition['compiled_function']
            
            # Если нет условий с ==, добавляем в корень
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
            
            # Строим дерево по search_path
            current_level = search_tree
            sorted_fields = sorted(search_path.items())
            
            # Создаем промежуточные узлы
            for field_name, field_value in sorted_fields:
                if field_name not in current_level:
                    current_level[field_name] = {}
                current_level = current_level[field_name]
                
                if field_value not in current_level:
                    current_level[field_value] = {}
                current_level = current_level[field_value]
            
            # В конечном узле создаем conditions если его нет
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
            self.logger.error(f"Ошибка добавления элемента {item_name}={item_value} в дерево: {e}")
            return False
    
    async def search_in_tree(self, search_tree: Dict[str, Any], data: Dict[str, Any]) -> List[Any]:
        """Быстрый поиск значений в дереве по данным события - O(m) где m - глубина дерева"""
        try:
            found_values = []
            await self._search_tree_by_path(search_tree, data, found_values)
            return found_values
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска в дереве: {e}")
            return []
    
    async def _check_items(self, items: List[Dict[str, Any]], data: Dict[str, Any], found_values: List[Any]):
        """Проверка элементов списка на соответствие условиям"""
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
                            self.logger.error(f"Ошибка проверки условия: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка проверки элементов: {e}")
    
    async def _search_tree_by_path(self, tree_node: Dict[str, Any], data: Dict[str, Any], found_values: List[Any]):
        """Быстрый поиск по дереву - проверяем conditions в каждом узле при погружении"""
        try:
            # Сначала проверяем conditions в текущем узле
            if 'conditions' in tree_node:
                await self._check_items(tree_node['conditions'], data, found_values)
            
            # Затем идем дальше по всем подходящим путям
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
            self.logger.error(f"Ошибка поиска по пути в дереве: {e}")
    
    async def build_condition(self, configs: List[Dict[str, Any]]) -> str:
        """Сборка условия из массива структур с простыми полями и кастомными условиями"""
        try:
            all_conditions = []
            
            for config in configs:
                config_conditions = []
                
                # Обрабатываем простые поля (кроме 'condition')
                for field, value in config.items():
                    if field == 'condition':
                        continue
                    
                    # Добавляем маркер $name для полей
                    if isinstance(value, str):
                        escaped_value = f"'{value}'"
                    else:
                        escaped_value = str(value)
                    
                    config_conditions.append(f"${field} == {escaped_value}")
                
                # Добавляем кастомное условие, если есть
                if 'condition' in config:
                    custom_condition = config['condition'].strip()
                    if custom_condition:
                        config_conditions.append(custom_condition)
                
                # Склеиваем условия конфигурации через AND
                if config_conditions:
                    config_condition = " and ".join(config_conditions)
                    all_conditions.append(f"({config_condition})")
            
            # Склеиваем все конфигурации через OR (каждая конфигурация - альтернатива)
            if all_conditions:
                return " or ".join(all_conditions)
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Ошибка сборки условия из конфигураций: {e}")
            return ""
