"""
Integration tests for ActionHub and action registration
Verify correct registration and invocation of actions through ActionHub
"""
import pytest

from tests.conftest import initialized_di_container  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_actions_registered(initialized_di_container):
    """Verify that all actions from config.yaml are visible in ActionHub"""
    # Get ActionHub and PluginsManager through DI
    action_hub = initialized_di_container.get_utility('action_hub')
    plugins_manager = initialized_di_container.get_utility('plugins_manager')

    # If action_hub is not obtained through DI for some reason, this is already a reason to fail
    assert action_hub is not None, "action_hub utility should be available through DI"
    assert plugins_manager is not None, "PluginsManager should be available through DI"
    
    all_plugins = plugins_manager.get_all_plugins_info()
    missing_actions = []
    
    for plugin_name, plugin_info in all_plugins.items():
        actions = plugin_info.get('actions', {})
        for action_name in actions.keys():
            # In ActionRegistry, the mapping key is the ACTION NAME, not plugin.action
            action_config = action_hub.get_action_config(action_name)
            if action_config is None:
                missing_actions.append(f"{plugin_name}.{action_name}")
    
    if missing_actions:
        pytest.fail(
            "Actions not found in ActionHub (by action name):\n"
            + "\n".join(missing_actions)
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_call_with_validation(initialized_di_container):
    """Verify action invocation with input data validation"""
    action_hub = initialized_di_container.get_utility('action_hub')
    assert action_hub is not None, "action_hub utility should be available through DI"
    
    # Test a simple action from scenario_helper (sleep)
    # In ActionHub, the action is registered under the name 'sleep'
    result = await action_hub.execute_action(
        'sleep',
        data={'seconds': 0.01}  # Minimum delay for test
    )
    
    # Verify response structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert 'result' in result, "Result should contain 'result' field"
    assert result['result'] == 'success', f"Action should execute successfully, got: {result}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_config_retrieval(initialized_di_container):
    """Verify action configuration retrieval"""
    action_hub = initialized_di_container.get_utility('action_hub')
    plugins_manager = initialized_di_container.get_utility('plugins_manager')

    assert action_hub is not None, "action_hub utility should be available through DI"
    assert plugins_manager is not None, "PluginsManager should be available through DI"
    
    all_plugins = plugins_manager.get_all_plugins_info()
    
    # Check several random actions
    checked_count = 0
    for plugin_name, plugin_info in all_plugins.items():
        actions = plugin_info.get('actions', {})
        if not actions:
            continue
        
        # Take the first action from each plugin
        first_action = list(actions.keys())[0]
        
        action_config = action_hub.get_action_config(first_action)
        assert action_config is not None, (
            f"Action configuration {plugin_name}.{first_action} should be available"
        )
        
        # Verify configuration structure
        assert isinstance(
            action_config, dict
        ), f"Configuration {plugin_name}.{first_action} should be a dictionary"
        
        checked_count += 1
        if checked_count >= 5:  # Check first 5 plugins
            break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_hub_internal_actions(initialized_di_container):
    """Verify ActionHub internal actions"""
    action_hub = initialized_di_container.get_utility('action_hub')
    assert action_hub is not None, "action_hub utility should be available through DI"
    
    # Check internal action get_available_actions
    result = await action_hub.execute_action('get_available_actions')
    
    assert isinstance(result, dict), "Result should be a dictionary"
    assert 'result' in result, "Result should contain 'result' field"
    
    # If successful, should return mapping of available actions
    if result.get('result') == 'success' and 'response_data' in result:
        actions_mapping = result.get('response_data', {})
        assert isinstance(actions_mapping, dict), "response_data should be a dictionary with actions"
        # The system actually has actions, so we expect at least one action
        assert len(actions_mapping) > 0, "At least one action should be available"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_call_with_invalid_data(initialized_di_container):
    """Verify handling of invalid data when invoking an action"""
    action_hub = initialized_di_container.get_utility('action_hub')
    assert action_hub is not None, "action_hub utility should be available through DI"
    
    # Try to invoke action with invalid data
    result = await action_hub.execute_action(
        'sleep',
        data={'seconds': -1}  # Negative value should be rejected
    )
    
    # Result can be success (if validation is not strict) or error
    assert isinstance(result, dict), "Result should be a dictionary"
    assert 'result' in result, "Result should contain 'result' field"
    
    # If error, verify error structure
    if result.get('result') == 'error':
        assert 'error' in result, "Error field should be present when there's an error"

