"""
Scenario finder by events
Determines tenant_id from event and finds matching scenarios through search tree
"""

from typing import Any, Dict, List, Optional


class ScenarioFinder:
    """
    Scenario finder by events
    - Extract tenant_id from event
    - Find matching scenarios through search tree
    """
    
    def __init__(self, logger, condition_parser):
        self.logger = logger
        self.condition_parser = condition_parser
    
    def extract_tenant_id(self, event: Dict[str, Any]) -> Optional[int]:
        """Extract tenant_id from event system field"""
        try:
            # tenant_id should be in event system field
            if 'system' in event and 'tenant_id' in event['system']:
                tenant_id = event['system']['tenant_id']
                if isinstance(tenant_id, int):
                    return tenant_id
            
            # If tenant_id is missing from system field - this is an error
            self.logger.warning("tenant_id missing from event system field - event cannot be processed")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting tenant_id: {e}")
            return None
    
    async def find_scenarios_by_event(self, tenant_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> List[int]:
        """Find matching scenarios by event through search tree"""
        try:
            # Use scenario metadata for isolated processing
            search_tree = scenario_metadata['search_tree']
            
            # Check that search tree is not empty
            if not search_tree:
                return []
            
            # Search for scenario_id in search tree
            scenario_ids = await self.condition_parser.search_in_tree(search_tree, event)
            
            if not scenario_ids:
                return []
            
            # Filter only existing scenarios
            existing_scenarios = []
            scenario_index = scenario_metadata['scenario_index']
            for scenario_id in scenario_ids:
                if scenario_id in scenario_index:
                    existing_scenarios.append(scenario_id)
                else:
                    self.logger.warning(f"Found scenario_id {scenario_id} in search tree, but missing from index")
            
            return existing_scenarios
            
        except Exception as e:
            self.logger.error(f"Error finding scenarios by event for tenant {tenant_id}: {e}")
            return []

