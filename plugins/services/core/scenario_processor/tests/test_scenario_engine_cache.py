"""
Тесты функциональности ScenarioEngine с проверкой кэширования сценариев
"""
from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
class TestScenarioEngineCache:
    """Тесты кэширования сценариев в ScenarioEngine"""
    
    async def test_process_event_loads_scenarios_on_first_request(self, scenario_engine, mock_data_loader):
        """Проверка: при первом запросе сценарии загружаются из БД и кэшируются"""
        # Подготавливаем данные
        tenant_id = 1
        mock_scenarios = [
            {
                'id': 1,
                'scenario_name': 'test_scenario',
                'tenant_id': tenant_id
            }
        ]
        
        # Настраиваем мок data_loader для возврата сценариев
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios)
        
        # Создаем событие с правильной структурой
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # Первый запрос - должен вызвать load_scenarios_by_tenant
        await scenario_engine.process_event(event)
        
        # Проверяем, что data_loader был вызван
        mock_data_loader.load_scenarios_by_tenant.assert_called_once_with(tenant_id)
        
        # Проверяем, что кэш заполнен
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is True
    
    async def test_process_event_uses_cache_on_second_request(self, scenario_engine, mock_data_loader):
        """Проверка: при повторном запросе сценарии берутся из кэша (не из БД)"""
        # Подготавливаем данные
        tenant_id = 1
        mock_scenarios = [
            {
                'id': 1,
                'scenario_name': 'test_scenario',
                'tenant_id': tenant_id
            }
        ]
        
        # Настраиваем мок data_loader
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios)
        
        # Создаем событие с правильной структурой
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # Первый запрос - загружает из БД
        await scenario_engine.process_event(event)
        
        # Сбрасываем счетчик вызовов
        mock_data_loader.load_scenarios_by_tenant.reset_mock()
        
        # Второй запрос - должен использовать кэш
        await scenario_engine.process_event(event)
        
        # Проверяем, что data_loader НЕ был вызван повторно
        mock_data_loader.load_scenarios_by_tenant.assert_not_called()
    
    async def test_process_event_metadata_correct(self, scenario_engine, mock_data_loader):
        """Проверка: метаданные сценариев корректны для поиска"""
        # Подготавливаем данные
        tenant_id = 1
        mock_scenarios = [
            {
                'id': 1,
                'scenario_name': 'test_scenario',
                'tenant_id': tenant_id
            }
        ]
        
        # Настраиваем мок data_loader
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios)
        
        # Создаем событие с правильной структурой
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # Обрабатываем событие
        await scenario_engine.process_event(event)
        
        # Получаем метаданные
        metadata = await scenario_engine.cache.get_scenario_metadata(tenant_id)
        
        # Проверяем структуру метаданных
        assert metadata is not None
        assert 'search_tree' in metadata
        assert 'scenario_index' in metadata
        assert 'scenario_name_index' in metadata
    
    async def test_reload_tenant_scenarios_reloads_from_db(self, scenario_engine, mock_data_loader):
        """Проверка: reload_tenant_scenarios перезагружает сценарии из БД"""
        # Подготавливаем данные
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
        
        # Настраиваем мок data_loader для первого запроса
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios_1)
        
        # Создаем событие с правильной структурой
        event = {
            'system': {
                'tenant_id': tenant_id
            },
            'event_type': 'message'
        }
        
        # Первый запрос - загружает из БД
        await scenario_engine.process_event(event)
        
        # Проверяем, что кэш заполнен
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is True
        
        # Инвалидируем кэш
        await scenario_engine.cache.reload_tenant_scenarios(tenant_id)
        
        # Проверяем, что кэш очищен
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is False
        
        # Настраиваем мок для второго запроса (другие данные)
        mock_data_loader.load_scenarios_by_tenant = AsyncMock(return_value=mock_scenarios_2)
        
        # Второй запрос - должен загрузить новые данные из БД
        await scenario_engine.process_event(event)
        
        # Проверяем, что data_loader был вызван снова
        assert mock_data_loader.load_scenarios_by_tenant.call_count == 1
        
        # Проверяем, что кэш заполнен новыми данными
        assert await scenario_engine.cache.has_tenant_cache(tenant_id) is True

