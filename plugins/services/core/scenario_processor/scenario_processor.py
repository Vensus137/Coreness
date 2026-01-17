"""
Scenario Processor - сервис для обработки событий по сценариям
"""

import asyncio
from typing import Any, Dict, Optional

from .core.scheduled_scenario_manager import ScheduledScenarioManager
from .scenario_engine.scenario_engine import ScenarioEngine
from .utils.data_loader import DataLoader
from .utils.scheduler import ScenarioScheduler


class ScenarioProcessor:
    """
    Сервис для обработки событий по сценариям
    - Получает обработанные события от event_processor
    - Определяет tenant_id и загружает сценарии
    - Выполняет действия через ActionHub
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        # Создаем DataLoader для передачи в ScenarioEngine
        self.data_loader = DataLoader(
            logger=self.logger,
            database_manager=self.database_manager
        )
        
        # Создаем движок обработки сценариев
        self.scenario_engine = ScenarioEngine(
            data_loader=self.data_loader,
            logger=self.logger,
            action_hub=self.action_hub,
            condition_parser=kwargs['condition_parser'],
            placeholder_processor=kwargs['placeholder_processor'],
            cache_manager=kwargs['cache_manager'],
            settings_manager=self.settings_manager
        )
        
        # Создаем scheduler для работы с cron (используется для валидации и в менеджере)
        self.scheduler = ScenarioScheduler(
            logger=self.logger,
            datetime_formatter=self.datetime_formatter
        )
        
        # Создаем менеджер scheduled сценариев
        self.scheduled_manager = ScheduledScenarioManager(
            scenario_engine=self.scenario_engine,
            data_loader=self.data_loader,
            scheduler=self.scheduler,
            logger=self.logger,
            datetime_formatter=self.datetime_formatter,
            database_manager=self.database_manager,
            task_manager=kwargs['task_manager'],
            cache_manager=kwargs['cache_manager']
        )
        
        # Регистрируем себя в ActionHub
        self.action_hub.register('scenario_processor', self)
        
        # Состояние сервиса
        self.is_running = False
        self._run_task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Основной цикл работы сервиса"""
        try:
            self.is_running = True
            
            # Запускаем менеджер scheduled сценариев
            await self.scheduled_manager.run()
            
        except asyncio.CancelledError:
            self.logger.info("ScenarioProcessor остановлен")
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле ScenarioProcessor: {e}")
        finally:
            self.is_running = False
    
    def shutdown(self):
        """Синхронный graceful shutdown сервиса"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Останавливаем менеджер scheduled сценариев
        self.scheduled_manager.shutdown()
    
    # === Actions для ActionHub ===
    
    async def process_scenario_event(self, data: dict) -> Dict[str, Any]:
        """
        Обработка события по сценариям
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Обрабатываем событие через scenario_engine
            success = await self.scenario_engine.process_event(data)
            
            if success:
                return {"result": "success"}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось обработать событие по сценариям"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка обработки события: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    
    async def sync_scenarios(self, data: dict) -> Dict[str, Any]:
        """
        Синхронизация сценариев тенанта: удаление старых → сохранение новых → перезагрузка кэша
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            scenarios = data.get('scenarios', [])
            
            # 1. Удаляем старые сценарии
            delete_success = await self.data_loader.delete_tenant_scenarios(tenant_id)
            if not delete_success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось удалить старые сценарии"
                    }
                }
            
            # 2. Сохраняем новые сценарии
            saved_scenarios = 0
            
            for scenario_data in scenarios:
                    # Валидация cron выражения если указан schedule
                    schedule = scenario_data.get('schedule')
                    if schedule:
                        if not self.scheduler.is_valid_cron(schedule):
                            self.logger.error(f"Невалидное cron выражение '{schedule}' для сценария {scenario_data.get('scenario_name')}")
                            continue
                    
                    scenario_id = await self.data_loader.save_scenario(tenant_id, scenario_data)
                    if scenario_id is None:
                        self.logger.error(f"Не удалось создать сценарий {scenario_data.get('scenario_name')}")
                        continue
                    
                    saved_scenarios += 1
                    
                    # Создаем триггеры сценария
                    trigger = scenario_data.get('trigger', [])
                    for trigger_data in trigger:
                        await self.data_loader.save_trigger(scenario_id, trigger_data)
                    
                    # Создаем шаги сценария
                    step = scenario_data.get('step', [])
                    for step_data in step:
                        await self.data_loader.save_step(scenario_id, step_data)
            
            # 3. Перезагружаем кэш обычных сценариев
            scenarios_reload_success = await self.scenario_engine.reload_tenant_scenarios(tenant_id)
            if not scenarios_reload_success:
                self.logger.warning(f"Не удалось перезагрузить кэш обычных сценариев для tenant {tenant_id}")
            
            # 4. Перезагружаем scheduled метаданные
            scheduled_reload_success = await self.scheduled_manager.reload_scheduled_metadata(tenant_id)
            if not scheduled_reload_success:
                self.logger.warning(f"Не удалось перезагрузить scheduled метаданные для tenant {tenant_id}")
            
            # Определяем результат в зависимости от успешности перезагрузок
            if scenarios_reload_success and scheduled_reload_success:
                # Обе перезагрузки успешны
                return {"result": "success"}
            elif scenarios_reload_success or scheduled_reload_success:
                # Только одна перезагрузка успешна - частичный успех
                failed_parts = []
                if not scenarios_reload_success:
                    failed_parts.append("обычные сценарии")
                if not scheduled_reload_success:
                    failed_parts.append("scheduled метаданные")
                
                return {
                    "result": "partial_success",
                    "error": {
                        "code": "PARTIAL_SUCCESS",
                        "message": f"Частичный успех: не удалось перезагрузить {', '.join(failed_parts)}"
                    }
                }
            else:
                # Обе перезагрузки не удались
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось перезагрузить кэш сценариев"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации сценариев: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def execute_scenario(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение сценария или массива сценариев по имени
        
        Примечание: _scenario_metadata добавляется в data в ScenarioExecutor.execute_scenario
        и передается через action_data в этот action для изоляции обработки события
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            scenario_param = data.get('scenario')
            
            # Получаем tenant_id (уже передан из контекста)
            tenant_id = data.get('tenant_id')
            
            # Получаем метаданные сценариев из контекста (добавляются в ScenarioExecutor.execute_scenario)
            # Используются для изоляции обработки: обновление структуры сценариев не влияет на уже запущенные сценарии
            scenario_metadata = data.get('_scenario_metadata')
            
            # Получаем параметр return_cache (по умолчанию true)
            return_cache = data.get('return_cache', True)
            if not isinstance(return_cache, bool):
                return_cache = True  # По умолчанию включаем возврат кэша
            
            if isinstance(scenario_param, str):
                # Один сценарий
                result, cache = await self.scenario_engine._execute_scenario_by_name(
                    tenant_id=tenant_id,
                    scenario_name=scenario_param,
                    data=data,
                    scenario_metadata=scenario_metadata
                )
                
                response_data = {
                    'scenario_result': result
                }
                
                # Если return_cache включен и есть кэш - возвращаем его в response_data
                # Кэш будет добавлен в _cache[action_name] автоматически в scenario_engine
                # Возвращаем кэш даже при ошибке, если он был частично накоплен
                if return_cache and cache:
                    # Мержим кэш из выполненного сценария в response_data
                    # cache - это весь _cache из выполненного сценария (словарь с ключами action_name)
                    # Это позволит использовать данные из выполненного сценария через _cache[action_name]
                    response_data.update(cache)
                    # Восстанавливаем scenario_result на случай, если он был перезаписан из cache
                    response_data['scenario_result'] = result
                
                return {
                    'result': 'success' if result != 'error' else 'error',
                    'response_data': response_data
                }
                
            elif isinstance(scenario_param, list):
                # Массив сценариев - выполняем последовательно
                # ВАЖНО: Для массива сценариев возврат кэша отключен, т.к. сложно определить логику объединения
                # и это может нарушить изоляцию сценариев
                last_result = 'success'
                
                # Получаем метаданные сценариев из контекста (добавляются в ScenarioExecutor.execute_scenario)
                scenario_metadata = data.get('_scenario_metadata')
                
                for scenario_name in scenario_param:
                    result, _ = await self.scenario_engine._execute_scenario_by_name(
                        tenant_id=tenant_id,
                        scenario_name=scenario_name,
                        data=data,
                        scenario_metadata=scenario_metadata
                    )
                    
                    # Если техническая ошибка - прерываем
                    if result == 'error':
                        return {'result': 'error'}
                    
                    # Если abort или stop - прерываем всю цепочку и передаем результат
                    if result in ['abort', 'stop']:
                        return {
                            'result': 'success',
                            'response_data': {
                                'scenario_result': result
                            }
                        }
                    
                    # Сохраняем результат (success, break)
                    last_result = result
                
                # Для массива сценариев кэш не возвращается (изоляция сохраняется)
                return {
                    'result': 'success',
                    'response_data': {
                        'scenario_result': last_result
                    }
                }
            
            else:
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'scenario должен быть строкой или массивом'
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения сценария: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }
    
    async def wait_for_action(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ожидание завершения асинхронного действия по action_id
        Возвращает результат основного действия AS IS (как будто оно выполнилось напрямую)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            action_id = data.get('action_id')
            timeout = data.get('timeout')  # Опциональный таймаут в секундах
            
            # Получаем контекст сценария из data
            async_action = data.get('_async_action', {})
            
            if action_id not in async_action:
                return {
                    'result': 'error',
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': f'Async действие с action_id={action_id} не найдено'
                    }
                }
            
            future = async_action[action_id]
            
            # Проверяем что это Future
            if not isinstance(future, asyncio.Future):
                return {
                    'result': 'error',
                    'error': {
                        'code': 'INVALID_STATE',
                        'message': f'Некорректный тип Future для action_id={action_id}'
                    }
                }
            
            # Если действие уже завершено - сразу возвращаем результат AS IS
            if future.done():
                try:
                    result = future.result()
                    # Возвращаем результат основного действия AS IS (полностью копируем структуру)
                    # Результат попадет в data через merge response_data в scenario_engine
                    return result
                except Exception as e:
                    return {
                        'result': 'error',
                        'error': {
                            'code': 'INTERNAL_ERROR',
                            'message': str(e)
                        }
                    }
            
            # Ждем завершения с таймаутом или без
            try:
                if timeout:
                    result = await asyncio.wait_for(future, timeout=float(timeout))
                else:
                    result = await future
                
                # Возвращаем результат основного действия AS IS (полностью копируем структуру)
                # Результат попадет в data через merge response_data в scenario_engine
                return result
                
            except asyncio.TimeoutError:
                # Таймаут - это ошибка самого wait_for_action, возвращаем ошибку ожидания
                return {
                    'result': 'timeout',
                    'error': {
                        'code': 'TIMEOUT',
                        'message': f'Превышено время ожидания для action_id={action_id}'
                    }
                }
            except Exception as e:
                # Ошибка при ожидании - возвращаем ошибку wait_for_action
                return {
                    'result': 'error',
                    'error': {
                        'code': 'INTERNAL_ERROR',
                        'message': str(e)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка ожидания async действия: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }