"""
Configuration loader from DB for scenario_processor
"""

from typing import Any, Dict, List, Optional


class DataLoader:
    """
    Universal scenario data loader from DB for scenario_processor
    Works with any tenants, accepting tenant_id in each method
    """
    
    def __init__(self, logger, database_manager):
        self.logger = logger
        self.database_manager = database_manager
    
    async def load_scenarios_by_tenant(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Load all scenarios for tenant
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            scenarios = await master_repo.get_scenarios_by_tenant(tenant_id)
            
            return scenarios
            
        except Exception as e:
            self.logger.error(f"Error loading scenarios for tenant {tenant_id}: {e}")
            return []
    
    async def load_triggers_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """
        Load scenario triggers
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            triggers = await master_repo.get_triggers_by_scenario(scenario_id)
            
            return triggers
            
        except Exception as e:
            self.logger.error(f"Error loading triggers for scenario {scenario_id}: {e}")
            return []
    
    async def load_steps_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """
        Load scenario steps
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            steps = await master_repo.get_steps_by_scenario(scenario_id)
            
            return steps
            
        except Exception as e:
            self.logger.error(f"Error loading steps for scenario {scenario_id}: {e}")
            return []
    
    async def load_transitions_by_step(self, step_id: int) -> List[Dict[str, Any]]:
        """
        Load step transitions
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            transitions = await master_repo.get_transitions_by_step(step_id)
            
            return transitions
            
        except Exception as e:
            self.logger.error(f"Error loading transitions for step {step_id}: {e}")
            return []
    
    # === Deletion methods ===
    
    async def delete_tenant_scenarios(self, tenant_id: int) -> bool:
        """
        Delete all tenant scenarios from DB
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Get all tenant scenarios
            scenarios = await master_repo.get_scenarios_by_tenant(tenant_id)
            
            for scenario in scenarios:
                scenario_id = scenario['id']
                
                # Delete scenario steps (and their transitions)
                await master_repo.delete_steps_by_scenario(scenario_id)
                
                # Delete scenario triggers (and their conditions)
                await master_repo.delete_triggers_by_scenario(scenario_id)
                
                # Delete scenario itself
                await master_repo.delete_scenario(scenario_id)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting scenarios for tenant {tenant_id}: {e}")
            return False
    
    # === Save methods ===
    
    async def save_scenario(self, tenant_id: int, scenario_data: Dict[str, Any]) -> Optional[int]:
        """
        Save scenario to DB
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Create scenario
            scenario_id = await master_repo.create_scenario({
                'tenant_id': tenant_id,
                'scenario_name': scenario_data['scenario_name'],
                'description': scenario_data.get('description', ''),
                'schedule': scenario_data.get('schedule'),  # Cron expression (may be None)
                'is_active': True
            })
            
            return scenario_id
            
        except Exception as e:
            self.logger.error(f"Error saving scenario for tenant {tenant_id}: {e}")
            return None
    
    async def load_scheduled_scenarios(self, tenant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load all scheduled scenarios from DB
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            scenarios = await master_repo.get_scheduled_scenarios(tenant_id)
            return scenarios
            
        except Exception as e:
            self.logger.error(f"Error loading scheduled scenarios: {e}")
            return []
    
    async def save_trigger(self, scenario_id: int, trigger_data: Dict[str, Any]) -> Optional[int]:
        """
        Save scenario trigger to DB
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Create trigger with condition
            trigger_id = await master_repo.create_trigger({
                'scenario_id': scenario_id,
                'condition_expression': trigger_data['condition_expression']
            })
            
            return trigger_id
            
        except Exception as e:
            self.logger.error(f"Error saving trigger for scenario {scenario_id}: {e}")
            return None
    
    async def save_step(self, scenario_id: int, step_data: Dict[str, Any]) -> Optional[int]:
        """
        Save scenario step to DB
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Create step
            step_id = await master_repo.create_step({
                'scenario_id': scenario_id,
                'step_order': step_data['step_order'],
                'action_name': step_data['action_name'],
                'params': step_data.get('params', {}),
                'is_async': step_data.get('is_async', False),
                'action_id': step_data.get('action_id'),
                'is_active': True
            })
            
            # Create step transitions
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
            self.logger.error(f"Error saving step for scenario {scenario_id}: {e}")
            return None