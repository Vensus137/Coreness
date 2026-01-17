"""
Загрузчик конфигурации из БД для scenario_processor
"""

from typing import Any, Dict, List, Optional


class DataLoader:
    """
    Универсальный загрузчик данных сценариев из БД для scenario_processor
    Работает с любыми tenant'ами, принимая tenant_id в каждый метод
    """
    
    def __init__(self, logger, database_manager):
        self.logger = logger
        self.database_manager = database_manager
    
    async def load_scenarios_by_tenant(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Загрузка всех сценариев для tenant'а
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            scenarios = await master_repo.get_scenarios_by_tenant(tenant_id)
            
            return scenarios
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сценариев для tenant {tenant_id}: {e}")
            return []
    
    async def load_triggers_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """
        Загрузка триггеров сценария
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            triggers = await master_repo.get_triggers_by_scenario(scenario_id)
            
            return triggers
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки триггеров для сценария {scenario_id}: {e}")
            return []
    
    async def load_steps_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """
        Загрузка шагов сценария
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            steps = await master_repo.get_steps_by_scenario(scenario_id)
            
            return steps
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки шагов для сценария {scenario_id}: {e}")
            return []
    
    async def load_transitions_by_step(self, step_id: int) -> List[Dict[str, Any]]:
        """
        Загрузка переходов шага
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            transitions = await master_repo.get_transitions_by_step(step_id)
            
            return transitions
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки переходов для шага {step_id}: {e}")
            return []
    
    # === Методы удаления ===
    
    async def delete_tenant_scenarios(self, tenant_id: int) -> bool:
        """
        Удаление всех сценариев tenant'а из БД
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Получаем все сценарии tenant'а
            scenarios = await master_repo.get_scenarios_by_tenant(tenant_id)
            
            for scenario in scenarios:
                scenario_id = scenario['id']
                
                # Удаляем шаги сценария (и их переходы)
                await master_repo.delete_steps_by_scenario(scenario_id)
                
                # Удаляем триггеры сценария (и их условия)
                await master_repo.delete_triggers_by_scenario(scenario_id)
                
                # Удаляем сам сценарий
                await master_repo.delete_scenario(scenario_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления сценариев для tenant {tenant_id}: {e}")
            return False
    
    # === Методы сохранения ===
    
    async def save_scenario(self, tenant_id: int, scenario_data: Dict[str, Any]) -> Optional[int]:
        """
        Сохранение сценария в БД
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Создаем сценарий
            scenario_id = await master_repo.create_scenario({
                'tenant_id': tenant_id,
                'scenario_name': scenario_data['scenario_name'],
                'description': scenario_data.get('description', ''),
                'schedule': scenario_data.get('schedule'),  # Cron выражение (может быть None)
                'is_active': True
            })
            
            return scenario_id
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения сценария для tenant {tenant_id}: {e}")
            return None
    
    async def load_scheduled_scenarios(self, tenant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Загрузка всех scheduled сценариев из БД
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            scenarios = await master_repo.get_scheduled_scenarios(tenant_id)
            return scenarios
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки scheduled сценариев: {e}")
            return []
    
    async def save_trigger(self, scenario_id: int, trigger_data: Dict[str, Any]) -> Optional[int]:
        """
        Сохранение триггера сценария в БД
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Создаем триггер с условием
            trigger_id = await master_repo.create_trigger({
                'scenario_id': scenario_id,
                'condition_expression': trigger_data['condition_expression']
            })
            
            return trigger_id
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения триггера для сценария {scenario_id}: {e}")
            return None
    
    async def save_step(self, scenario_id: int, step_data: Dict[str, Any]) -> Optional[int]:
        """
        Сохранение шага сценария в БД
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Создаем шаг
            step_id = await master_repo.create_step({
                'scenario_id': scenario_id,
                'step_order': step_data['step_order'],
                'action_name': step_data['action_name'],
                'params': step_data.get('params', {}),
                'is_async': step_data.get('is_async', False),
                'action_id': step_data.get('action_id'),
                'is_active': True
            })
            
            # Создаем переходы шага
            transition = step_data.get('transition', [])
            for transition_data in transition:
                await master_repo.create_transition({
                    'step_id': step_id,
                    'action_result': transition_data.get('action_result', 'success'),
                    'transition_action': transition_data.get('transition_action', 'continue'),
                    'transition_value': transition_data.get('transition_value')
                })
            
            return step_id
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения шага для сценария {scenario_id}: {e}")
            return None