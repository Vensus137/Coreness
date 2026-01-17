"""
Загрузчик сценариев из БД
Загружает сценарии, триггеры и шаги из базы данных и строит структуру для кэширования
"""

from typing import Any, Dict


class ScenarioLoader:
    """
    Загрузчик сценариев из БД
    - Загрузка сценариев для tenant'а
    - Загрузка триггеров и шагов сценариев
    - Построение структуры для кэширования
    """
    
    def __init__(self, logger, data_loader, condition_parser):
        self.logger = logger
        self.data_loader = data_loader
        self.condition_parser = condition_parser
    
    async def load_tenant_scenarios(self, tenant_id: int) -> Dict[str, Any]:
        """Загрузка сценариев для конкретного tenant'а. Возвращает структуру кэша с ключами search_tree, scenario_index, scenario_name_index"""
        try:
            # Инициализируем структуру кэша для tenant'а
            cache = {
                'search_tree': {},
                'scenario_index': {},
                'scenario_name_index': {}
            }
            
            # Загружаем все сценарии tenant'а
            scenarios = await self.data_loader.load_scenarios_by_tenant(tenant_id)
            if not scenarios:
                self.logger.warning(f"Не найдено сценариев для tenant {tenant_id}")
                # Кэшируем пустой результат, чтобы не повторять запросы
                return cache
            
            # Обрабатываем каждый сценарий
            for scenario in scenarios:
                scenario_id = scenario['id']
                scenario_name = scenario['scenario_name']
                
                # Создаем запись сценария в справочнике
                cache['scenario_index'][scenario_id] = {
                    'data': {
                        'id': scenario_id,
                        'name': scenario_name,
                        'raw_data': scenario
                    },
                    'trigger': (),  # Будет заполнено tuple после загрузки триггеров
                    'step': ()      # Будет заполнено tuple после загрузки шагов
                }
                
                # Добавляем в индекс для быстрого поиска по имени
                cache['scenario_name_index'][scenario_name] = scenario_id
                
                # Загружаем триггеры сценария
                await self._load_scenario_trigger(tenant_id, scenario_id, cache)
                
                # Загружаем шаги сценария
                await self._load_scenario_step(tenant_id, scenario_id, cache)
            
            return cache
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сценариев для tenant {tenant_id}: {e}")
            # Кэшируем ошибку как пустой результат, чтобы не повторять запросы
            return {
                'search_tree': {},
                'scenario_index': {},
                'scenario_name_index': {}
            }
    
    async def _load_scenario_trigger(self, tenant_id: int, scenario_id: int, cache: Dict[str, Any]) -> None:
        """Загрузка триггеров сценария"""
        try:
            trigger = await self.data_loader.load_triggers_by_scenario(scenario_id)
            
            trigger_list = []
            for trigger_data in trigger:
                trigger_id = trigger_data['id']
                condition_expression = trigger_data.get('condition_expression', '')
                
                # Парсим условие с помощью condition_parser
                parsed_condition = await self.condition_parser.parse_condition_string(condition_expression)
                
                # Добавляем триггер в дерево поиска
                if parsed_condition and parsed_condition.get('search_path'):
                    await self.condition_parser.add_to_tree(
                        cache['search_tree'],
                        parsed_condition,
                        'scenario_id',
                        scenario_id
                    )
                
                # Добавляем триггер в список (будет преобразован в tuple)
                trigger_list.append({
                    'trigger_id': trigger_id,
                    'condition': parsed_condition,
                    'raw_data': trigger_data
                })
            
            # Преобразуем список в tuple (immutable) для безопасного shallow copy
            cache['scenario_index'][scenario_id]['trigger'] = tuple(trigger_list)
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки триггеров для сценария {scenario_id}: {e}")
    
    async def _load_scenario_step(self, tenant_id: int, scenario_id: int, cache: Dict[str, Any]) -> None:
        """Загрузка шагов сценария"""
        try:
            step = await self.data_loader.load_steps_by_scenario(scenario_id)
            
            step_list = []
            for step_data in step:
                step_id = step_data['id']
                
                # Загружаем переходы шага
                transition = await self.data_loader.load_transitions_by_step(step_id)
                
                # Добавляем шаг в список (будет преобразован в tuple)
                step_list.append({
                    'step_id': step_id,
                    'step_order': step_data['step_order'],
                    'action_name': step_data['action_name'],
                    'params': step_data['params'],
                    'async': step_data.get('is_async', False),
                    'action_id': step_data.get('action_id'),
                    'transition': transition,
                    'raw_data': step_data
                })
            
            # Преобразуем список в tuple (immutable) для безопасного shallow copy
            cache['scenario_index'][scenario_id]['step'] = tuple(step_list)
                
        except Exception as e:
            self.logger.error(f"Ошибка загрузки шагов для сценария {scenario_id}: {e}")

