"""
Telegram Bot Parser - parser for Telegram bot configurations
Parses bots/telegram.yaml files
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class TelegramBotParser:
    """
    Parser for Telegram bot configurations
    Handles parsing of bots/telegram.yaml
    """
    
    def __init__(self, logger, settings_manager):
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Get settings from global (common for all services)
        global_settings = self.settings_manager.get_global_settings()
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        
        # Path to tenants
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
    
    async def parse_bot_config(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Parse bots/telegram.yaml for tenant
        """
        try:
            tenant_name = f"tenant_{tenant_id}"
            tenant_path = self.tenants_path / tenant_name
            
            if not tenant_path.exists():
                self.logger.warning(f"[Tenant-{tenant_id}] Tenant folder not found: {tenant_path}")
                return None
            
            config_file = tenant_path / "bots" / "telegram.yaml"
            
            if not config_file.exists():
                return None
            
            # Parse YAML
            loop = asyncio.get_event_loop()
            with open(config_file, 'r', encoding='utf-8') as f:
                content = await loop.run_in_executor(None, f.read)
            
            config = yaml.safe_load(content) or {}
            
            return config
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error parsing telegram.yaml: {e}")
            return None
