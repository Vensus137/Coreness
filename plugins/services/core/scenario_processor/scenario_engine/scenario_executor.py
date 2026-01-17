"""
Исполнитель сценариев
Выполняет сценарии, координирует выполнение шагов и обработку переходов
"""

from typing import Any, Callable, Dict, Optional, Tuple


class ScenarioExecutor:
    """
    Исполнитель сценариев
    - Выполнение сценариев по ID и по имени
    - Координация выполнения шагов
    - Обработка переходов между шагами
    """
    
    def __init__(self, logger, step_executor, transition_handler, cache_manager):
        self.logger = logger
        self.step_executor = step_executor
        self.transition_handler = transition_handler
        self.cache_manager = cache_manager
    
    async def execute_scenario(self, tenant_id: int, scenario_id: int, event: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Выполнение сценария по ID для конкретного tenant'а. Возвращает кортеж (result, cache)"""
        try:
            # Используем метаданные сценариев для изоляции обработки
            scenario_data = scenario_metadata['scenario_index'].get(scenario_id)
            if not scenario_data:
                self.logger.warning(f"Сценарий {scenario_id} не найден в справочнике для tenant {tenant_id}")
                return ('error', None)
            
            # Получаем шаги сценария (tuple)
            step = scenario_data.get('step', ())
            if not step:
                self.logger.warning(f"Сценарий {scenario_id} не содержит шагов для tenant {tenant_id}")
                return ('error', None)
            
            # Сортируем шаги по порядку (sorted работает с tuple, возвращает list)
            sorted_step = sorted(step, key=lambda x: x.get('step_order', 0))
            
            scenario_name = scenario_data.get('data', {}).get('name', f'Сценарий {scenario_id}')
            
            # Создаем копию события для накопления данных между шагами
            data = event.copy()
            data['tenant_id'] = tenant_id  # Добавляем tenant_id в данные
            data['_scenario_metadata'] = scenario_metadata  # Добавляем метаданные сценариев для использования в execute_scenario action
            
            # Инициализируем цепочку сценариев для отладки
            # Если цепочка уже есть (при прыжке из другого сценария), используем её, иначе создаем новую
            if 'scenario_chain' not in data or not isinstance(data.get('scenario_chain'), list):
                data['scenario_chain'] = [scenario_name]
            else:
                # Добавляем текущий сценарий в цепочку (копируем массив, чтобы не изменять оригинал)
                data['scenario_chain'] = data['scenario_chain'].copy()
                data['scenario_chain'].append(scenario_name)
            
            # Выполняем каждый шаг
            # Используем while вместо for, чтобы поддерживать отрицательные значения move_steps для возврата назад
            i = 0
            while i < len(sorted_step):
                step_data = sorted_step[i]
                params = step_data.get('params', {})
                
                # Выполняем шаг
                step_result = await self.step_executor.execute_step(step_data, data)
                transition = step_data.get('transition', [])
                
                # Мержим response_data в _cache
                response_data = step_result.get('response_data', {})
                if response_data:
                    self.cache_manager.merge_response_data(
                        response_data=response_data,
                        data=data,
                        action_name=step_data.get('action_name'),
                        params=params
                    )
                
                # Добавляем ошибку из действия в атрибут last_error (только если она не None)
                error = step_result.get('error')
                if error is not None:
                    data['last_error'] = error
                
                # Добавляем результат выполнения действия в атрибут last_result (для отладки)
                result = step_result.get('result')
                if result is not None:
                    data['last_result'] = result
                
                # Проверяем response_data на abort/stop из execute_scenario
                scenario_result = response_data.get('scenario_result')
                if scenario_result == 'abort':
                    # abort - прерываем всю цепочку выполнения текущего сценария
                    cache = self.cache_manager.extract_cache(data)
                    return ('abort', cache)
                elif scenario_result == 'stop':
                    # stop - прерываем всю обработку события
                    cache = self.cache_manager.extract_cache(data)
                    return ('stop', cache)
                
                # Обрабатываем переходы по результату шага
                transition_result = await self.transition_handler.process_transitions(
                    step_result.get('result'),
                    transition
                )
                transition_action = transition_result.get('action', 'continue')
                transition_value = transition_result.get('value')
                
                # Обрабатываем переходы
                if transition_action == 'stop':
                    result, cache = await self.transition_handler.handle_stop_abort_break('stop', data)
                    return (result, cache)
                    
                elif transition_action == 'abort':
                    result, cache = await self.transition_handler.handle_stop_abort_break('abort', data)
                    return (result, cache)
                    
                elif transition_action == 'break':
                    result, cache = await self.transition_handler.handle_stop_abort_break('break', data)
                    return (result, cache)
                    
                elif transition_action == 'jump_to_scenario':
                    result, cache = await self.transition_handler.handle_jump_to_scenario(
                        transition_value=transition_value,
                        tenant_id=tenant_id,
                        data=data,
                        scenario_metadata=scenario_metadata,
                        execute_scenario_by_name_func=execute_scenario_by_name_func
                    )
                    
                    if result == 'continue':
                        # Продолжаем выполнение следующего шага
                        i += 1
                        continue
                    else:
                        # stop, abort или success - возвращаем результат
                        return (result, cache)
                    
                elif transition_action == 'move_steps':
                    result, new_index, cache = await self.transition_handler.handle_move_steps(
                        transition_value=transition_value,
                        current_index=i,
                        sorted_step=sorted_step,
                        data=data
                    )
                    
                    if result == 'continue':
                        # Продолжаем с новым индексом
                        i = new_index
                        continue
                    else:
                        # success - завершаем сценарий
                        return ('success', cache)
                    
                elif transition_action == 'jump_to_step':
                    result, new_index, cache = await self.transition_handler.handle_jump_to_step(
                        transition_value=transition_value,
                        sorted_step=sorted_step,
                        data=data
                    )
                    
                    if result == 'continue':
                        # Продолжаем с новым индексом
                        i = new_index
                        continue
                    else:
                        # success - завершаем сценарий
                        return ('success', cache)
                
                # Продолжаем выполнение следующего шага (continue)
                i += 1
            
            # Возвращаем только _cache из финальных данных
            cache = self.cache_manager.extract_cache(data)
            return ('success', cache)
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения сценария {scenario_id} для tenant {tenant_id}: {e}")
            # Пытаемся сохранить частично накопленный кэш, если он есть
            try:
                cache = self.cache_manager.extract_cache(data)
            except (NameError, UnboundLocalError):
                cache = None
            return ('error', cache)
    
    async def execute_scenario_by_name(self, tenant_id: int, scenario_name: str, data: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_func: Callable) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Поиск и выполнение сценария по названию для конкретного tenant'а. Возвращает кортеж (result, cache)"""
        try:
            # Используем метаданные сценариев для изоляции обработки
            if scenario_metadata is None:
                return ('error', None)
            
            scenario_name_index = scenario_metadata['scenario_name_index']
            
            # Быстрый поиск O(1) через индекс
            if scenario_name not in scenario_name_index:
                self.logger.warning(f"Сценарий '{scenario_name}' не найден для tenant {tenant_id}")
                return ('error', None)
            
            target_scenario_id = scenario_name_index[scenario_name]
            
            # Создаем копию data для передачи в сценарий (чтобы не изменять оригинал)
            # Цепочка сценариев будет обновлена в execute_scenario
            data = data.copy()
            
            result, cache = await execute_scenario_func(
                tenant_id=tenant_id,
                scenario_id=target_scenario_id,
                event=data,
                scenario_metadata=scenario_metadata
            )
            
            # Возвращаем результат и только _cache
            return (result, cache)
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения сценария '{scenario_name}' для tenant {tenant_id}: {e}")
            return ('error', None)

