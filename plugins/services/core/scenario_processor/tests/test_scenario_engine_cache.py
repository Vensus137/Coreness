"""
Tests for ScenarioEngine functionality with scenario caching verification
"""
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
class TestScenarioEngineCache:
    """Tests for scenario caching in ScenarioEngine"""
    
    async def test_process_event_loads_scenarios_on_first_request(self, scenario_engine, mock_data_loader):
        """Check: on first request scenarios are loaded from DB and cached"""
        # Prepare data
        tenant_id = 1
        mock_scenarios = [
            {
                'id': 1,
                'scenario_name': 'test_scenario',
                'tenant_id': tenant_id
            }
        ]
        
        # Configure mock data_loader to return scenarios
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios)
        
        # Create event with correct structure
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # First request - should call load_scenarios_by_tenant
        await scenario_engine.process_event(event)
        
        # Check that data_loader was called
        mock_data_loader.load_scenarios_by_tenant.assert_called_once_with(tenant_id)
        
        # Check that cache is filled
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is True
    
    async def test_process_event_uses_cache_on_second_request(self, scenario_engine, mock_data_loader):
        """Check: on second request scenarios are taken from cache (not from DB)"""
        # Prepare data
        tenant_id = 1
        mock_scenarios = [
            {
                'id': 1,
                'scenario_name': 'test_scenario',
                'tenant_id': tenant_id
            }
        ]
        
        # Configure mock data_loader
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios)
        
        # Create event with correct structure
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # First request - loads from DB
        await scenario_engine.process_event(event)
        
        # Reset call counter
        mock_data_loader.load_scenarios_by_tenant.reset_mock()
        
        # Second request - should use cache
        await scenario_engine.process_event(event)
        
        # Check that data_loader was NOT called again
        mock_data_loader.load_scenarios_by_tenant.assert_not_called()
    
    async def test_process_event_metadata_correct(self, scenario_engine, mock_data_loader):
        """Check: scenario metadata is correct for search"""
        # Prepare data
        tenant_id = 1
        mock_scenarios = [
            {
                'id': 1,
                'scenario_name': 'test_scenario',
                'tenant_id': tenant_id
            }
        ]
        
        # Configure mock data_loader
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios)
        
        # Create event with correct structure
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # Process event
        await scenario_engine.process_event(event)
        
        # Get metadata
        metadata = await scenario_engine.cache.get_scenario_metadata(tenant_id)
        
        # Check metadata structure
        assert metadata is not None
        assert 'search_tree' in metadata
        assert 'scenario_index' in metadata
        assert 'scenario_name_index' in metadata
    
    async def test_reload_tenant_scenarios_reloads_from_db(self, scenario_engine, mock_data_loader):
        """Check: reload_tenant_scenarios reloads scenarios from DB"""
        # Prepare data
        tenant_id = 1
        mock_scenarios_1 = [
            {
                'id': 1,
                'scenario_name': 'scenario_1',
                'tenant_id': tenant_id
            }
        ]
        mock_scenarios_2 = [
            {
                'id': 2,
                'scenario_name': 'scenario_2',
                'tenant_id': tenant_id
            }
        ]
        
        # Configure mock data_loader for first request
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios_1)
        
        # Create event with correct structure
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # First request - loads from DB
        await scenario_engine.process_event(event)
        
        # Check that cache is filled
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is True
        
        # Invalidate cache
        await scenario_engine.cache.reload_tenant_scenarios(tenant_id)
        
        # Check that cache is cleared
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is False
        
        # Configure mock for second request (different data)
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios_2)
        
        # Second request - should load new data from DB
        await scenario_engine.process_event(event)
        
        # Check that data_loader was called again
        assert mock_data_loader.load_scenarios_by_tenant.call_count == 1
        
        # Check that cache is filled with new data
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is True

