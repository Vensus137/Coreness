import importlib.util
from typing import Any, Dict, List, Optional, Type


class DIContainer:
    """DI container for managing plugin dependencies"""
    
    def __init__(self, logger: Any, plugins_manager: Any, settings_manager: Any = None):
        self.logger = logger
        self.plugins_manager = plugins_manager
        self.settings_manager = settings_manager
        
        # Caches for instances and classes
        self._utilities: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._utilities_classes: Dict[str, Type] = {}
        self._services_classes: Dict[str, Type] = {}
        
        # Register passed utilities as already initialized
        self._utilities['logger'] = logger
        self._utilities['plugins_manager'] = plugins_manager
        self._utilities['settings_manager'] = settings_manager
        
        # Initialization flags
        self._utilities_initialized = False
        self._services_initialized = False
    
    def initialize_all_plugins(self):
        """Initialize all plugins according to plan from SettingsManager"""
        self.logger.info("Starting initialization of all plugins...")
        
        # Check SettingsManager availability
        if self.settings_manager is None:
            self.logger.error("SettingsManager not passed to DIContainer")
            return
        
        # Get startup plan from SettingsManager
        startup_plan = self.settings_manager.get_startup_plan()
        
        if not startup_plan:
            self.logger.error("SettingsManager failed to build startup plan")
            return
        
        self.logger.info(f"Startup plan: {startup_plan['total_services']} services, {startup_plan['total_utilities']} utilities")
        
        # Initialize utilities in correct order
        self._initialize_utilities_from_plan(startup_plan['dependency_order'])
        
        # Initialize services
        self._initialize_services_from_plan(startup_plan['enabled_services'])
        
        self.logger.info("All plugins successfully initialized")
    
    def get_startup_plan(self) -> Optional[Dict[str, Any]]:
        """Get startup plan from SettingsManager"""
        return self.settings_manager.get_startup_plan()
    
    def _initialize_utilities_from_plan(self, dependency_order: List[str]):
        """Initialize utilities according to plan from SettingsManager"""
        if self._utilities_initialized:
            return
        
        for utility_name in dependency_order:
            self._register_utility_from_manager(utility_name)
        
        self._utilities_initialized = True
        self.logger.info(f"Initialized utilities: {len(self._utilities)}")
    
    def _initialize_services_from_plan(self, enabled_services: List[str]):
        """Initialize services according to plan from SettingsManager"""
        if self._services_initialized:
            return
        
        for service_name in enabled_services:
            self._register_service_from_manager(service_name)
        
        self._services_initialized = True
        self.logger.info(f"Initialized services: {len(self._services)}")
    
    def _register_utility_from_manager(self, utility_name: str):
        """Register utility from PluginsManager"""
        utility_info = self.plugins_manager.get_plugin_info(utility_name)
        if not utility_info:
            self.logger.error(f"Information about utility {utility_name} not found")
            return
        
        try:
            # Load utility class
            utility_class = self._load_plugin_class(utility_info)
            if not utility_class:
                return
            
            # Check if utility is singleton
            is_singleton = utility_info.get('singleton', False)
            
            if is_singleton:
                # Create instance immediately for singleton
                instance = self._create_utility_instance(utility_name, utility_class)
                self._utilities[utility_name] = instance
            else:
                # Save only class for non-singleton
                self._utilities_classes[utility_name] = utility_class
                
        except Exception as e:
            self.logger.error(f"Error registering utility {utility_name}: {e}")
    
    def _register_service_from_manager(self, service_name: str):
        """Register service from PluginsManager"""
        service_info = self.plugins_manager.get_plugin_info(service_name)
        if not service_info:
            self.logger.error(f"Information about service {service_name} not found")
            return
        
        try:
            # Load service class
            service_class = self._load_plugin_class(service_info)
            if not service_class:
                return
            
            # Check if service is singleton
            is_singleton = service_info.get('singleton', False)
            
            if is_singleton:
                # Create instance immediately for singleton
                instance = self._create_service_instance(service_name, service_class)
                self._services[service_name] = instance
            else:
                # Save only class for non-singleton
                self._services_classes[service_name] = service_class
                
        except Exception as e:
            self.logger.error(f"Error registering service {service_name}: {e}")
    
    def _load_plugin_class(self, plugin_info: Dict) -> Optional[Type]:
        """Load plugin class from file"""
        plugin_path = plugin_info['path']
        plugin_name = plugin_info['name']
        
        # Determine class file name (usually folder name + .py)
        class_file_name = f"{plugin_name}.py"
        class_file_path = f"{plugin_path}/{class_file_name}"
        
        # If file with folder name not found, search for other .py files
        if not self._file_exists(class_file_path):
            # Search for any .py file in plugin folder
            py_files = self._find_py_files(plugin_path)
            if not py_files:
                self.logger.error(f"No .py files found in plugin folder: {plugin_path}")
                return None
            class_file_path = py_files[0]  # Take first found .py file
        
        try:
            # Load module with correct __package__ setup
            module_name = f"plugin_{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, class_file_path)
            module = importlib.util.module_from_spec(spec)
            
            # Set __package__ for correct relative import handling
            # Convert path to universal format (replace all separators with '/')
            universal_path = plugin_path.replace('\\', '/')
            # Replace '/' with '.' to create package name
            module.__package__ = universal_path.replace('/', '.')
            
            spec.loader.exec_module(module)
            
            # Search for class with name matching plugin name
            class_name = self._get_class_name_from_module(module, plugin_name)
            if class_name:
                # If class found, return it
                plugin_class = getattr(module, class_name)
                return plugin_class
            else:
                # If class not found, return module itself (for modules with functions)
                return module
            
        except Exception as e:
            self.logger.error(f"Error loading class for plugin {plugin_name}: {e}")
            return None
    
    def _file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        import os
        return os.path.exists(file_path)
    
    def _find_py_files(self, directory: str) -> List[str]:
        """Search for .py files in directory"""
        import os
        py_files = []
        for file in os.listdir(directory):
            if file.endswith('.py') and not file.startswith('__'):
                py_files.append(os.path.join(directory, file))
        return py_files
    
    def _get_class_name_from_module(self, module: Any, plugin_name: str) -> Optional[str]:
        """Search for class name in module or return module itself"""
        
        # First search for class with name matching plugin name
        class_name = plugin_name.replace('_', '').title()  # logger -> Logger
        if hasattr(module, class_name):
            attr = getattr(module, class_name)
            if isinstance(attr, type):
                return class_name
        
        # If not found, search for classes that might be main classes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and not attr_name.startswith('_'):
                # Check that it's not a builtin class, not typing.Any or other types
                # And that class is defined in this module (not imported)
                if (not attr.__module__.startswith('builtins') and 
                    attr is not type and 
                    not attr.__module__.startswith('typing') and
                    attr_name not in ['Any', 'Dict', 'List', 'Optional', 'Type', 'Path'] and
                    not attr.__module__.startswith('pathlib') and
                    attr.__module__ == module.__name__):  # Class must be defined in this module
                    return attr_name
        
        # If class not found, return None (will use module itself)
        return None
    
    def _create_utility_instance(self, utility_name: str, utility_class: Type, use_on_demand: bool = False) -> Any:
        """Create utility instance with dependency injection"""
        
        # Check if this is a module (not a class)
        if hasattr(utility_class, '__file__'):
            # This is a module, return it as is
            return utility_class
        
        # Get ALL utility dependencies (required + optional)
        dependencies = self.plugins_manager.get_plugin_dependencies(utility_name)
        
        # Create dependency dictionary for passing to constructor
        deps_dict = {}
        missing_deps = []
        
        for dep_name in dependencies:
            # Choose dependency retrieval method based on flag
            if use_on_demand:
                dep_instance = self.get_utility_on_demand(dep_name)
            else:
                dep_instance = self.get_utility(dep_name)
                
            if dep_instance:
                # If this is logger, create named logger for utility
                if dep_name == 'logger' and utility_name != 'logger':
                    deps_dict[dep_name] = dep_instance.get_logger(utility_name)
                else:
                    deps_dict[dep_name] = dep_instance
            else:
                missing_deps.append(dep_name)
                self.logger.warning(f"Dependency {dep_name} for utility {utility_name} not found - will be skipped")
        
        # Log dependency information (only if there are problems)
        if missing_deps:
            pass
        
        # Create instance with dependencies
        try:
            if deps_dict:
                # Pass dependencies as named arguments
                # Constructor will extract needed dependencies from kwargs
                instance = utility_class(**deps_dict)
            else:
                # If no dependencies, create without arguments
                instance = utility_class()
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Error creating utility instance {utility_name}: {e}")
            raise
    
    def _create_service_instance(self, service_name: str, service_class: Type) -> Any:
        """Create service instance with dependency injection"""
        
        # Get ALL service dependencies (required + optional)
        dependencies = self.plugins_manager.get_plugin_dependencies(service_name)
        
        # Create dependency dictionary for passing to constructor
        deps_dict = {}
        missing_deps = []
        
        for dep_name in dependencies:
            # Services can depend on utilities
            dep_instance = self.get_utility(dep_name)
            if dep_instance:
                # If this is logger, create named logger for service
                if dep_name == 'logger':
                    deps_dict[dep_name] = dep_instance.get_logger(service_name)
                else:
                    deps_dict[dep_name] = dep_instance
            else:
                missing_deps.append(dep_name)
                self.logger.warning(f"Dependency {dep_name} for service {service_name} not found - will be skipped")
        
        # Log dependency information (only if there are problems)
        if missing_deps:
            pass
        
        # Create instance with dependencies
        try:
            if deps_dict:
                # Pass dependencies as named arguments
                # Constructor will extract needed dependencies from kwargs
                instance = service_class(**deps_dict)
            else:
                # If no dependencies, create without arguments
                instance = service_class()
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Error creating service instance {service_name}: {e}")
            raise
    
    def get_utility(self, name: str) -> Optional[Any]:
        """Get utility by name"""
        if name in self._utilities:
            return self._utilities[name]
        
        if name in self._utilities_classes:
            # Create instance for non-singleton
            utility_class = self._utilities_classes[name]
            instance = self._create_utility_instance(name, utility_class)
            return instance
        
        return None
    
    def get_utility_on_demand(self, name: str) -> Optional[Any]:
        """Get utility on demand, even if it's not in startup plan"""
        
        # First try standard method
        utility = self.get_utility(name)
        if utility:
            return utility
        
        # If not found - load from PluginsManager
        utility_info = self.plugins_manager.get_plugin_info(name)
        if not utility_info:
            self.logger.warning(f"Utility {name} not found in PluginsManager")
            return None
        
        try:
            # Load utility class
            utility_class = self._load_plugin_class(utility_info)
            if not utility_class:
                self.logger.error(f"Failed to load utility class {name}")
                return None
            
            # Create instance with on_demand flag
            instance = self._create_utility_instance(name, utility_class, use_on_demand=True)
            
            # Register for future use
            is_singleton = utility_info.get('singleton', False)
            if is_singleton:
                self._utilities[name] = instance
                self.logger.info(f"Utility {name} created and registered as singleton")
            else:
                self._utilities_classes[name] = utility_class
                self.logger.info(f"Utility class {name} registered for on-demand creation")
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Error creating utility {name}: {e}")
            return None
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get service by name"""
        if name in self._services:
            return self._services[name]
        
        if name in self._services_classes:
            # Create instance for non-singleton
            service_class = self._services_classes[name]
            instance = self._create_service_instance(name, service_class)
            return instance
        
        return None
    
    def get_all_utilities(self) -> Dict[str, Any]:
        """Get all registered utilities"""
        return self._utilities.copy()
    
    def get_all_services(self) -> Dict[str, Any]:
        """Get all registered services (singleton + non-singleton)"""
        all_services = self._services.copy()  # singleton services
        
        # Add non-singleton services, creating instances
        for service_name, service_class in self._services_classes.items():
            try:
                instance = self._create_service_instance(service_name, service_class)
                all_services[service_name] = instance
            except Exception as e:
                self.logger.error(f"Error creating service instance {service_name}: {e}")
        
        return all_services
    
    def shutdown(self):
        """Graceful container termination"""
        self.logger.info("Shutting down DI container...")
        
        # Call shutdown on all utilities if they have such method
        # Plugins stop their internal background tasks (polling, task processors, cache cleanup, etc.)
        for utility_name, utility_instance in self._utilities.items():
            if hasattr(utility_instance, 'shutdown'):
                try:
                    self.logger.info(f"Shutting down utility {utility_name}")
                    utility_instance.shutdown()
                except Exception as e:
                    self.logger.error(f"Error shutting down utility {utility_name}: {e}")
        
        # Call shutdown on all services if they have such method
        for service_name, service_instance in self._services.items():
            if hasattr(service_instance, 'shutdown'):
                try:
                    service_instance.shutdown()
                except Exception as e:
                    self.logger.error(f"Error shutting down service {service_name}: {e}")
        
        # Clear caches
        self._utilities.clear()
        self._services.clear()
        self._utilities_classes.clear()
        self._services_classes.clear()
        
        self.logger.info("DI container terminated") 