import asyncio
from datetime import timedelta
from typing import Any


class UserManager:
    def __init__(self, **kwargs):
        self.database_service = kwargs['database_service']
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings('user_manager')
        self.queue_read_interval = settings.get('queue_read_interval', 0.1)
        self.queue_batch_size = settings.get('queue_batch_size', 50)
        self.state_expire = settings.get('state_expire', 600)

    async def run(self):
        self.logger.info(f"старт фонового цикла (interval={self.queue_read_interval}, batch_size={self.queue_batch_size})")
        while True:
            try:
                await self._process_queue()
            except Exception as e:
                self.logger.error(f'Ошибка при обработке очереди: {e}')
            await asyncio.sleep(self.queue_read_interval)

    async def _process_queue(self):
        with self.database_service.session_scope('actions', 'user_states') as (session, repos):
            actions_repo = repos['actions']
            user_states_repo = repos['user_states']
            # Получаем пачку действий типа 'user'
            actions = actions_repo.get_pending_actions_by_type_parsed('user', limit=self.queue_batch_size)
            for action in actions:
                await self._handle_user_action(action, user_states_repo, actions_repo, session)

    async def _handle_user_action(self, action: Any, user_states_repo: Any, actions_repo: Any, session: Any):
        try:
            # action уже является распарсенным dict
            user_id = action.get('user_id')
            state_type = action.get('user_state')
            action_id = action.get('id')

            if state_type is None:
                self.logger.error(f'Нет user_state в action_data для user_id={user_id}')
                actions_repo.update_action(action_id, status='failed')
                session.commit()
                return

            # Обрабатываем сброс состояния (пустая строка)
            if state_type == "":
                user_states_repo.clear_user_state(user_id)
        
            else:
                # Определяем время жизни состояния
                expire_seconds = action.get('expire_seconds')
                if expire_seconds is None:
                    expire_seconds = self.state_expire
                expired_at = self.datetime_formatter.now_local() + timedelta(seconds=expire_seconds)
                user_states_repo.update_user_state(user_id, state_type=state_type, expired_at=expired_at)

            actions_repo.update_action(action_id, status='completed')
            session.commit()
        except Exception as e:
            self.logger.error(f'Ошибка при установке состояния пользователя: {e}')
            action_id = action.get('id')
            actions_repo.update_action(action_id, status='failed')
            session.rollback()
