"""
Обработчик переходов между шагами сценария
Обрабатывает все типы переходов: stop, abort, break, jump_to_scenario, move_steps, jump_to_step
"""

from typing import Any, Dict, List, Optional, Tuple


class TransitionHandler:
    """
    Обработчик переходов между шагами сценария
    - Парсинг переходов по результату действия
    - Обработка всех типов переходов
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def process_transitions(self, action_result: str, transition: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Обработка переходов по результату действия. Возвращает словарь с ключами action и value"""
        try:
            # Сначала ищем переход "any" - он обрабатывается первым
            any_transition = None
            matching_transition = None
            
            for transition_data in transition:
                if transition_data.get('action_result') == 'any':
                    any_transition = transition_data
                elif transition_data.get('action_result') == action_result:
                    matching_transition = transition_data
            
            # Используем переход "any" если он есть, иначе ищем по результату действия
            final_transition = any_transition if any_transition else matching_transition
            
            if not final_transition:
                return {'action': 'continue', 'value': None}
            
            transition_action = final_transition.get('transition_action', 'continue')
            transition_value = final_transition.get('transition_value')
            
            # Выполняем переход
            if transition_action == 'continue':
                # Продолжаем выполнение следующего шага
                return {'action': 'continue', 'value': None}
                
            elif transition_action == 'stop':
                # Прерываем всю обработку события (все сценарии)
                return {'action': 'stop', 'value': None}
                
            elif transition_action == 'break':
                # Прерываем выполнение только текущего сценария
                return {'action': 'break', 'value': None}
                
            elif transition_action == 'abort':
                # Прерываем всю цепочку выполнения текущего сценария (включая вложенные)
                return {'action': 'abort', 'value': None}
                
            elif transition_action == 'jump_to_scenario':
                # Переходим к другому сценарию
                if not transition_value:
                    return {'action': 'continue', 'value': None}
                
                return {'action': 'jump_to_scenario', 'value': transition_value}
                
            elif transition_action == 'move_steps':
                # Перемещаемся на указанное количество шагов
                return {'action': 'move_steps', 'value': transition_value}
            
            elif transition_action == 'jump_to_step':
                # Переход к конкретному шагу по индексу
                return {'action': 'jump_to_step', 'value': transition_value}
                
            else:
                return {'action': 'continue', 'value': None}
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки переходов: {e}")
            return {'action': 'continue', 'value': None}
    
    async def handle_stop_abort_break(self, transition_action: str, data: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Обработка переходов stop, abort, break. Возвращает кортеж (result, cache)"""
        cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
        return (transition_action, cache)
    
    async def handle_jump_to_scenario(self, transition_value: Any, tenant_id: int, data: Dict[str, Any], scenario_metadata: Dict[str, Any], execute_scenario_by_name_func) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Обработка перехода jump_to_scenario. Возвращает кортеж (result, cache)"""
        if not transition_value:
            # transition_value пустое или None - продолжаем выполнение
            return ('continue', None)
        
        if isinstance(transition_value, str):
            # Один сценарий
            jump_data = data.copy()
            jump_result, jump_cache = await execute_scenario_by_name_func(
                tenant_id=tenant_id,
                scenario_name=transition_value,
                data=jump_data,
                scenario_metadata=scenario_metadata
            )
            
            # Если переходный сценарий вернул stop или abort - передаем его дальше
            if jump_result in ['stop', 'abort']:
                cache = jump_cache if jump_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
                return (jump_result, cache)
            
            # Текущий сценарий завершен успешно - возвращаем кэш из прыжка или из data
            cache = jump_cache if jump_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
            return ('success', cache)
            
        elif isinstance(transition_value, list):
            # Массив сценариев - выполняем последовательно
            last_cache = None
            jump_data = data.copy()
            
            for scenario_name in transition_value:
                jump_result, jump_cache = await execute_scenario_by_name_func(
                    tenant_id=tenant_id,
                    scenario_name=scenario_name,
                    data=jump_data,
                    scenario_metadata=scenario_metadata
                )
                
                # Сохраняем последний кэш
                if jump_cache:
                    last_cache = jump_cache
                
                # Если любой из переходных сценариев вернул stop или abort - прерываем всю цепочку
                if jump_result in ['stop', 'abort']:
                    cache = last_cache if last_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
                    return (jump_result, cache)
            
            # Все сценарии завершены успешно - возвращаем последний кэш или из data
            cache = last_cache if last_cache else (data.get('_cache') if isinstance(data.get('_cache'), dict) else None)
            return ('success', cache)
        else:
            # Некорректный тип transition_value - логируем и продолжаем выполнение
            self.logger.warning(f"Некорректный тип transition_value для jump_to_scenario: {type(transition_value)}, ожидается str или list")
            return ('continue', None)
    
    async def handle_move_steps(self, transition_value: Any, current_index: int, sorted_step: List[Dict[str, Any]], data: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
        """Обработка перехода move_steps. Возвращает кортеж (result, new_index, cache)"""
        # Перемещаемся на указанное количество шагов (положительное = вперед, отрицательное = назад)
        # Логика: переместиться на N шагов означает перейти к шагу i + N
        # move_steps: 1 = перейти на 1 шаг вперед (к следующему шагу)
        # move_steps: 2 = перейти на 2 шага вперед (пропустить 1 шаг)
        # move_steps: -1 = перейти на 1 шаг назад
        step_count = transition_value or 1
        try:
            step_count = int(step_count)
        except (ValueError, TypeError):
            step_count = 1
        
        # Формула: i + step_count (просто перемещаемся на N шагов)
        new_index = current_index + step_count
        
        # Проверяем границы: индекс должен быть в диапазоне [0, len(sorted_step))
        if 0 <= new_index < len(sorted_step):
            return ('continue', new_index, None)
        elif new_index < 0:
            # Если индекс стал отрицательным - начинаем с начала
            return ('continue', 0, None)
        else:
            # Если индекс выходит за границы вперед - завершаем сценарий
            cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
            return ('success', None, cache)
    
    async def handle_jump_to_step(self, transition_value: Any, sorted_step: List[Dict[str, Any]], data: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[Dict[str, Any]]]:
        """Обработка перехода jump_to_step. Возвращает кортеж (result, new_index, cache)"""
        # Переход к конкретному шагу по индексу (шаги нумеруются с 0)
        step_index = transition_value
        try:
            step_index = int(step_index)
        except (ValueError, TypeError):
            # Если индекс некорректен - продолжаем выполнение
            return ('continue', None, None)
        
        # Проверяем границы: индекс должен быть в диапазоне [0, len(sorted_step))
        if 0 <= step_index < len(sorted_step):
            return ('continue', step_index, None)
        else:
            # Если индекс выходит за границы - завершаем сценарий
            cache = data.get('_cache') if isinstance(data.get('_cache'), dict) else None
            return ('success', None, cache)

