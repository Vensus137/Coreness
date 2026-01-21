import os
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml


class PluginsManager:
    """Manager for utilities and services with dependency and DI support"""

    @staticmethod
    def _find_project_root(start_path: Path) -> Path:
        """Reliably determine project root"""
        # First check environment variable
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and Path(env_root).exists():
            return Path(env_root)
        
        # Search by key files/folders
        current = start_path
        while current != current.parent:
            # Check for key project files
            if (current / "plugins").exists() and \
               (current / "app").exists():
                return current
            current = current.parent
        
        # If not found - use fallback
        return start_path.parent.parent.parent.parent

    def __init__(self, plugins_dir: str = "plugins", utilities_dir: str = "utilities", services_dir: str = "services", **kwargs):
        self.logger = kwargs['logger']
        self.plugins_dir = plugins_dir
        self.utilities_dir = utilities_dir
        self.services_dir = services_dir
        
        # Cache for utilities and dependencies information
        self._utilities_info: Dict[str, Dict] = {}
        self._services_info: Dict[str, Dict] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

        # Set project root reliably
        self.project_root = self._find_project_root(Path(__file__))

        # Load information about all utilities and services
        self._load_utilities_and_services_info()

    def _load_utilities_and_services_info(self):
        """Load information about all utilities and services for DI system"""
        self.logger.info("Loading information about utilities and services...")
        self._utilities_info.clear()
        self._services_info.clear()
        self._dependency_graph.clear()

        # Load utilities information (recursively)
        utilities_dir = os.path.join(self.project_root, self.plugins_dir, self.utilities_dir)
        self._scan_plugins_recursively(utilities_dir, "utilities", self._utilities_info)
        
        # Load services information (recursively)
        services_dir = os.path.join(self.project_root, self.plugins_dir, self.services_dir)
        self._scan_plugins_recursively(services_dir, "services", self._services_info)
        
        # Build dependency graph
        self._build_dependency_graph()
        
    def _scan_plugins_recursively(self, root_dir: str, plugin_type: str, target_cache: Dict[str, Dict]):
        """
        Recursively scan directory and load plugin information
        """
        if not os.path.exists(root_dir):
            self.logger.warning(f"Directory {plugin_type} not found: {root_dir}")
            return

        self._scan_directory_recursively(root_dir, plugin_type, target_cache, "")
        self.logger.info(f"Loaded {plugin_type}: {len(target_cache)}")

    def _scan_directory_recursively(self, directory: str, plugin_type: str, target_cache: Dict[str, Dict], relative_path: str):
        """
        Recursively scan directory for plugins
        """
        for item_name in os.listdir(directory):
            item_path = os.path.join(directory, item_name)
            
            if os.path.isdir(item_path):
                # Check if config.yaml exists in this folder
                config_path = os.path.join(item_path, 'config.yaml')
                
                if os.path.exists(config_path):
                    # Found plugin!
                    # Form relative path from project root
                    relative_plugin_path = os.path.relpath(item_path, self.project_root)
                    self._load_plugin_info(relative_plugin_path, item_name, plugin_type, target_cache, relative_path)
                else:
                    # This is a subfolder, continue recursion
                    new_relative_path = os.path.join(relative_path, item_name) if relative_path else item_name
                    self._scan_directory_recursively(item_path, plugin_type, target_cache, new_relative_path)

    def _load_plugin_info(self, plugin_path: str, plugin_name: str, plugin_type: str, target_cache: Dict[str, Dict], relative_path: str):
        """
        Load information about specific plugin
        """
        # Form full path for reading config.yaml
        full_plugin_path = os.path.join(self.project_root, plugin_path)
        config_path = os.path.join(full_plugin_path, 'config.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # Check if plugin is enabled (enabled by default)
            enabled = config.get('enabled', True)
            if not enabled:
                self.logger.info(f"Plugin {plugin_name} disabled in configuration, skipping")
                return
            
            plugin_info = {
                'name': config.get('name', plugin_name),
                'description': config.get('description', ''),
                'type': plugin_type,
                'path': plugin_path,
                'config_path': config_path,
                'relative_path': relative_path,
                'dependencies': config.get('dependencies', []),
                'optional_dependencies': config.get('optional_dependencies', []),
                'settings': config.get('settings', {}),
                'features': config.get('features', []),
                'singleton': config.get('singleton', False)
            }
            
            # Add all fields from config
            plugin_info['methods'] = config.get('methods', {})
            plugin_info['actions'] = config.get('actions', {})
            
            # Check required fields for different types
            if plugin_type == "utilities":
                if not plugin_info['methods']:
                    self.logger.warning(f"Utility {plugin_name} does not have methods section")
                # actions for utilities are optional
            elif plugin_type == "services":
                if not plugin_info['actions']:
                    self.logger.warning(f"Service {plugin_name} does not have actions section")
                # methods for services are no longer required
            
            target_cache[plugin_info['name']] = plugin_info
            
        except Exception as e:
            self.logger.error(f"Error loading config for {plugin_type[:-1]} {plugin_name}: {e}")

    def _load_plugins_info(self, plugin_type: str, plugins_subdir: str, target_cache: Dict[str, Dict]):
        """
        Universal method for loading plugin information (utilities or services)
        """
        plugins_dir = os.path.join(self.project_root, self.plugins_dir, plugins_subdir)
        self._scan_plugins_recursively(plugins_dir, plugin_type, target_cache)

    def _scan_plugins_in_directory(self, directory: str, plugin_type: str, target_cache: Dict[str, Dict], level: str = None):
        """
        Scan directory and load plugin information (deprecated method)
        """
        self.logger.warning("Method _scan_plugins_in_directory is deprecated, use _scan_plugins_recursively")
        self._scan_directory_recursively(directory, plugin_type, target_cache, "")

    def _load_utilities_info(self):
        """Load information about all utilities from plugins/utilities/ (deprecated method)"""
        self.logger.warning("Method _load_utilities_info is deprecated, use _scan_plugins_recursively")
        utilities_dir = os.path.join(self.project_root, self.plugins_dir, self.utilities_dir)
        self._scan_plugins_recursively(utilities_dir, "utilities", self._utilities_info)

    def _load_services_info(self):
        """Load information about all services from plugins/services/ (deprecated method)"""
        self.logger.warning("Method _load_services_info is deprecated, use _scan_plugins_recursively")
        services_dir = os.path.join(self.project_root, self.plugins_dir, self.services_dir)
        self._scan_plugins_recursively(services_dir, "services", self._services_info)

    def _build_dependency_graph(self):
        """Build dependency graph for checking circular dependencies"""
        # Add all utilities and services to graph
        for utility_name in self._utilities_info:
            self._dependency_graph[utility_name] = set()
        
        for service_name in self._services_info:
            self._dependency_graph[service_name] = set()
        
        # Add utility dependencies
        for utility_name, utility_info in self._utilities_info.items():
            for dep in utility_info['dependencies']:
                if dep in self._utilities_info:
                    self._dependency_graph[utility_name].add(dep)
                else:
                    self.logger.warning(f"Utility {utility_name} depends on non-existent utility: {dep}")
        
        # Add service dependencies
        for service_name, service_info in self._services_info.items():
            for dep in service_info['dependencies']:
                if dep in self._utilities_info:
                    self._dependency_graph[service_name].add(dep)
                else:
                    self.logger.warning(f"Service {service_name} depends on non-existent utility: {dep}")


    # === Public methods ===

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        """
        Universal method for getting information about any plugin (utility or service)
        """
        # First try to find as utility
        plugin_info = self._utilities_info.get(plugin_name)
        if plugin_info:
            return plugin_info
        
        # If not found as utility, try as service
        plugin_info = self._services_info.get(plugin_name)
        if plugin_info:
            return plugin_info
        
        return None

    def get_plugin_type(self, plugin_name: str) -> Optional[str]:
        """
        Get plugin type (utility or service)
        """
        plugin_info = self.get_plugin_info(plugin_name)
        return plugin_info.get('type') if plugin_info else None

    def get_all_plugins_info(self) -> Dict[str, Dict]:
        """
        Get information about all plugins (utilities + services)
        """
        all_plugins = {}
        all_plugins.update(self._utilities_info)
        all_plugins.update(self._services_info)
        return all_plugins

    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Dict]:
        """
        Get all plugins of specified type
        """
        if plugin_type == "utilities":
            return self._utilities_info.copy()
        elif plugin_type == "services":
            return self._services_info.copy()
        else:
            self.logger.warning(f"Unknown plugin type: {plugin_type}")
            return {}

    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """
        Get ALL plugin dependencies (mandatory + optional)
        """
        mandatory = self.get_plugin_mandatory_dependencies(plugin_name)
        optional = self.get_plugin_optional_dependencies(plugin_name)
        return mandatory + optional
    
    def get_plugin_mandatory_dependencies(self, plugin_name: str) -> List[str]:
        """
        Get only mandatory plugin dependencies
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return []
        
        return plugin_info.get('dependencies', [])
    
    def get_plugin_optional_dependencies(self, plugin_name: str) -> List[str]:
        """
        Get only optional plugin dependencies
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return []
        
        return plugin_info.get('optional_dependencies', [])

    def reload(self):
        """Reload plugin information"""
        self.logger.info("Reloading plugin information...")
        self._load_utilities_and_services_info() 