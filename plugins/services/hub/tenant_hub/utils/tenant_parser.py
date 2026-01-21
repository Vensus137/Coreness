"""
Tenant Parser - submodule for parsing tenant configurations
Parses tenant configurations from files (separately bot and scenarios)
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class TenantParser:
    """
    Submodule for parsing tenant configurations
    Parses separate parts: bot/config or scenarios
    """
    
    def __init__(self, logger, settings_manager, condition_parser):
        self.logger = logger
        self.settings_manager = settings_manager
        self.condition_parser = condition_parser
        
        # Get settings from global (common for all services)
        global_settings = self.settings_manager.get_global_settings()
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        
        # Get maximum nesting depth setting for storage
        tenant_hub_settings = self.settings_manager.get_plugin_settings("tenant_hub")
        self.storage_max_depth = tenant_hub_settings.get("storage_max_depth", 10)
        
        # Path to tenants (single folder without system/public separation)
        # Folder already created in tenant_hub, no check needed
        from pathlib import Path
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
    
    # === Public methods ===
    
    async def parse_bot(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse only bot configuration and commands (without scenarios)
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
            
            # Parse tg_bot.yaml
            bot_data = await self._parse_bot_data(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": bot_data
            }
                
        except Exception as e:
            self.logger.error(f"Error parsing bot configuration: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_scenarios(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse only tenant scenarios (without bot)
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
            scenario_data = await self._parse_scenarios(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": scenario_data
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
    
    async def parse_storage(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse only tenant storage (without bot and scenarios)
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
            
            # Parse storage
            storage_data = await self._parse_storage(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": storage_data
            }
                
        except Exception as e:
            self.logger.error(f"Error parsing storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_tenant_config(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse tenant config from config.yaml file
        Returns dictionary with config (e.g., {"ai_token": "..."})
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
            
            # Parse config.yaml
            config = await self._parse_tenant_config_file(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": config
            }
                
        except Exception as e:
            self.logger.error(f"Error parsing tenant attributes: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_tenant(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse entire tenant configuration (bot + scenarios)
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
            
            # Parse bot
            bot_data = await self._parse_bot_data(tenant_id, tenant_path)
            
            # Parse scenarios
            scenario_data = await self._parse_scenarios(tenant_id, tenant_path)
            
            # Parse storage
            storage_data = await self._parse_storage(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": {
                    "bot": bot_data.get("bot", {}),
                    "bot_commands": bot_data.get("bot_commands", []),
                    "scenarios": scenario_data.get("scenarios", []),
                    "storage": storage_data.get("storage", {})
                }
            }
                
        except Exception as e:
            self.logger.error(f"Error parsing tenant configuration: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    # === Internal methods ===
    
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
    
    async def _parse_bot_data(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Parse bot data (bot + bot_commands)"""
        bot_data = {
            "bot": {},
            "bot_commands": []
        }
        
        # Parse tg_bot.yaml
        bot_file = tenant_path / "tg_bot.yaml"
        if bot_file.exists():
            yaml_data = await self._parse_yaml_file(bot_file)
            
            # Extract bot data
            # bot_token can be None if not specified in config (then used from DB)
            bot_token = yaml_data.get("bot_token")
            # If token is empty string, consider it missing
            if bot_token is not None and not bot_token.strip():
                bot_token = None
            
            bot_data["bot"] = {
                "bot_token": bot_token,
                "is_active": yaml_data.get("is_active", True)
            }
            
            # Extract bot commands
            commands = yaml_data.get("commands", [])
            for cmd in commands:
                bot_data["bot_commands"].append({
                    "action_type": "register",
                    "command": cmd.get("command"),
                    "description": cmd.get("description"),
                    "scope": cmd.get("scope", "default")
                })
            
            # Extract commands for clearing
            command_clear = yaml_data.get("command_clear", [])
            for cmd in command_clear:
                bot_data["bot_commands"].append({
                    "action_type": "clear",
                    "command": None,
                    "description": None,
                    "scope": cmd.get("scope", "default"),
                    "chat_id": cmd.get("chat_id"),
                    "user_id": cmd.get("user_id")
                })
        else:
            self.logger.warning(f"[Tenant-{tenant_id}] File tg_bot.yaml not found")
        
        return bot_data
    
    async def _parse_scenarios(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Parse all tenant scenarios"""
        scenarios = []
        scenarios_path = tenant_path / "scenarios"
        
        if scenarios_path.exists():
            # Parse all YAML files recursively from scenarios (including subfolders)
            for yaml_file in scenarios_path.rglob("*.yaml"):
                file_scenarios = await self._parse_scenario_file(yaml_file)
                scenarios.extend(file_scenarios)
        
        return {
            "scenarios": scenarios
        }
    
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
    
    async def _parse_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse YAML file"""
        try:
            loop = asyncio.get_event_loop()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = await loop.run_in_executor(None, f.read)
            return yaml.safe_load(content) or {}
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return {}
    
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
    
    async def _parse_storage(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Parse storage section from tenant config"""
        storage = {}
        storage_path = tenant_path / "storage"
        
        if storage_path.exists() and storage_path.is_dir():
            # Parse all YAML files in storage folder
            for yaml_file in storage_path.glob("*.yaml"):
                try:
                    # Parse file content
                    yaml_content = await self._parse_yaml_file(yaml_file)
                    
                    # Expected structure: {group_key: {key: value}}
                    if not isinstance(yaml_content, dict):
                        self.logger.warning(f"[Tenant-{tenant_id}] File {yaml_file.name} contains invalid structure, expected dictionary")
                        continue
                    
                    # Process each group in file
                    for group_key, group_data in yaml_content.items():
                        if not isinstance(group_data, dict):
                            self.logger.warning(f"[Tenant-{tenant_id}] Group '{group_key}' in file {yaml_file.name} contains invalid structure, expected dictionary")
                            continue
                        
                        # Validate and normalize group attributes
                        validated_group = await self._validate_and_normalize_storage_group(
                            tenant_id, group_key, group_data, yaml_file.name
                        )
                        
                        if validated_group:
                            # Merge with existing group data (if group already existed in another file)
                            if group_key in storage:
                                # Merge attributes, new ones overwrite old ones
                                storage[group_key].update(validated_group)
                            else:
                                storage[group_key] = validated_group
                        
                except Exception as e:
                    self.logger.error(f"[Tenant-{tenant_id}] Error parsing storage file {yaml_file.name}: {e}")
        
        return {
            "storage": storage
        }
    
    async def _validate_and_normalize_storage_group(
        self, tenant_id: int, group_key: str, group_data: Dict[str, Any], file_name: str
    ) -> Dict[str, Any]:
        """
        Validate and normalize storage attribute group
        
        Supports:
        - Simple types (str, int, float, bool, None)
        - Arrays with simple types or complex structures (dict, list)
        - Dictionaries (dict) with any supported value types
        - Recursive validation of nested structures (maximum depth configured via config.yaml: tenant_hub.storage_max_depth)
        """
        validated_group = {}
        
        for key, value in group_data.items():
            validated_value = await self._validate_storage_value(
                tenant_id, group_key, key, value, file_name, depth=0, max_depth=self.storage_max_depth
            )
            
            if validated_value is not None:
                validated_group[key] = validated_value
        
        return validated_group
    
    async def _validate_storage_value(
        self, tenant_id: int, group_key: str, key: str, value: Any, file_name: str, depth: int = 0, max_depth: int = 10
    ) -> Any:
        """
        Recursively validate storage value with support for complex structures
        
        Supports:
        - Simple types: str, int, float, bool, None
        - Arrays: can contain simple types, dictionaries or other arrays
        - Dictionaries: can contain any supported value types
        
        Parameters:
        - depth: current nesting depth
        - max_depth: maximum nesting depth to prevent recursion
        """
        # Check nesting depth
        if depth > max_depth:
            self.logger.warning(
                f"[Tenant-{tenant_id}] Attribute '{group_key}.{key}' in file {file_name} "
                f"exceeds maximum nesting depth ({max_depth}), skipping."
            )
            return None
        
        # Process dictionaries (JSON objects)
        if isinstance(value, dict):
            validated_dict = {}
            for dict_key, dict_value in value.items():
                nested_key = f"{key}.{dict_key}" if depth > 0 else f"{group_key}.{key}.{dict_key}"
                validated_nested = await self._validate_storage_value(
                    tenant_id, group_key, nested_key, dict_value, file_name, 
                    depth=depth + 1, max_depth=max_depth
                )
                if validated_nested is not None:
                    validated_dict[dict_key] = validated_nested
            
            return validated_dict if validated_dict else None
        
        # Process arrays
        elif isinstance(value, list):
            validated_list = []
            invalid_items = []
            
            for i, item in enumerate(value):
                array_key = f"{key}[{i}]" if depth > 0 else f"{group_key}.{key}[{i}]"
                validated_item = await self._validate_storage_value(
                    tenant_id, group_key, array_key, item, file_name,
                    depth=depth + 1, max_depth=max_depth
                )
                
                if validated_item is not None:
                    validated_list.append(validated_item)
                else:
                    invalid_items.append(i)
            
            # Log invalid items only if there are valid ones
            if invalid_items and validated_list:
                for i in invalid_items:
                    self.logger.warning(
                        f"[Tenant-{tenant_id}] Element '{group_key}.{key}[{i}]' in file {file_name} "
                        f"contains unsupported type, skipping."
                    )
            
            # Return validated array only if it's not empty or empty array was originally valid
            if validated_list or (not invalid_items and len(value) == 0):
                return validated_list
            elif invalid_items:
                # If array is completely invalid, log once
                self.logger.warning(
                    f"[Tenant-{tenant_id}] Attribute '{group_key}.{key}' in file {file_name} "
                    f"contains array with invalid elements, skipping."
                )
            return None
        
        # Process simple types
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        
        # Process other types - try to convert to string
        else:
            original_type = type(value).__name__
            try:
                str_value = str(value)
                self.logger.warning(
                    f"[Tenant-{tenant_id}] Attribute '{group_key}.{key}' in file {file_name} "
                    f"was converted to string from {original_type}"
                )
                return str_value
            except Exception as e:
                self.logger.error(
                    f"[Tenant-{tenant_id}] Failed to convert attribute '{group_key}.{key}' "
                    f"in file {file_name}: {e}. Skipping."
                )
                return None
    
    async def _parse_tenant_config_file(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """
        Parse config.yaml file with tenant config
        Returns dictionary with config (e.g., {"ai_token": "..."})
        If file doesn't exist or field is empty → don't add to dictionary
        """
        config = {}
        tenant_file = tenant_path / "config.yaml"
        
        if tenant_file.exists():
            yaml_data = await self._parse_yaml_file(tenant_file)
            
            # Extract ai_token (priority) or openrouter_token (backward compatibility)
            ai_token = yaml_data.get("ai_token")
            if not ai_token:
                # Backward compatibility: check old field
                ai_token = yaml_data.get("openrouter_token")
            # If token is empty string, consider it missing
            if ai_token is not None and ai_token.strip():
                config["ai_token"] = ai_token.strip()
                # Also save to old field for backward compatibility
                config["openrouter_token"] = ai_token.strip()
        else:
            # File doesn't exist - this is normal, return empty dictionary
            pass
        
        return config

