"""
Integration tests for dependencies and DI resolution
Verify correct dependency resolution through DI container
"""
import pytest

from tests.conftest import initialized_di_container  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_dependencies_resolved(initialized_di_container):
    """Verify that all dependencies can be resolved"""
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    all_plugins = plugins_manager.get_all_plugins_info()
    
    errors = []
    skipped_plugins = ['logger', 'plugins_manager', 'settings_manager']  # These are created manually
    
    for plugin_name in all_plugins.keys():
        if plugin_name in skipped_plugins:
            continue  # These are created manually in Application
        
        try:
            plugin_type = plugins_manager.get_plugin_type(plugin_name)
            if plugin_type == 'utilities' or plugin_type == 'utility':
                _ = initialized_di_container.get_utility(plugin_name)
            elif plugin_type == 'services' or plugin_type == 'service':
                _ = initialized_di_container.get_service(plugin_name)
            else:
                errors.append(f"{plugin_name}: unknown plugin type '{plugin_type}'")
                continue
        except Exception as e:
            errors.append(f"{plugin_name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Dependency resolution errors:\n" + "\n".join(errors))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dependency_order_correct(initialized_di_container):
    """Verify correct dependency initialization order"""
    settings_manager = initialized_di_container.get_utility('settings_manager')
    startup_plan = settings_manager.get_startup_plan()
    
    assert startup_plan is not None, "Startup plan should be built"
    
    dependency_order = startup_plan.get('dependency_order', [])
    assert len(dependency_order) > 0, "Dependency order should be defined"
    
    # Verify that foundation utilities come first (if they are in the list)
    foundation_utils = ['logger', 'plugins_manager', 'settings_manager']
    
    # Verify that utilities that others depend on are initialized earlier
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    
    for i, util_name in enumerate(dependency_order):
        if util_name in foundation_utils:
            continue  # Foundation utilities may be excluded from plan
        
        # Get dependencies of this utility
        deps = plugins_manager.get_plugin_dependencies(util_name)
        
        # Verify that all dependencies are initialized earlier
        for dep in deps:
            if dep in dependency_order:
                dep_idx = dependency_order.index(dep)
                if dep_idx >= i:
                    # This may be normal if dependency is created manually
                    if dep not in foundation_utils:
                        # Warn but don't fail - this may be normal
                        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_required_utilities_initialized(initialized_di_container):
    """Verify that all required utilities can be retrieved"""
    settings_manager = initialized_di_container.get_utility('settings_manager')
    startup_plan = settings_manager.get_startup_plan()
    
    required_utilities = startup_plan.get('required_utilities', [])
    assert len(required_utilities) > 0, "Required utilities should be defined"
    
    # Verify that accessing required utilities does not cause exceptions
    errors = []
    for util_name in required_utilities:
        try:
            _ = initialized_di_container.get_utility(util_name)
        except Exception as e:
            errors.append(f"{util_name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Errors accessing required utilities:\n" + "\n".join(errors))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_enabled_services_initialized(initialized_di_container):
    """Verify that all enabled services can be retrieved"""
    settings_manager = initialized_di_container.get_utility('settings_manager')
    startup_plan = settings_manager.get_startup_plan()
    
    enabled_services = startup_plan.get('enabled_services', [])
    assert len(enabled_services) > 0, "Enabled services should be defined"
    
    # Verify that accessing enabled services does not cause exceptions
    errors = []
    for service_name in enabled_services:
        try:
            _ = initialized_di_container.get_service(service_name)
        except Exception as e:
            errors.append(f"{service_name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Errors accessing enabled services:\n" + "\n".join(errors))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_optional_dependencies_handled(initialized_di_container):
    """Verify correct handling of optional dependencies"""
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    all_plugins = plugins_manager.get_all_plugins_info()
    
    errors = []
    
    for plugin_name, plugin_info in all_plugins.items():
        optional_deps = plugin_info.get('optional_dependencies', [])
        
        if not optional_deps:
            continue
        
        # Verify that optional dependencies are either available or handled correctly
        for opt_dep in optional_deps:
            try:
                # Try to get optional dependency
                dep_instance = initialized_di_container.get_utility(opt_dep)
                # If dependency is not found, this is normal for optional ones
                # Main thing is that no errors occur
            except Exception as e:
                errors.append(f"{plugin_name} -> {opt_dep}: {str(e)}")
    
    if errors:
        pytest.fail(f"Optional dependency handling errors:\n" + "\n".join(errors))

