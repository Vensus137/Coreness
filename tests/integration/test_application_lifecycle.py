"""
Integration tests for application lifecycle
Verify correct application initialization and shutdown
"""
import pytest

from tests.conftest import initialized_di_container, di_container  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_application_startup(initialized_di_container):
    """Verify correct application initialization"""
    # Verify that all utilities are initialized
    # Foundation utilities are available through get_utility(), but may not be in get_all_utilities()
    utilities = initialized_di_container.get_all_utilities()
    
    # Verify presence of critical foundation utilities through get_utility()
    logger = initialized_di_container.get_utility('logger')
    assert logger is not None, "Logger should be initialized"
    
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    assert plugins_manager is not None, "PluginsManager should be initialized"
    
    settings_manager = initialized_di_container.get_utility('settings_manager')
    assert settings_manager is not None, "SettingsManager should be initialized"
    
    # Verify that there are other utilities (not just foundation)
    # Foundation utilities may not appear in get_all_utilities(), but others should be
    if len(utilities) == 0:
        # If there are no utilities in the list, verify that at least one non-foundation utility is available
        test_utilities = ['action_hub', 'database_manager', 'cache_manager']
        found_utility = False
        for util_name in test_utilities:
            util = initialized_di_container.get_utility(util_name)
            if util is not None:
                found_utility = True
                break
        assert found_utility, "At least one non-foundation utility should be available"
    
    # Verify that all services can be retrieved
    services = initialized_di_container.get_all_services()
    assert len(services) > 0, "Services should be initialized"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_di_container_shutdown(di_container):
    """Verify correct DI container shutdown"""
    # Initialize container for test
    di_container.initialize_all_plugins()
    
    # Verify that container is initialized before shutdown
    # Foundation utilities are always available, verify them
    logger = di_container.get_utility('logger')
    assert logger is not None, "Logger should be available before shutdown"
    
    # Verify that shutdown does not cause errors
    # Note: shutdown clears the container, so we only verify absence of exceptions
    try:
        di_container.shutdown()
    except Exception as e:
        pytest.fail(f"Shutdown raised exception: {e}")
    
    # Verify that shutdown does not cause errors on repeated call
    try:
        di_container.shutdown()  # Should be safe
    except Exception as e:
        pytest.fail(f"Repeated shutdown raised exception: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_foundation_utilities_available(initialized_di_container):
    """Verify foundation utilities availability"""
    # Foundation utilities are available through get_utility until shutdown
    foundation_utils = ['logger', 'plugins_manager', 'settings_manager']
    
    for util_name in foundation_utils:
        util_instance = initialized_di_container.get_utility(util_name)
        assert util_instance is not None, f"Foundation utility {util_name} should be available"
        
        # Verify that this is indeed a utility instance
        assert hasattr(util_instance, '__class__'), f"{util_name} should be an object"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_services_can_be_retrieved(initialized_di_container):
    """Verify that all services can be retrieved from DI container"""
    # Get list of enabled services from startup plan
    settings_manager = initialized_di_container.get_utility('settings_manager')
    assert settings_manager is not None, "SettingsManager should be available"
    
    startup_plan = settings_manager.get_startup_plan()
    assert startup_plan is not None, "Startup plan should be built"
    
    enabled_services = startup_plan.get('enabled_services', [])
    assert len(enabled_services) > 0, "At least one enabled service should exist"
    
    # Verify that each service can be retrieved by name
    for service_name in enabled_services:
        service_instance = initialized_di_container.get_service(service_name)
        assert service_instance is not None, f"Service {service_name} should be available"

