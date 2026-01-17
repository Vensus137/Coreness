"""
Core модуль для обработки событий по сценариям
Оркестратор - координирует работу всех компонентов для обработки событий по сценариям
"""

from typing import Any, Dict, Optional

from .cache_manager import CacheManager
from .scenario_cache import ScenarioCache
from .scenario_executor import ScenarioExecutor
from .scenario_finder import ScenarioFinder
from .scenario_loader import ScenarioLoader
from .step_executor import StepExecutor
from .transition_handler import TransitionHandler


class ScenarioEngine:
    """
    Движок обработки событий по сценариям для множественных tenant'ов
    Оркестратор - координирует работу всех компонентов:
    - ScenarioCache - кэширование сценариев
    - ScenarioLoader - загрузка сценариев из БД
    - ScenarioFinder - поиск сценариев по событиям
    - ScenarioExecutor - выполнение сценариев
    """
    
    def __init__(self, data_loader, logger, action_hub, condition_parser, placeholder_processor, cache_manager, settings_manager):
        self.logger = logger
        self.action_hub = action_hub
        self.condition_parser = condition_parser
        self.placeholder_processor = placeholder_processor
        self.data_loader = data_loader
        
        # Инициализируем компоненты
        self.cache = ScenarioCache(self.logger, cache_manager, settings_manager)
        self.loader = ScenarioLoader(self.logger, self.data_loader, self.condition_parser)
        self.finder = ScenarioFinder(self.logger, self.condition_parser)
        
        # Создаем компоненты для выполнения
        cache_manager = CacheManager(self.logger, self.action_hub)
        step_executor = StepExecutor(self.logger, self.action_hub, self.placeholder_processor)
        transition_handler = TransitionHandler(self.logger)
        
        self.executor = ScenarioExecutor(
            self.logger,
            step_executor,
            transition_handler,
            cache_manager
        )
    
    async def process_event(self, event: Dict[str, Any]) -> bool:
        """Обработка события по сценариям"""
        try:
            # Определяем tenant_id из события
            tenant_id = self.finder.extract_tenant_id(event)
            if not tenant_id:
                self.logger.warning("Не удалось определить tenant_id из события")
                return False
            
            # Загружаем сценарии tenant'а (если еще не загружены)
            if not await self.cache.has_tenant_cache(tenant_id):
                cache_data = await self.loader.load_tenant_scenarios(tenant_id)
                await self.cache.set_tenant_cache(tenant_id, cache_data)
            
            # Получаем метаданные сценариев для изоляции обработки события
            scenario_metadata = await self.cache.get_scenario_metadata(tenant_id)
            if not scenario_metadata:
                self.logger.warning(f"Не удалось получить метаданные сценариев для tenant {tenant_id}")
                return False
            
            # Ищем подходящие сценарии (используем метаданные)
            scenario_ids = await self.finder.find_scenarios_by_event(tenant_id, event, scenario_metadata)
            
            if scenario_ids:
                # Выполняем найденные сценарии (используем метаданные)
                for scenario_id in scenario_ids:
                    result, _ = await self.executor.execute_scenario(
                        tenant_id=tenant_id,
                        scenario_id=scenario_id,
                        event=event,
                        scenario_metadata=scenario_metadata,
                        execute_scenario_by_name_func=self._execute_scenario_by_name_wrapper
                    )
                    
                    # Проверяем результат выполнения сценария
                    if result == 'stop':
                        # stop - прерываем всю обработку события (все сценарии)
                        return True
                    elif result == 'abort':
                        # abort - прерываем всю цепочку выполнения текущего сценария (включая вложенные)
                        # но продолжаем с другими сценариями из других триггеров
                        continue
                    elif result == 'break':
                        # break - прерываем только текущий сценарий, продолжаем с другими
                        continue
                    elif result == 'error':
                        self.logger.warning(f"Ошибка выполнения сценария {scenario_id}")
                        continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки события: {e}")
            return False
    
    async def _execute_scenario_by_name_wrapper(self, tenant_id: int, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
        """Обертка для выполнения сценария по имени. Используется для передачи в ScenarioExecutor для jump_to_scenario переходов"""
        return await self.executor.execute_scenario_by_name(
            tenant_id=tenant_id,
            scenario_name=scenario_name,
            data=data,
            scenario_metadata=scenario_metadata,
            execute_scenario_func=self._execute_scenario_wrapper
        )
    
    async def _execute_scenario_wrapper(self, tenant_id: int, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any]) -> tuple[str, Optional[Dict[str, Any]]]:
        """Обертка для выполнения сценария по ID. Используется для передачи в ScenarioExecutor"""
        return await self.executor.execute_scenario(
            tenant_id=tenant_id,
            scenario_id=scenario_id,
            event=event,
            scenario_metadata=scenario_metadata,
            execute_scenario_by_name_func=self._execute_scenario_by_name_wrapper
        )
    
    async def _execute_scenario_by_name(self, tenant_id: int, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any] = None) -> tuple[str, Optional[Dict[str, Any]]]:
        """Поиск и выполнение сценария по названию для конкретного tenant'а. Публичный метод для использования извне"""
        if scenario_metadata is None:
            # Если метаданные не переданы, получаем их
            scenario_metadata = await self.cache.get_scenario_metadata(tenant_id)
            if not scenario_metadata:
                self.logger.warning(f"Не удалось получить метаданные сценариев для tenant {tenant_id}")
                return ('error', None)
        
        return await self.executor.execute_scenario_by_name(
            tenant_id=tenant_id,
            scenario_name=scenario_name,
            data=data,
            scenario_metadata=scenario_metadata,
            execute_scenario_func=self._execute_scenario_wrapper
        )
    
    async def reload_tenant_scenarios(self, tenant_id: int) -> bool:
        """Перезагрузка кэша сценариев для конкретного tenant'а"""
        try:
            # Очищаем кэш
            if not await self.cache.reload_tenant_scenarios(tenant_id):
                return False
            
            # Загружаем заново
            cache_data = await self.loader.load_tenant_scenarios(tenant_id)
            await self.cache.set_tenant_cache(tenant_id, cache_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка перезагрузки сценариев для tenant {tenant_id}: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Очистка ресурсов"""
        try:
            await self.cache.cleanup()
        except Exception as e:
            self.logger.error(f"Ошибка очистки: {e}")
