import asyncio
from typing import Any, Dict, List

from .types import QueueConfig


class QueueManager:
    """Queue and limit management"""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Get queue settings
        settings = self.settings_manager.get_plugin_settings('task_manager') if self.settings_manager else {}
        queues_settings = settings.get('queues', {})
        self.queue_configs = self._load_queue_configs(queues_settings)
        
        # Settings from TaskManager
        self.wait_interval = kwargs.get('wait_interval', 1.0)
        
        # Semaphores for resource control
        self.semaphores = {
            queue_name: asyncio.Semaphore(config.max_concurrent)
            for queue_name, config in self.queue_configs.items()
        }
        
        # Task queues
        self.task_queues = {
            queue_name: asyncio.Queue()
            for queue_name in self.queue_configs.keys()
        }
        
    
    def _load_queue_configs(self, queues_settings: Dict[str, Any]) -> Dict[str, QueueConfig]:
        """Loads queue configurations"""
        configs = {}
        
        # Skip service fields (type, description)
        for queue_name, queue_settings in queues_settings.items():
            if queue_name in ['type', 'description']:
                continue
                
            config = QueueConfig(
                name=queue_name,
                max_concurrent=queue_settings.get('max_concurrent', 10),
                timeout=queue_settings.get('timeout', 60.0),
                retry_count=queue_settings.get('retry_count', 3),
                retry_delay=queue_settings.get('retry_delay', 1.0)
            )
            configs[queue_name] = config
        
        return configs
    
    # Public methods for working with queues
    def get_available_queues(self) -> List[str]:
        """Returns list of available queues"""
        return list(self.queue_configs.keys())
    
    def is_queue_valid(self, queue_name: str) -> bool:
        """Checks if queue exists"""
        return queue_name in self.queue_configs
    
    def get_queue_config(self, queue_name: str) -> QueueConfig:
        """Gets queue configuration"""
        return self.queue_configs[queue_name]
    
