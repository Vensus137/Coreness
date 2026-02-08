"""
Storage Parser - parser for tenant storage configurations
Parses storage/*.yaml files and validates structure
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class StorageParser:
    """
    Parser for tenant storage configurations
    Handles parsing and validation of storage/*.yaml files
    """
    
    def __init__(self, logger, settings_manager):
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Get settings from global (common for all services)
        global_settings = self.settings_manager.get_global_settings()
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        
        # Get maximum nesting depth setting for storage
        storage_hub_settings = self.settings_manager.get_plugin_settings("storage_hub")
        self.storage_max_depth = storage_hub_settings.get("storage_max_depth", 20)
        
        # Path to tenants
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
    
    async def parse_storage(self, tenant_id: int) -> Dict[str, Any]:
        """
        Parse storage section from tenant config
        
        Returns dict with storage structure: {group_key: {key: value}}
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
            storage_data = await self._parse_storage_files(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": {
                    "storage": storage_data
                }
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
    
    async def _parse_storage_files(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Parse all storage YAML files from tenant storage folder"""
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
        
        return storage
    
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
    
    async def _validate_and_normalize_storage_group(
        self, tenant_id: int, group_key: str, group_data: Dict[str, Any], file_name: str
    ) -> Dict[str, Any]:
        """
        Validate and normalize storage attribute group
        
        Supports:
        - Simple types (str, int, float, bool, None)
        - Arrays with simple types or complex structures (dict, list)
        - Dictionaries (dict) with any supported value types
        - Recursive validation of nested structures (maximum depth configured via config.yaml: storage_hub.storage_max_depth)
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
        self, tenant_id: int, group_key: str, key: str, value: Any, file_name: str, depth: int = 0, max_depth: int = 20
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
