import datetime
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv


class SettingsManager:
    """Manager for bot settings and global parameters"""

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
            if (current / "main.py").exists() and \
               (current / "plugins").exists() and \
               (current / "app").exists():
                return current
            current = current.parent
        
        # If not found - use fallback
        return start_path.parent.parent.parent.parent

    def __init__(self, config_dir: str = "config", **kwargs):
        self.logger = kwargs['logger']
        self.plugins_manager = kwargs['plugins_manager']
        self.config_dir = config_dir
        
        # Cache for settings and startup plans
        self._cache: Dict[str, Any] = {}
        
        # Cache for environment variables (variable name -> value)
        self._env_cache: Dict[str, str] = {}
        
        # Application startup time (will get on demand)
        self._startup_time = None
        
        # Set project root reliably
        self.project_root = self._find_project_root(Path(__file__))

        # Load environment variables from .env file
        self._load_environment_variables()

        # Load settings
        self._load_settings()

    def _load_environment_variables(self):
        """Load environment variables from .env file"""
        try:
            load_dotenv(self.project_root / '.env')
            self.logger.info("Environment variables loaded")
        except Exception as e:
            self.logger.warning(f"Error loading environment variables: {e}")

    def _load_settings(self):
        # Load global settings
        global_settings = self._load_yaml_file('settings.yaml')
        
        # Process environment variables in settings
        self._cache['settings'] = self._resolve_env_variables(global_settings)
        
        self.logger.info("Global settings loaded")

    def _load_yaml_file(self, relative_path: str) -> dict:
        """Load YAML file by relative path from config_dir"""
        file_path = os.path.join(self.project_root, self.config_dir, relative_path)
        if os.path.exists(file_path):
            return self._load_yaml_from_path(file_path)
        
        self.logger.warning(f"Configuration file not found: {relative_path}")
        return {}

    def _load_yaml_from_path(self, file_path: str) -> dict:
        """Load YAML file by absolute path"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Process environment variables
                processed_content = self.resolve_env_variables(content)
                return yaml.safe_load(processed_content) or {}
        except Exception as e:
            self.logger.error(f"Error loading file {file_path}: {e}")
            return {}

    def _deep_merge(self, base_dict: dict, override_dict: dict) -> dict:
        """Deep merge dictionaries: override_dict overrides base_dict"""
        result = base_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result

    # === Public methods ===

    def get_startup_time(self):
        """Get application startup time"""
        if self._startup_time is None:
            self._startup_time = self._get_local_time()
        return self._startup_time

    def get_settings_section(self, section: str) -> dict:
        """Get section from settings.yaml by name (e.g., 'logger', 'database_manager')."""
        settings = self._cache.get('settings', {})
        return settings.get(section, {})

    def get_all_settings(self) -> dict:
        """Get all settings from settings.yaml"""
        return self._cache.get('settings', {}).copy()

    def get_project_root(self) -> Path:
        """Get project root"""
        return self.project_root

    def get_global_settings(self) -> dict:
        """Get global settings from 'global' section"""
        return self.get_settings_section('global')

    def get_file_base_path(self) -> str:
        """Get base path for files from global settings"""
        global_settings = self.get_global_settings()
        return global_settings.get('file_base_path', 'resources')

    def _resolve_env_variables(self, data: Any) -> Any:
        """
        Recursively process environment variables in format ${VARIABLE}
        """
        if isinstance(data, dict):
            return {key: self._resolve_env_variables(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_variables(item) for item in data]
        elif isinstance(data, str):
            return self._resolve_env_variable_in_string(data)
        else:
            return data
    
    def _get_env_variable(self, env_var: str) -> str:
        """
        Get environment variable with caching and logging
        """
        # Check cache
        if env_var in self._env_cache:
            return self._env_cache[env_var]
        
        # Get value from environment
        resolved_value = os.getenv(env_var, '')
        
        # Log only once for each variable
        if not resolved_value:
            self.logger.warning(f"Environment variable {env_var} not set")
        
        # Cache result
        self._env_cache[env_var] = resolved_value
        
        return resolved_value
    
    def _resolve_env_variable_in_string(self, value: str) -> str:
        """
        Replace environment variables in string
        """
        if not isinstance(value, str):
            return value
        
        # Check if entire string is an environment variable
        if value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return self._get_env_variable(env_var)
        
        # Check if string contains environment variables
        import re
        pattern = r'\$\{([^}]+)\}'
        
        def replace_env_var(match):
            env_var = match.group(1)
            return self._get_env_variable(env_var)
        
        return re.sub(pattern, replace_env_var, value)
    
    def resolve_env_variables(self, data: Any) -> Any:
        """
        Public method for processing environment variables in data
        """
        return self._resolve_env_variables(data)

    def resolve_file_path(self, path: str) -> str:
        """
        Universal path resolution to absolute.
        Works with any paths: relative, absolute, mixed.
        """
        # If already absolute and in correct base folder - return as is
        base_path = self.get_file_base_path()
        full_base_path = os.path.join(self.project_root, base_path)
        
        if path.startswith(full_base_path):
            return path  # Already correct absolute path
        
        # If relative - resolve
        return os.path.join(self.project_root, base_path, path)

    def get_relative_path(self, path: str) -> str:
        """
        Universal relative path retrieval.
        Works with any paths: relative, absolute, mixed.
        """
        try:
            base_path = self.get_file_base_path()
            full_base_path = os.path.join(self.project_root, base_path)
            
            # If already relative - return as is
            if not os.path.isabs(path):
                return path.replace('\\', '/')  # Already relative, normalize
            
            # If absolute - convert to relative
            if path.startswith(full_base_path):
                relative_path = os.path.relpath(path, full_base_path)
                return relative_path.replace('\\', '/')
            else:
                # If file not in base path, return filename
                return os.path.basename(path)
        except Exception as e:
            self.logger.warning(f"Error getting relative path for {path}: {e}")
            return os.path.basename(path)

    def get_plugin_enabled_status(self, plugin_name: str) -> bool:
        """
        Get plugin enabled status considering new management structure:
        services disabled by default, utilities enabled by default
        """
        # Get merged settings (preset + global)
        management_config = self.get_settings_section('plugin_management') or {}
        
        # Determine plugin type via plugins_manager
        plugin_type = self.plugins_manager.get_plugin_type(plugin_name)
        
        # Apply rules depending on type
        if plugin_type == 'services':
            return self._check_services_rules(plugin_name, management_config.get('services', {}))
        elif plugin_type == 'utilities':
            return self._check_utilities_rules(plugin_name, management_config.get('utilities', {}))
        else:
            # For unknown type return False
            self.logger.warning(f"Unknown plugin type {plugin_name}: {plugin_type}")
            return False

    def _check_services_rules(self, service_name: str, services_config: dict) -> bool:
        """Check service management rules"""
        # Check disabled_services
        if service_name in services_config.get('disabled_services', []):
            return False
        
        # Check enabled_services
        if service_name in services_config.get('enabled_services', []):
            return True
        
        # If service not in lists, use default_enabled
        default_enabled = services_config.get('default_enabled', False)
        return default_enabled
    
    def _check_utilities_rules(self, utility_name: str, utilities_config: dict) -> bool:
        """Check utility management rules"""
        # Check disabled_utilities
        if utility_name in utilities_config.get('disabled_utilities', []):
            return False
        
        # Check enabled_utilities
        if utility_name in utilities_config.get('enabled_utilities', []):
            return True
        
        # If utility not in lists, use default_enabled
        default_enabled = utilities_config.get('default_enabled', True)
        return default_enabled

    def get_plugin_settings(self, plugin_name: str) -> dict:
        """
        Universal method for getting settings of any plugin (utility or service)
        with priority: global from settings.yaml > local from plugin config.yaml
        """
        # Get plugin information from plugins_manager
        plugin_info = self.plugins_manager.get_plugin_info(plugin_name)
        
        if not plugin_info:
            self.logger.warning(f"Plugin {plugin_name} not found")
            return {}
        
        # Global settings from settings.yaml
        global_settings = self.get_settings_section(plugin_name)
        
        # Local settings from plugin config.yaml
        local_settings = plugin_info.get('settings', {})
        
        # Build final dict with priority: global > local
        all_keys = set(global_settings.keys()) | set(local_settings.keys())
        merged = {}
        for key in all_keys:
            global_val = global_settings.get(key, None)
            local_val = local_settings.get(key, None)
            
            # If local parameter is dict with default, take default
            if isinstance(local_val, dict) and 'default' in local_val:
                local_val = local_val['default']
            
            # Priority: global > local
            merged[key] = global_val if global_val is not None else local_val
        
        # Process environment variables in final settings
        return self._resolve_env_variables(merged)

    def get_plugin_info(self, plugin_name: str) -> dict:
        """
        Proxy method for getting full plugin information from PluginsManager
        Returns full plugin configuration including actions, methods, etc.
        """
        return self.plugins_manager.get_plugin_info(plugin_name)

    def reload(self):
        """Reload bot settings and global parameters"""
        self.logger.info("Reloading settings...")
        self._load_settings()
        # Clear startup plan cache on reload
        self.invalidate_startup_cache()
    
    def _get_local_time(self) -> datetime.datetime:
        """Get current local time without dependency on datetime_formatter"""
        import datetime
        from zoneinfo import ZoneInfo

        # Get timezone settings from datetime_formatter (if available)
        # or use default value
        timezone_name = "Europe/Moscow"  # default value
        
        try:
            # Try to get datetime_formatter settings
            datetime_settings = self.get_plugin_settings("datetime_formatter")
            timezone_name = datetime_settings.get('timezone', timezone_name)
        except Exception:
            # If failed to get settings, use default value
            pass
        
        # Create timezone and get local time
        tz = ZoneInfo(timezone_name)
        return datetime.datetime.now(tz).replace(tzinfo=None)
    
    # === Startup planning methods ===
    
    def get_startup_plan(self) -> Dict[str, Any]:
        """Get full application startup plan with caching"""
        self.logger.info("Requesting startup plan...")
        
        try:
            # Check cache initialization
            if not hasattr(self, '_cache') or self._cache is None:
                self.logger.error("Cache not initialized!")
                self._cache = {}
            
            if 'startup_plan' not in self._cache:
                self.logger.info("Startup plan not cached, building...")
                self._cache['startup_plan'] = None
            
            if self._cache['startup_plan'] is None:
                self.logger.info("Building startup plan...")
                try:
                    self._cache['startup_plan'] = self._build_startup_plan()
                    self.logger.info("Startup plan built successfully")
                except Exception as e:
                    self.logger.error(f"Error building startup plan: {e}")
                    # Return empty plan instead of None
                    self._cache['startup_plan'] = {
                        'enabled_services': [],
                        'required_utilities': [],
                        'dependency_order': [],
                        'total_services': 0,
                        'total_utilities': 0
                    }
            else:
                self.logger.info("Using cached startup plan")
            
            return self._cache['startup_plan']
            
        except Exception as e:
            self.logger.error(f"Critical error in get_startup_plan: {e}")
            # Return empty plan in case of critical error
            return {
                'enabled_services': [],
                'required_utilities': [],
                'dependency_order': [],
                'total_services': 0,
                'total_utilities': 0
            }
    
    def get_enabled_services(self) -> List[str]:
        """Get list of enabled services with caching"""
        if 'enabled_services' not in self._cache or self._cache['enabled_services'] is None:
            self._cache['enabled_services'] = self._analyze_enabled_services()
        return self._cache['enabled_services']
    
    def get_required_utilities(self) -> List[str]:
        """Get list of required utilities with caching"""
        if 'required_utilities' not in self._cache or self._cache['required_utilities'] is None:
            self._cache['required_utilities'] = self._analyze_required_utilities()
        return self._cache['required_utilities']
    
    def _build_startup_plan(self) -> Dict[str, Any]:
        """Build full application startup plan"""
        self.logger.info("Building application startup plan...")
        
        # Check plugins_manager availability
        if not self.plugins_manager:
            self.logger.error("PluginsManager unavailable, returning empty plan")
            return {
                'enabled_services': [],
                'required_utilities': [],
                'dependency_order': [],
                'total_services': 0,
                'total_utilities': 0
            }
        
        # Get services that CAN start (enabled + all dependencies available)
        enabled_services = self._analyze_enabled_services()
        
        # Get required utilities directly
        required_utilities = self._analyze_required_utilities(enabled_services)
        
        # Exclude utilities already created in Application (circular dependencies)
        excluded_utilities = ['settings_manager', 'plugins_manager']
        for utility in excluded_utilities:
            if utility in required_utilities:
                required_utilities.remove(utility)
                self.logger.info(f"Excluded {utility} from initialization plan (already created in Application)")
        
        # Build utility initialization order
        dependency_order = self._calculate_dependency_order(required_utilities)
        
        plan = {
            'enabled_services': enabled_services,
            'required_utilities': required_utilities,
            'dependency_order': dependency_order,
            'total_services': len(enabled_services),
            'total_utilities': len(required_utilities)
        }
        
        self.logger.info(f"Startup plan: {plan['total_services']} services, {plan['total_utilities']} utilities")
        
        return plan
    
    def _analyze_enabled_services(self) -> List[str]:
        """Analyze and return services that CAN start (all dependencies available)"""
        # Get all services directly from plugins_manager
        services_info = self.plugins_manager.get_plugins_by_type("services")
        if not services_info:
            self.logger.warning("No services found in PluginsManager")
            return []
        
        # First pass: check basic conditions (existence and enabled status)
        candidate_services = []
        for service_name in services_info.keys():
            # Check enabled status via new plugin_management system
            if self.get_plugin_enabled_status(service_name):
                candidate_services.append(service_name)
            else:
                self.logger.info(f"Service {service_name} disabled via plugin_management")
        
        # Second pass: check startup possibility (all dependencies available)
        can_start_services = []
        excluded_services = []
        
        for service_name in candidate_services:
            # 1. Check plugin itself (existence, enabled status, circular dependencies)
            if not self._can_plugin_start(service_name):
                excluded_services.append(service_name)
                self.logger.warning(f"Service {service_name} excluded: basic checks failed")
                continue
            
            # 2. Check dependencies (transitive dependencies)
            service_dependencies = self._collect_all_transitive_dependencies(service_name)
            if service_name not in service_dependencies:
                self.logger.warning(f"Service {service_name} excluded: unavailable dependencies")
                excluded_services.append(service_name)
                continue
            
            # If passed all checks - can start
            can_start_services.append(service_name)
        
        if excluded_services:
            self.logger.info(f"Excluded services with unavailable dependencies: {len(excluded_services)}")
        
        self.logger.info(f"Can start services: {len(can_start_services)} out of {len(candidate_services)}")
        return can_start_services
    
    def _analyze_required_utilities(self, can_start_services: List[str]) -> List[str]:
        """Analyze and return utilities needed for services that CAN start"""
        # Use passed service list instead of calling _analyze_enabled_services() again
        
        if not can_start_services:
            self.logger.warning("No services that can start")
            return []
        
        # Collect all transitive dependencies for each service
        all_required_utilities = set()
        
        for service_name in can_start_services:
            # Get ALL transitive dependencies of service
            service_dependencies = self._collect_all_transitive_dependencies(service_name)
            
            # Add to common set (exclude service itself)
            service_dependencies.discard(service_name)
            all_required_utilities.update(service_dependencies)
            
        # Filter only enabled utilities
        enabled_utilities = self._filter_enabled_utilities(list(all_required_utilities))
        
        self.logger.info(f"Required utilities for startup: {len(enabled_utilities)} out of {len(all_required_utilities)}")
        return enabled_utilities
    
    def _filter_enabled_utilities(self, utility_names: List[str]) -> List[str]:
        """Filter only enabled utilities"""
        enabled_utilities = []
        disabled_count = 0
        
        for utility_name in utility_names:
            # Check enabled status via new plugin_management system
            if self.get_plugin_enabled_status(utility_name):
                enabled_utilities.append(utility_name)
            else:
                disabled_count += 1
                self.logger.info(f"Utility {utility_name} disabled via plugin_management")
        
        if disabled_count > 0:
            self.logger.info(f"Skipped disabled utilities: {disabled_count}")
        
        return enabled_utilities
    
    def _collect_all_transitive_dependencies(self, plugin_name: str) -> set:
        """Collect ALL transitive dependencies for plugin"""
        collected = set()
        self._collect_transitive_dependencies_recursive(plugin_name, collected, [])
        return collected
    
    def _collect_transitive_dependencies_recursive(self, plugin_name: str, collected: set, path: List[str] = None):
        """Recursively collect transitive dependencies for one plugin"""
        if path is None:
            path = []
        
        # Check circular dependency in current path
        if plugin_name in path:
            # Circular dependency detected
            cycle_start = path.index(plugin_name)
            cycle_path = path[cycle_start:] + [plugin_name]
            self.logger.error(f"Circular dependency detected: {' → '.join(cycle_path)}")
            return  # Avoid infinite recursion
        
        # If already processed this plugin, skip
        if plugin_name in collected:
            return
        
        # Add current plugin to path and collected
        path.append(plugin_name)
        collected.add(plugin_name)
        
        # Get mandatory and optional dependencies separately
        mandatory_deps = self.plugins_manager.get_plugin_mandatory_dependencies(plugin_name)
        optional_deps = self.plugins_manager.get_plugin_optional_dependencies(plugin_name)
        
        # Check availability of mandatory dependencies
        for dep_name in mandatory_deps:
            if not self._is_dependency_available(dep_name):
                self.logger.warning(f"Mandatory dependency {dep_name} for {plugin_name} unavailable - excluding plugin")
                # Clear entire collected for this plugin
                collected.clear()
                path.pop()
                return
        
        # If all mandatory available, process all dependencies
        all_deps = mandatory_deps + optional_deps
        for dep_name in all_deps:
            # For optional dependencies check availability
            if dep_name in optional_deps and not self._is_dependency_available(dep_name):
                # Skip unavailable optional dependency
                continue
            
            # Recursively process dependency
            self._collect_transitive_dependencies_recursive(dep_name, collected, path.copy())
        
        # Remove current plugin from path
        path.pop()
    
    def _is_dependency_available(self, dep_name: str) -> bool:
        """Check dependency availability"""
        # Check existence
        dep_info = self.plugins_manager.get_plugin_info(dep_name)
        if not dep_info:
            return False
        
        # Check enabled status via new plugin_management system
        return self.get_plugin_enabled_status(dep_name)
    
    def _can_plugin_start(self, plugin_name: str) -> bool:
        """Check if plugin can start (basic checks)"""
        # Check plugin existence
        plugin_info = self.plugins_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            self.logger.warning(f"Plugin {plugin_name} not found")
            return False
        
        # Check plugin enabled status via new plugin_management system
        if not self.get_plugin_enabled_status(plugin_name):
            self.logger.info(f"Plugin {plugin_name} disabled via plugin_management")
            return False
        
        # Check circular dependencies in dependency chain
        if self._has_circular_dependencies(plugin_name):
            self.logger.warning(f"Plugin {plugin_name} excluded: circular dependencies detected")
            return False
        
        return True
    
    def _has_circular_dependencies(self, plugin_name: str) -> bool:
        """Check for circular dependencies for plugin"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            # Get node dependencies (ALL dependencies for checking circular dependencies)
            dependencies = self.plugins_manager.get_plugin_dependencies(node)
            
            for neighbor in dependencies:
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Circular dependency detected
                    cycle_start = list(rec_stack).index(neighbor)
                    cycle_path = list(rec_stack)[cycle_start:] + [neighbor]
                    self.logger.error(f"Circular dependency detected: {' → '.join(cycle_path)}")
                    return True
            
            rec_stack.remove(node)
            return False
        
        return has_cycle(plugin_name)
    
    def _calculate_dependency_order(self, utility_names: List[str]) -> List[str]:
        """Calculate correct initialization order for utilities"""
        if not utility_names:
            return []
        
        # Get full dependency graph (ALL dependencies for correct order)
        full_graph = {}
        for utility_name in utility_names:
            deps = self.plugins_manager.get_plugin_dependencies(utility_name)
            # Filter only dependencies that are in our list
            filtered_deps = [dep for dep in deps if dep in utility_names]
            full_graph[utility_name] = set(filtered_deps)
        
        # Topological sort for subset
        def topological_sort(graph: Dict[str, set]) -> List[str]:
            result = []
            visited = set()
            temp_visited = set()
            excluded_nodes = set()  # Nodes with circular dependencies
            
            def visit(node: str):
                if node in temp_visited:
                    # Circular dependency detected - critical error
                    cycle_start = list(temp_visited).index(node)
                    cycle_path = list(temp_visited)[cycle_start:] + [node]
                    self.logger.error(f"Circular dependency detected: {' → '.join(cycle_path)}")
                    
                    # Exclude ALL nodes in cycle
                    for cycle_node in cycle_path:
                        excluded_nodes.add(cycle_node)
                        self.logger.warning(f"Excluded node with circular dependency: {cycle_node}")
                    return
                
                if node in visited:
                    return
                
                temp_visited.add(node)
                
                for neighbor in graph.get(node, set()):
                    visit(neighbor)
                
                temp_visited.remove(node)
                visited.add(node)
                
                # Add node only if not excluded
                if node not in excluded_nodes:
                    result.append(node)
                else:
                    self.logger.warning(f"Node {node} excluded from initialization order")
            
            for node in graph:
                if node not in visited:
                    visit(node)
            
            return result
        
        return topological_sort(full_graph)
    
    def invalidate_startup_cache(self):
        """Invalidate startup plan cache"""
        self._cache['startup_plan'] = None
        self._cache['enabled_services'] = None
        self._cache['required_utilities'] = None
        self.logger.info("Startup plan cache cleared")
    