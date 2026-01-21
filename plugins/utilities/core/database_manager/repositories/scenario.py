"""
Repository for working with scenarios
Contains methods for getting scenarios and their components from DB
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select

from ..models import Scenario, ScenarioStep, ScenarioStepTransition, ScenarioTrigger
from .base import BaseRepository


class ScenarioRepository(BaseRepository):
    """
    Repository for working with scenarios
    """
    
    def __init__(self, session_factory, **kwargs):
        super().__init__(session_factory, **kwargs)
    
    async def get_scenarios_by_tenant(self, tenant_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get all scenarios for tenant
        """
        try:
            with self._get_session() as session:
                stmt = select(Scenario).where(Scenario.tenant_id == tenant_id)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting scenarios for tenant {tenant_id}: {e}")
            return None
    
    async def get_triggers_by_scenario(self, scenario_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get scenario triggers
        """
        try:
            with self._get_session() as session:
                stmt = select(ScenarioTrigger).where(ScenarioTrigger.scenario_id == scenario_id)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting triggers for scenario {scenario_id}: {e}")
            return None
    
    async def get_steps_by_scenario(self, scenario_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get scenario steps
        """
        try:
            with self._get_session() as session:
                stmt = select(ScenarioStep).where(ScenarioStep.scenario_id == scenario_id)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting steps for scenario {scenario_id}: {e}")
            return None
    
    async def get_transitions_by_step(self, step_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Get step transitions
        """
        try:
            with self._get_session() as session:
                stmt = select(ScenarioStepTransition).where(ScenarioStepTransition.step_id == step_id)
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting transitions for step {step_id}: {e}")
            return None
    
    # === Deletion methods ===
    
    async def delete_steps_by_scenario(self, scenario_id: int) -> Optional[bool]:
        """
        Delete all scenario steps (including their transitions)
        """
        try:
            with self._get_session() as session:
                # First delete step transitions
                stmt_transitions = delete(ScenarioStepTransition).where(
                    ScenarioStepTransition.step_id.in_(
                        select(ScenarioStep.id).where(ScenarioStep.scenario_id == scenario_id)
                    )
                )
                session.execute(stmt_transitions)
                
                # Then delete steps themselves
                stmt_steps = delete(ScenarioStep).where(ScenarioStep.scenario_id == scenario_id)
                session.execute(stmt_steps)
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error deleting steps for scenario {scenario_id}: {e}")
            return None
    
    async def delete_triggers_by_scenario(self, scenario_id: int) -> Optional[bool]:
        """
        Delete all scenario triggers
        """
        try:
            with self._get_session() as session:
                stmt_triggers = delete(ScenarioTrigger).where(ScenarioTrigger.scenario_id == scenario_id)
                session.execute(stmt_triggers)
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error deleting triggers for scenario {scenario_id}: {e}")
            return None
    
    async def delete_scenario(self, scenario_id: int) -> Optional[bool]:
        """
        Delete scenario
        """
        try:
            with self._get_session() as session:
                stmt = delete(Scenario).where(Scenario.id == scenario_id)
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error deleting scenario {scenario_id}: {e}")
            return None
    
    # === Creation methods ===
    
    async def create_scenario(self, scenario_data: Dict[str, Any]) -> Optional[int]:
        """
        Create scenario
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=Scenario,
                    fields={
                        'tenant_id': scenario_data.get('tenant_id'),
                        'scenario_name': scenario_data.get('scenario_name'),
                        'description': scenario_data.get('description', ''),
                        'schedule': scenario_data.get('schedule'),  # Cron expression (can be None)
                        'last_scheduled_run': scenario_data.get('last_scheduled_run')  # Last run time (can be None)
                    },
                    json_fields=[]
                )
                
                stmt = insert(Scenario).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                scenario_id = result.inserted_primary_key[0]
                return scenario_id
                
        except Exception as e:
            self.logger.error(f"Error creating scenario: {e}")
            return None
    
    async def create_trigger(self, trigger_data: Dict[str, Any]) -> Optional[int]:
        """
        Create scenario trigger
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=ScenarioTrigger,
                    fields={
                        'scenario_id': trigger_data.get('scenario_id'),
                        'condition_expression': trigger_data.get('condition_expression')
                    },
                    json_fields=[]
                )
                
                stmt = insert(ScenarioTrigger).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                trigger_id = result.inserted_primary_key[0]
                return trigger_id
                
        except Exception as e:
            self.logger.error(f"Error creating trigger: {e}")
            return None
    
    async def create_step(self, step_data: Dict[str, Any]) -> Optional[int]:
        """
        Create scenario step
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=ScenarioStep,
                    fields={
                        'scenario_id': step_data.get('scenario_id'),
                        'step_order': step_data.get('step_order'),
                        'action_name': step_data.get('action_name'),
                        'params': step_data.get('params', {}),
                        'is_async': step_data.get('is_async', False),
                        'action_id': step_data.get('action_id')
                    },
                    json_fields=['params']  # params is JSON field
                )
                
                stmt = insert(ScenarioStep).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                step_id = result.inserted_primary_key[0]
                return step_id
                
        except Exception as e:
            self.logger.error(f"Error creating step: {e}")
            return None
    
    async def create_transition(self, transition_data: Dict[str, Any]) -> Optional[int]:
        """
        Create step transition
        """
        try:
            with self._get_session() as session:
                # Prepare data for insertion via data_preparer
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=ScenarioStepTransition,
                    fields={
                        'step_id': transition_data.get('step_id'),
                        'action_result': transition_data.get('action_result', 'success'),
                        'transition_action': transition_data.get('transition_action', 'continue'),
                        'transition_value': transition_data.get('transition_value')
                    },
                    json_fields=[]  # transition_value is regular string, not JSON
                )
                
                stmt = insert(ScenarioStepTransition).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                transition_id = result.inserted_primary_key[0]
                return transition_id
                
        except Exception as e:
            self.logger.error(f"Error creating transition: {e}")
            return None
    
    # === Methods for scheduled scenarios ===
    
    async def get_scheduled_scenarios(self, tenant_id: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get all scheduled scenarios (with schedule IS NOT NULL)
        """
        try:
            with self._get_session() as session:
                stmt = select(Scenario).where(
                    Scenario.schedule.isnot(None)
                )
                
                # If tenant_id specified - add filter
                if tenant_id is not None:
                    stmt = stmt.where(Scenario.tenant_id == tenant_id)
                
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                
        except Exception as e:
            self.logger.error(f"Error getting scheduled scenarios: {e}")
            return None
    
    async def update_scenario_last_run(self, scenario_id: int, last_run: datetime) -> Optional[bool]:
        """
        Update last run time of scheduled scenario
        """
        try:
            with self._get_session() as session:
                from sqlalchemy import update
                
                stmt = update(Scenario).where(
                    Scenario.id == scenario_id
                ).values(
                    last_scheduled_run=last_run
                )
                
                session.execute(stmt)
                session.commit()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating last_scheduled_run for scenario {scenario_id}: {e}")
            return None
    
