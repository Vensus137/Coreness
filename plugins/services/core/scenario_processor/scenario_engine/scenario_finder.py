"""
Поиск сценариев по событиям
Определяет tenant_id из события и находит подходящие сценарии через дерево поиска
"""

from typing import Any, Dict, List, Optional


class ScenarioFinder:
    """
    Поиск сценариев по событиям
    - Извлечение tenant_id из события
    - Поиск подходящих сценариев через дерево поиска
    """
    
    def __init__(self, logger, condition_parser):
        self.logger = logger
        self.condition_parser = condition_parser
    
    def extract_tenant_id(self, event: Dict[str, Any]) -> Optional[int]:
        """Извлечение tenant_id из системного поля события"""
        try:
            # tenant_id должен быть в системном поле события
            if 'system' in event and 'tenant_id' in event['system']:
                tenant_id = event['system']['tenant_id']
                if isinstance(tenant_id, int):
                    return tenant_id
            
            # Если tenant_id нет в системном поле - это ошибка
            self.logger.warning("tenant_id отсутствует в системном поле события - событие не может быть обработано")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения tenant_id: {e}")
            return None
    
    async def find_scenarios_by_event(self, tenant_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> List[int]:
        """Поиск подходящих сценариев по событию через дерево поиска"""
        try:
            # Используем метаданные сценариев для изоляции обработки
            search_tree = scenario_metadata['search_tree']
            
            # Проверяем что дерево поиска не пустое
            if not search_tree:
                return []
            
            # Ищем scenario_id в дереве поиска
            scenario_ids = await self.condition_parser.search_in_tree(search_tree, event)
            
            if not scenario_ids:
                return []
            
            # Фильтруем только существующие сценарии
            existing_scenarios = []
            scenario_index = scenario_metadata['scenario_index']
            for scenario_id in scenario_ids:
                if scenario_id in scenario_index:
                    existing_scenarios.append(scenario_id)
                else:
                    self.logger.warning(f"Найден scenario_id {scenario_id} в дереве поиска, но отсутствует в справочнике")
            
            return existing_scenarios
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска сценариев по событию для tenant {tenant_id}: {e}")
            return []

