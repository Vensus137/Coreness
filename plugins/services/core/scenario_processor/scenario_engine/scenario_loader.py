"""
Scenario loader from database
Loads scenarios, triggers and steps from database and builds structure for caching
"""

from typing import Any, Dict


class ScenarioLoader:
    """
    Scenario loader from database
    - Load scenarios for tenant
    - Load triggers and scenario steps
    - Build structure for caching
    """
    
    def __init__(self, logger, data_loader, condition_parser):
        self.logger = logger
        self.data_loader = data_loader
        self.condition_parser = condition_parser
    
    async def load_tenant_scenarios(self, tenant_id: int) -> Dict[str, Any]:
        """Load scenarios for specific tenant. Returns cache structure with keys search_tree, scenario_index, scenario_name_index"""
        try:
            # Initialize cache structure for tenant
            cache = {
                'search_tree': {},
                'scenario_index': {},
                'scenario_name_index': {}
            }
            
            # Load all tenant scenarios
            scenarios = await self.data_loader.load_scenarios_by_tenant(tenant_id)
            if not scenarios:
                self.logger.warning(f"No scenarios found for tenant {tenant_id}")
                # Cache empty result to avoid repeating queries
                return cache
            
            # Process each scenario
            for scenario in scenarios:
                scenario_id = scenario['id']
                scenario_name = scenario['scenario_name']
                
                # Create scenario entry in index
                cache['scenario_index'][scenario_id] = {
                    'data': {
                        'id': scenario_id,
                        'name': scenario_name,
                        'raw_data': scenario
                    },
                    'trigger': (),  # Will be filled with tuple after loading triggers
                    'step': ()      # Will be filled with tuple after loading steps
                }
                
                # Add to index for fast name lookup
                cache['scenario_name_index'][scenario_name] = scenario_id
                
                # Load scenario triggers
                await self._load_scenario_trigger(tenant_id, scenario_id, cache)
                
                # Load scenario steps
                await self._load_scenario_step(tenant_id, scenario_id, cache)
            
            return cache
            
        except Exception as e:
            self.logger.error(f"Error loading scenarios for tenant {tenant_id}: {e}")
            # Cache error as empty result to avoid repeating queries
            return {
                'search_tree': {},
                'scenario_index': {},
                'scenario_name_index': {}
            }
    
    async def _load_scenario_trigger(self, tenant_id: int, scenario_id: int, cache: Dict[str, Any]) -> None:
        """Load scenario triggers"""
        try:
            trigger = await self.data_loader.load_triggers_by_scenario(scenario_id)
            
            trigger_list = []
            for trigger_data in trigger:
                trigger_id = trigger_data['id']
                condition_expression = trigger_data.get('condition_expression', '')
                
                # Parse condition using condition_parser
                parsed_condition = await self.condition_parser.parse_condition_string(condition_expression)
                
                # Add trigger to search tree
                if parsed_condition and parsed_condition.get('search_path'):
                    await self.condition_parser.add_to_tree(
                        cache['search_tree'],
                        parsed_condition,
                        'scenario_id',
                        scenario_id
                    )
                
                # Add trigger to list (will be converted to tuple)
                trigger_list.append({
                    'trigger_id': trigger_id,
                    'condition': parsed_condition,
                    'raw_data': trigger_data
                })
            
            # Convert list to tuple (immutable) for safe shallow copy
            cache['scenario_index'][scenario_id]['trigger'] = tuple(trigger_list)
                
        except Exception as e:
            self.logger.error(f"Error loading triggers for scenario {scenario_id}: {e}")
    
    async def _load_scenario_step(self, tenant_id: int, scenario_id: int, cache: Dict[str, Any]) -> None:
        """Load scenario steps"""
        try:
            step = await self.data_loader.load_steps_by_scenario(scenario_id)
            
            step_list = []
            for step_data in step:
                step_id = step_data['id']
                
                # Load step transitions
                transition = await self.data_loader.load_transitions_by_step(step_id)
                
                # Add step to list (will be converted to tuple)
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
            
            # Convert list to tuple (immutable) for safe shallow copy
            cache['scenario_index'][scenario_id]['step'] = tuple(step_list)
                
        except Exception as e:
            self.logger.error(f"Error loading steps for scenario {scenario_id}: {e}")

