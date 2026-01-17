"""
Action Registry - реестр сервисов и маршрутизация действий
"""

import asyncio
from typing import Any, Dict, Optional, Union


class ActionRegistry:
    """
    Реестр сервисов и маршрутизация действий
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.task_manager = kwargs['task_manager']
        # Получаем валидаторы из параметров
        self.access_validator = kwargs['access_validator']
        self.action_validator = kwargs['action_validator']
        
        # Registry сервисов
        self._services: Dict[str, Any] = {}
        
        # Маппинг действий к сервисам с полной информацией
        self._action_mapping: Dict[str, Dict[str, Any]] = {}
        
        # Добавляем специальные действия ActionHub в маппинг вручную
        self._add_internal_actions()
    
    def _add_internal_actions(self):
        """Добавление специальных действий ActionHub в маппинг из конфигурации"""
        try:
            # Получаем информацию о плагине ActionHub через прокси-метод
            plugin_info = self.settings_manager.get_plugin_info('action_hub')
            
            if not plugin_info:
                self.logger.warning("Плагин ActionHub не найден")
                return
            
            # Извлекаем блок actions из конфигурации
            actions = plugin_info.get('actions', {})
            
            # Добавляем специальные действия в маппинг
            special_actions = ['get_available_actions']
            
            for action_name in special_actions:
                if action_name in actions:
                    action_config = actions[action_name]
                    
                    self._action_mapping[action_name] = {
                        'service': 'action_hub',
                        'description': action_config.get('description', ''),
                        'input': action_config.get('input', {}),
                        'output': action_config.get('output', {}),
                        'config': action_config
                    }
                    
            
            # Внутренние действия добавлены
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления внутренних действий: {e}")
    
    def register(self, service_name: str, service_instance: Any) -> bool:
        """Регистрация сервиса с автоматическим построением маппинга действий"""
        try:
            # Регистрируем сервис
            self._services[service_name] = service_instance
            
            # Строим маппинг действий для этого сервиса
            self._build_action_mapping_for_service(service_name)
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка регистрации сервиса '{service_name}': {e}")
            return False
    
    def unregister(self, service_name: str) -> bool:
        """Отмена регистрации сервиса с очисткой маппинга действий"""
        try:
            if service_name in self._services:
                # Удаляем сервис
                del self._services[service_name]
                
                # Очищаем маппинг действий этого сервиса
                self._remove_action_mapping_for_service(service_name)
                
                return True
            else:
                self.logger.warning(f"Сервис '{service_name}' не найден")
                return False
        except Exception as e:
            self.logger.error(f"Ошибка отмены регистрации сервиса '{service_name}': {e}")
            return False
    
    def _build_action_mapping_for_service(self, service_name: str):
        """Построение маппинга действий для сервиса из его конфигурации"""
        try:
            # Получаем полную конфигурацию сервиса через SettingsManager
            plugin_info = self.settings_manager.get_plugin_info(service_name)
            
            if not plugin_info:
                self.logger.warning(f"Конфигурация сервиса '{service_name}' не найдена")
                return
            
            # Извлекаем блок actions
            actions = plugin_info.get('actions', {})
            
            if not actions:
                self.logger.info(f"У сервиса '{service_name}' нет действий")
                return
            
            # Добавляем каждое действие в маппинг с полной информацией
            for action_name, action_config in actions.items():
                if action_name in self._action_mapping:
                    self.logger.warning(f"Действие '{action_name}' уже замаплено на '{self._action_mapping[action_name]['service']}', перезаписываем на '{service_name}'")
                
                # Сохраняем полную информацию о действии
                self._action_mapping[action_name] = {
                    'service': service_name,
                    'description': action_config.get('description', ''),
                    'input': action_config.get('input', {}),
                    'output': action_config.get('output', {}),
                    'config': action_config  # Полная конфигурация действия
                }
            
            # Маппинг построен
            
        except Exception as e:
            self.logger.error(f"Ошибка построения маппинга для сервиса '{service_name}': {e}")
    
    def _remove_action_mapping_for_service(self, service_name: str):
        """Удаление маппинга действий для сервиса"""
        try:
            # Находим все действия, замапленные на этот сервис
            actions_to_remove = [
                action_name for action_name, mapped_service in self._action_mapping.items()
                if mapped_service == service_name
            ]
            
            # Удаляем их из маппинга
            for action_name in actions_to_remove:
                del self._action_mapping[action_name]
            
                
        except Exception as e:
            self.logger.error(f"Ошибка удаления маппинга для сервиса '{service_name}': {e}")
    
    def route_action(self, action_name: str, params: Dict[str, Any]) -> str:
        """Определение, какой сервис должен обработать действие"""
        if action_name in self._action_mapping:
            service_name = self._action_mapping[action_name]['service']
            return service_name
        else:
            self.logger.warning(f"Действие '{action_name}' не найдено в маппинге")
            return 'unknown'
    
    def get_action_config(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение полной конфигурации действия
        
        Возвращает конфигурацию действия из маппинга или None если действие не найдено
        """
        if action_name in self._action_mapping:
            return self._action_mapping[action_name].get('config')
        return None
    
    def _validate_access(self, action_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация доступа на основе правил действия"""
        try:
            # Получаем конфигурацию действия
            action_info = self._action_mapping.get(action_name)
            if not action_info:
                return {"result": "success"}  # Нет конфигурации - пропускаем
            
            action_config = action_info.get('config', {})
            
            # Используем AccessValidator для проверки доступа
            return self.access_validator.validate_action_access(action_name, action_config, data)
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации доступа для действия '{action_name}': {e}")
            return {
                "result": "error",
                "error": f"Ошибка валидации доступа: {str(e)}"
            }
    
    async def execute_action(self, action_name: str, data: dict = None, queue_name: str = None, 
                            fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Выполнение действия на соответствующем сервисе через очереди
        """
        # Если data не передан, используем пустой словарь
        if data is None:
            data = {}
        
        # Отправляем в указанную очередь или common по умолчанию
        target_queue = queue_name if queue_name else "common"
        
        # submit_task возвращает Dict или Future в зависимости от параметров
        result = await self.task_manager.submit_task(
            task_id=f"action_{action_name}",
            coro=self._create_action_wrapper(action_name, data),
            queue_name=target_queue,
            fire_and_forget=fire_and_forget,
            return_future=return_future
        )
        
        return result
    
    async def _execute_action_direct(self, action_name: str, data: dict = None) -> Dict[str, Any]:
        """Внутренний метод выполнения действия (используется в wrapper для TaskManager)"""
        # Если data не передан, используем пустой словарь
        if data is None:
            data = {}
        
        # Специальные действия ActionHub (не требуют регистрации сервиса)
        if action_name == 'get_available_actions':
            result = self._get_available_actions()
            self._log_action_result(action_name, 'action_hub', result)
            return result
        
        # Обычные действия через зарегистрированные сервисы
        # Определяем сервис для действия
        service_name = self.route_action(action_name, data)
        
        if service_name == 'unknown':
            error_result = {"result": "error", "error": f"Действие '{action_name}' не найдено"}
            self._log_action_result(action_name, 'unknown', error_result)
            return error_result
        
        # Получаем сервис
        service = self._services.get(service_name)
        if not service:
            error_result = {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Сервис '{service_name}' не зарегистрирован"
                }
            }
            self._log_action_result(action_name, service_name, error_result)
            return error_result
        
        # Валидация входных данных (если валидатор доступен)
        validated_data = data
        if self.action_validator:
            validation_result = self.action_validator.validate_action_input(
                service_name, action_name, data
            )
            if validation_result.get("result") != "success":
                self._log_action_result(action_name, service_name, validation_result)
                return validation_result
            
            # Получаем валидированные данные с преобразованными типами
            validated_data = validation_result.get("validated_data", data)
        
        # Выполняем действие на сервисе
        try:
            # Получаем метод действия из сервиса
            action_method = getattr(service, action_name, None)
            if not action_method:
                error_result = {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Метод '{action_name}' не найден в сервисе '{service_name}'"
                    }
                }
                self._log_action_result(action_name, service_name, error_result)
                return error_result
            
            # Прокидываем валидированные данные как data словарь
            result = await action_method(data=validated_data)
            
            # Централизованное логирование ошибок
            self._log_action_result(action_name, service_name, result)
            
            return result
            
        except Exception as e:
            error_result = {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
            self._log_action_result(action_name, service_name, error_result)
            return error_result
    
    async def execute_action_secure(self, action_name: str, data: dict = None, queue_name: str = None, 
                                   fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Безопасное выполнение действия с проверкой tenant_access
        Проверяет доступ по tenant_id и вызывает обычный execute_action
        """
        
        # Если data не передан, используем пустой словарь
        if data is None:
            data = {}
        
        # Проверяем доступ перед выполнением
        access_result = self._validate_access(action_name, data)
        if access_result.get("result") != "success":
            # Если return_future - создаем Future с ошибкой доступа
            if return_future:
                error_future = asyncio.Future()
                error_future.set_result(access_result)
                return error_future
            return access_result
        
        # Вызываем обычный execute_action с queue_name="action" по умолчанию для secure
        target_queue = queue_name if queue_name else "action"
        
        return await self.execute_action(
            action_name=action_name,
            data=data,
            queue_name=target_queue,
            fire_and_forget=fire_and_forget,
            return_future=return_future
        )
    
    def _create_action_wrapper(self, action_name: str, data: dict):
        """Создает обертку для выполнения действия в TaskManager"""
        async def wrapper():
            return await self._execute_action_direct(action_name, data)
        return wrapper
    
    def _log_action_result(self, action_name: str, service_name: str, result: Dict[str, Any]):
        """Централизованное логирование результатов действий"""
        try:
            result_status = result.get('result', 'unknown')
            
            if result_status == 'error':
                error_obj = result.get('error', {})
                error_msg = error_obj.get('message', 'Unknown error')
                error_code = error_obj.get('code', '')
                if error_code:
                    error_msg = f"[{error_code}] {error_msg}"
                self.logger.error(f"Действие {{{action_name}}} ({service_name}) завершилось с ошибкой: {error_msg}")
            
            elif result_status == 'timeout':
                error_obj = result.get('error', {})
                timeout_msg = error_obj.get('message', 'Timeout')
                self.logger.warning(f"Действие {{{action_name}}} ({service_name}) завершилось по таймауту: {timeout_msg}")
            
            elif result_status == 'not_found':
                pass

            elif result_status == 'success':
                # Успешные действия не логируем (чтобы не спамить)
                pass
            
            elif result_status == 'failed':
                # Неудачное прохождение валидации - не логируем (это нормальное поведение)
                pass
            
            else:
                # Неизвестный статус
                self.logger.warning(f"Действие {{{action_name}}} ({service_name}) завершилось с неизвестным статусом: {result_status}")
                
        except Exception as e:
            self.logger.error(f"Ошибка логирования результата действия '{action_name}': {e}")
    
    def _get_available_actions(self) -> Dict[str, Any]:
        """Получение всех доступных действий с их метаданными"""
        try:
            actions = self._action_mapping.copy()
            return {
                "result": "success",
                "response_data": actions
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения доступных действий: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                },
                "response_data": {}
            }

