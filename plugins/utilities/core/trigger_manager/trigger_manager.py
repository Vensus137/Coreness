import json
from typing import Any, Dict


class TriggerManager:
    """
    Менеджер триггеров: обрабатывает входящие ивенты, ищет триггер, разворачивает сценарий и кладёт действия в очередь.
    """
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.scenarios_manager = kwargs['scenarios_manager']
        self.database_service = kwargs['database_service']
        self.button_mapper = kwargs['button_mapper']
        self.trigger_processing = kwargs['trigger_processing']
        self.permission_manager = kwargs.get('permission_manager')  # Опциональная зависимость
        self.datetime_formatter = kwargs['datetime_formatter']
        self.bot = kwargs['bot_initializer'].get_bot()

    async def handle_event(self, event: Dict[str, Any]):
        """
        Обработка входящего ивента: поиск триггера, разворачивание сценария, запись действий в очередь.
        Event уже конвертирован в безопасный справочник через ObjectConverter.
        """
        self.logger.debug(f"handle_event: входящий event: {event}")
        
        # 1. Поиск сценария по событию
        scenario_name = self.trigger_processing.find_scenario_by_event(event)
        if not scenario_name:
            self.logger.warning(f"Триггер не найден для ивента: {event}")
            return
            
        # 2. Получение развернутого сценария
        scenario = self.scenarios_manager.get_scenario(scenario_name)
        if not scenario:
            self.logger.warning(f"Сценарий '{scenario_name}' не найден или не может быть развёрнут")
            return
            
        actions = scenario.get('actions', [])
        if not actions:
            self.logger.warning(f"Сценарий '{scenario_name}' не содержит действий")
            return
            
        # 3. Обработка действий
        await self._process_actions(event, actions, scenario_name)

    async def _process_actions(self, event: Dict[str, Any], actions: list, scenario_name: str):
        """Обрабатывает список действий из сценария."""
        with self.database_service.session_scope('actions', 'users') as (_, repos):
            actions_repo = repos['actions']
            users_repo = repos['users']

            # Обновляем пользователя
            await self._update_user(event, users_repo)
            
            # Обрабатываем действия
            await self._process_actions_recursive(actions, event, actions_repo)

    async def _process_actions_recursive(self, actions: list, event: Dict[str, Any], 
                                       actions_repo, previous_action_id: int = None) -> int:
        """Рекурсивно обрабатывает список действий с поддержкой массивов сценариев."""
        for action in actions:
            if action.get('type') == 'scenario':
                # Обрабатываем сценарий (может быть строкой или массивом)
                # Возвращаем ID последнего действия из сценария
                last_action_id = await self._process_scenario_action(action, event, actions_repo, previous_action_id)
                if last_action_id:
                    previous_action_id = last_action_id
            else:
                # Обычное действие
                previous_action_id = await self._process_single_action(
                    action, event, actions_repo, previous_action_id
                )
        
        return previous_action_id

    async def _process_scenario_action(self, action: dict, event: Dict[str, Any], 
                                     actions_repo, previous_action_id: int = None):
        """Обрабатывает действие типа 'scenario' с поддержкой массивов."""
        scenario_names = self._normalize_to_list(action.get('value'))
        
        if not scenario_names:
            self.logger.error(f"Пустое значение value в действии scenario: {action}")
            return
        
        # Если несколько сценариев - связываем только с предыдущим действием до сценариев
        if len(scenario_names) > 1:
            for scenario_name in scenario_names:
                scenario = self.scenarios_manager.get_scenario(scenario_name)
                if not scenario:
                    self.logger.error(f"Сценарий '{scenario_name}' не найден")
                    continue
                
                scenario_actions = scenario.get('actions', [])
                if not scenario_actions:
                    self.logger.warning(f"Сценарий '{scenario_name}' не содержит действий")
                    continue
                
                # Рекурсивно обрабатываем действия сценария с тем же previous_action_id
                await self._process_actions_recursive(scenario_actions, event, actions_repo, previous_action_id)
        
        # Если один сценарий - связываем с последним действием внутри сценария
        else:
            scenario_name = scenario_names[0]
            
            scenario = self.scenarios_manager.get_scenario(scenario_name)
            if not scenario:
                self.logger.error(f"Сценарий '{scenario_name}' не найден")
                return
            
            scenario_actions = scenario.get('actions', [])
            if not scenario_actions:
                self.logger.warning(f"Сценарий '{scenario_name}' не содержит действий")
                return
            
            # Рекурсивно обрабатываем действия сценария и получаем ID последнего действия
            last_action_id = await self._process_actions_recursive(scenario_actions, event, actions_repo, previous_action_id)
            
            # Обновляем previous_action_id для следующих действий
            if last_action_id:
                return last_action_id
        
        return previous_action_id

    def _normalize_to_list(self, value) -> list:
        """Преобразует значение в список."""
        if isinstance(value, str):
            return [value]
        elif isinstance(value, list):
            return value
        else:
            self.logger.error(f"Неподдерживаемый тип value для сценария: {type(value)}")
            return []

    async def _update_user(self, event: Dict[str, Any], users_repo):
        """Обновляет или создает пользователя в базе данных."""
        user_id = event.get('user_id')
        if not user_id:
            return
            
        # Event уже содержит ISO строки дат, парсим их
        event_date = event.get('event_date')
        if event_date:
            last_activity = self.datetime_formatter.parse(event_date)
        else:
            last_activity = self.datetime_formatter.now_local()

        users_repo.add_or_update(
            user_id=user_id,
            username=event.get('username'),
            first_name=event.get('first_name'),
            last_name=event.get('last_name'),
            is_bot=event.get('is_bot', False),
            last_activity=last_activity
        )

    async def _process_single_action(self, action: dict, event: Dict[str, Any], 
                                   actions_repo, previous_action_id: int = None) -> int:
        """Обрабатывает одно действие из сценария."""
        # Проверяем доступ к действию
        fail_reason = await self._check_action_access(action, event)
        
        # Подготавливаем данные действия
        action_data = self._prepare_action_data(action, event, fail_reason)
        
        # Определяем статус и параметры цепочки
        status, chain_params = self._determine_action_status(action, action_data, previous_action_id)
        
        # Создаем действие в базе с привязкой к предыдущему действию
        current_action_id = self._create_action(
            action, event, action_data, status, chain_params, previous_action_id, actions_repo
        )
        
        return current_action_id

    async def _check_action_access(self, action: dict, event: Dict[str, Any]) -> str:
        """Проверяет доступ пользователя к действию."""
        user_id = event.get('user_id')
        if not user_id:
            return None
            
        # Если permission_manager недоступен - пропускаем проверки доступа
        if not self.permission_manager:
            # Логируем предупреждение о пропуске проверок
            required_role = action.get('required_role')
            required_permission = action.get('required_permission')
            group_admin = action.get('group_admin', False)
            
            if required_role or required_permission or group_admin:
                self.logger.warning(f"⚠️ Проверки доступа пропущены для user_id={user_id} к действию: {action.get('type')} (permission_manager отключен)")
            return None
            
        # Проверка ролей и разрешений
        required_role = action.get('required_role')
        required_permission = action.get('required_permission')
        
        if isinstance(required_role, str):
            required_role = [required_role]
        if isinstance(required_permission, str):
            required_permission = [required_permission]
            
        # Проверка всех типов доступа через permission_manager
        group_admin = action.get('group_admin', False)
        if not await self.permission_manager.check_access(user_id, required_role, required_permission, group_admin, event):
            self.logger.warning(f"❌ Доступ запрещен для user_id={user_id} к действию: {action.get('type')} (required_role={required_role}, required_permission={required_permission}, group_admin={group_admin})")
            return 'access_denied'
            
        return None

    def _prepare_action_data(self, action: dict, event: Dict[str, Any], fail_reason: str) -> dict:
        """Подготавливает данные действия. Event уже безопасный справочник."""
        # Простое объединение - event уже конвертирован в безопасный формат
        action_data = {**action, **event}
        
        if fail_reason:
            action_data['is_failed'] = True
            action_data['fail_reason'] = fail_reason
        else:
            action_data['is_failed'] = False
            
        return action_data

    def _determine_action_status(self, action: dict, action_data: dict, previous_action_id: int) -> tuple:
        """Определяет статус действия и параметры цепочки."""
        # Используем action_data для определения статуса ошибки
        chain = action.get('chain', False)
        chain_drop = action.get('chain_drop', None)
        
        # Определяем unlock_statuses
        if chain is True or chain == 'any':
            unlock_statuses = ['completed', 'failed', 'drop']
        elif isinstance(chain, str):
            unlock_statuses = [chain]
        elif isinstance(chain, list):
            unlock_statuses = [str(x) for x in chain if x]
        else:
            unlock_statuses = ['completed']
            
        is_chain = bool(chain)
        
        # Проверяем статус ошибки из action_data
        is_failed = action_data.get('is_failed', False)
        
        # Определяем статус
        if is_chain:
            if previous_action_id is not None:
                status = 'hold'
            else:
                if is_failed:
                    status = 'failed'
                else:
                    status = 'pending'
                self.logger.warning(f"Действие chain=true, но previous_id отсутствует — создаем как {status}")
        else:
            if is_failed:
                status = 'failed'
            else:
                status = 'pending'
        
        # Обрабатываем chain_drop_status
        chain_drop_status = None
        if chain_drop:
            if isinstance(chain_drop, str):
                chain_drop_status = [chain_drop]
            elif isinstance(chain_drop, list):
                chain_drop_status = [str(x) for x in chain_drop if x]
            else:
                self.logger.warning(f"Неподдерживаемый тип chain_drop: {type(chain_drop)}, значение: {chain_drop}")
        
        chain_params = {
            'is_chain': is_chain,
            'unlock_statuses': unlock_statuses,
            'chain_drop_status': chain_drop_status
        }
        
        return status, chain_params

    def _create_action(self, action: dict, event: Dict[str, Any], action_data: dict, 
                      status: str, chain_params: dict, previous_action_id: int, actions_repo) -> int:
        """Создает действие в базе данных. Event уже безопасный справочник."""
        user_id = event.get('user_id')
        chat_id = event.get('chat_id', 0)
        action_type = action.get('type')
        
        # Подготавливаем параметры для создания действия
        action_params = {
            'user_id': user_id,
            'chat_id': chat_id,
            'action_type': action_type,
            'action_data': action_data,
            'status': status,
            'chain_drop_status': chain_params['chain_drop_status']
        }
        
        # Добавляем prev_action_id если это цепочка
        if chain_params['is_chain'] and previous_action_id:
            action_params['prev_action_id'] = previous_action_id
            action_params['unlock_status'] = json.dumps(chain_params['unlock_statuses'], ensure_ascii=False)
        
        # action_data уже безопасный справочник, можно сразу сохранять
        return actions_repo.add_action(**action_params)


