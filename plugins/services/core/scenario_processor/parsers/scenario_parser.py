"""
Scenario Parser - parser for tenant scenario configurations
Parses scenarios/*.yaml files
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ScenarioParser:
    """
    Parser for tenant scenario configurations
    Handles parsing of scenarios/*.yaml files recursively
    """
    
    def __init__(self, logger, settings_manager, condition_parser):
        self.logger = logger
        self.settings_manager = settings_manager
        self.condition_parser = condition_parser
        
        # Get settings from global (common for all services)
        global_settings = self.settings_manager.get_global_settings()
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        
        # Path to tenants
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
    
    async def parse_scenarios(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse all tenant scenarios from scenarios/*.yaml
        
        Returns dict with scenarios list
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id not specified"
                    }
                }
            
            # Get tenant path
            tenant_path = await self._get_tenant_path(tenant_id)
            if not tenant_path:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Tenant {tenant_id} not found"
                    }
                }
            
            # Parse scenarios
            scenario_data = await self._parse_scenarios_files(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": {
                    "scenarios": scenario_data
                }
            }
                
        except Exception as e:
            self.logger.error(f"Error parsing scenarios: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def _get_tenant_path(self, tenant_id: int) -> Optional[Path]:
        """Get path to tenant folder"""
        try:
            tenant_name = f"tenant_{tenant_id}"
            tenant_path = self.tenants_path / tenant_name
            
            # Check tenant folder existence
            if not tenant_path.exists():
                self.logger.warning(f"Tenant folder not found: {tenant_path}")
                return None
            
            return tenant_path
            
        except Exception as e:
            self.logger.error(f"Error getting path to tenant {tenant_id}: {e}")
            return None
    
    async def _parse_scenarios_files(self, tenant_id: int, tenant_path: Path) -> List[Dict[str, Any]]:
        """Parse all tenant scenarios from scenarios folder"""
        scenarios = []
        scenarios_path = tenant_path / "scenarios"
        
        if scenarios_path.exists():
            # Parse all YAML files recursively from scenarios (including subfolders)
            for yaml_file in scenarios_path.rglob("*.yaml"):
                file_scenarios = await self._parse_scenario_file(yaml_file)
                scenarios.extend(file_scenarios)
        
        return scenarios
    
    async def _parse_scenario_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse scenario file"""
        scenarios = []
        
        try:
            loop = asyncio.get_event_loop()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = await loop.run_in_executor(None, f.read)
            
            yaml_content = yaml.safe_load(content) or {}
            
            # Process each scenario in file
            for scenario_name, scenario_data in yaml_content.items():
                if isinstance(scenario_data, dict):
                    # Parse triggers
                    parsed_trigger = await self._parse_scenario_trigger(scenario_data.get("trigger", []))
                    
                    # Parse steps
                    parsed_step = await self._parse_scenario_step(scenario_data.get("step", []))
                    
                    scenario = {
                        "scenario_name": scenario_name,
                        "description": scenario_data.get("description"),
                        "schedule": scenario_data.get("schedule"),  # Cron expression for scheduled scenarios
                        "trigger": parsed_trigger,
                        "step": parsed_step
                    }
                    scenarios.append(scenario)
            
        except Exception as e:
            self.logger.error(f"Error parsing scenario file {file_path}: {e}")
        
        return scenarios
    
    async def _parse_scenario_trigger(self, trigger: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse scenario triggers to DB format using condition_parser"""
        parsed_trigger = []
        
        for trigger_data in trigger:
            # Use condition_parser.build_condition to create condition
            condition_expression = await self.condition_parser.build_condition([trigger_data])
            
            parsed_trigger.append({
                "condition_expression": condition_expression
            })
        
        return parsed_trigger
    
    async def _parse_scenario_step(self, step: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse scenario steps to DB format"""
        parsed_step = []
        
        for step_order, step_data in enumerate(step):
            # Take params as is (dict)
            params = step_data.get("params", {})
            
            parsed_step.append({
                "step_order": step_order,
                "action_name": step_data.get("action") or step_data.get("action_name"),
                "params": params,
                "is_async": step_data.get("async", False),
                "action_id": step_data.get("action_id"),
                "transition": step_data.get("transition", [])
            })
        
        return parsed_step
