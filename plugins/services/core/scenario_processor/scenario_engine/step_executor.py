"""
Исполнитель шагов сценария
Выполняет шаги сценария, обрабатывает плейсхолдеры и async действия
"""

import asyncio
from typing import Any, Dict


class StepExecutor:
    """
    Исполнитель шагов сценария
    - Выполнение шагов с обработкой плейсхолдеров
    - Обработка синхронных и асинхронных действий
    """
    
    def __init__(self, logger, action_hub, placeholder_processor):
        self.logger = logger
        self.action_hub = action_hub
        self.placeholder_processor = placeholder_processor
    
    async def execute_step(self, step: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение шага сценария с обработкой плейсхолдеров"""
        try:
            # Валидация шага
            if not step or not isinstance(step, dict):
                self.logger.warning("Получен некорректный шаг")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Некорректный шаг'
                    }
                }
            
            action_name = step.get('action_name')
            if not action_name:
                self.logger.warning("Шаг не содержит action_name")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Отсутствует action_name'
                    }
                }
            
            params = step.get('params', {})
            
            # Проверяем флаг async
            is_async = step.get('async', False)
            action_id = step.get('action_id')  # Уникальный ID для отслеживания async действий
            
            # Обрабатываем плейсхолдеры в параметрах шага
            processed_params = self.placeholder_processor.process_placeholders_full(
                data_with_placeholders=params,
                values_dict=data  # Используем накопленные данные как источник значений
            )
            
            # Объединяем накопленные данные с обработанными параметрами шага
            action_data = {**data, **processed_params}
            
            # Защищаем системные атрибуты от перезаписи (защита от инъекций)
            if 'system' in data:
                action_data['system'] = data['system']  # Восстанавливаем оригинальные системные данные
            
            # Если async - запускаем асинхронно и сохраняем Future
            if is_async:
                if not action_id:
                    self.logger.warning("Async действие требует action_id")
                    return {
                        'result': 'error',
                        'error': {
                            'code': 'VALIDATION_ERROR',
                            'message': 'Отсутствует action_id для async действия'
                        }
                    }
                
                return await self.execute_action_async(action_name, action_data, action_id)
            else:
                # Обычное синхронное выполнение
                return await self.execute_action(action_name, action_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения шага {step.get('step_id', 'unknown')}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }
    
    async def execute_action(self, action_name: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение конкретного действия через ActionHub с безопасным выполнением"""
        try:
            result = await self.action_hub.execute_action_secure(action_name, data=action_data)
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения действия {action_name}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }
    
    async def execute_action_async(self, action_name: str, action_data: Dict[str, Any], action_id: str) -> Dict[str, Any]:
        """Запуск действия асинхронно с возвратом Future для отслеживания"""
        try:
            # Инициализируем хранилище async действий если его нет
            # Используем action_data для получения текущего состояния (может быть уже инициализировано)
            current_async_action = action_data.get('_async_action', {})
            
            # Запускаем действие через ActionHub с return_future=True
            future = await self.action_hub.execute_action_secure(
                action_name=action_name,
                data=action_data,
                fire_and_forget=True,  # Не ждем выполнения
                return_future=True     # Но получаем Future для отслеживания
            )
            
            # Проверяем что получили Future
            if not isinstance(future, asyncio.Future):
                self.logger.error(f"Ожидался Future для async действия {action_name}, получен {type(future)}")
                return {
                    'result': 'error',
                    'error': {
                        'code': 'INTERNAL_ERROR',
                        'message': 'Не удалось получить Future для async действия'
                    }
                }
            
            # Сохраняем Future в хранилище (копируем текущее состояние и добавляем новый)
            current_async_action[action_id] = future
            
            # Возвращаем успех без ожидания результата
            # ВАЖНО: Добавляем _async_action в response_data, чтобы он попал в _cache
            # Не добавляем action_id и status - они могут перезаписать данные пользователя
            return {
                'result': 'success',
                'response_data': {
                    '_async_action': current_async_action  # Сохраняем Future в response_data для добавления в _cache
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска async действия {action_name}: {e}")
            return {
                'result': 'error',
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': f'Внутренняя ошибка: {str(e)}'
                }
            }

