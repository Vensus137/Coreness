import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from .promo_management import PromoManagement
from .promo_operations import PromoOperations

class PromoManager:
    """Сервис для управления промокодами"""
    
    def __init__(self, **kwargs):
        self.database_service = kwargs['database_service']
        self.logger = kwargs['logger']
        self.hash_manager = kwargs['hash_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.settings_manager = kwargs['settings_manager']
        self.users_directory = kwargs['users_directory']
        
        # Инициализируем модули с прямым указанием зависимостей
        self.promo_management = PromoManagement(
            database_service=self.database_service,
            logger=self.logger,
            settings_manager=self.settings_manager,
            datetime_formatter=self.datetime_formatter,
            users_directory=self.users_directory
        )
        
        self.promo_operations = PromoOperations(
            hash_manager=self.hash_manager,
            datetime_formatter=self.datetime_formatter,
            settings_manager=self.settings_manager
        )
        
        # Получаем настройки
        settings = self.settings_manager.get_plugin_settings("promo_manager")
        self.queue_read_interval = settings.get('queue_read_interval', 0.10)
        self.queue_batch_size = settings.get('queue_batch_size', 50)
    
    async def run(self):
        """Основной цикл работы сервиса"""
        self.logger.info(f"Старт фонового цикла (interval={self.queue_read_interval}, batch_size={self.queue_batch_size})")
        
        while True:
            try:
                await self._process_queue()
            except Exception as e:
                self.logger.error(f'Ошибка при обработке очереди: {e}')
            await asyncio.sleep(self.queue_read_interval)
    
    async def _process_queue(self):
        """Обработка очереди действий"""
        with self.database_service.session_scope('actions', 'promo_codes', 'users') as (session, repos):
            actions_repo = repos['actions']
            promo_repo = repos['promo_codes']
            users_repo = repos['users']
            
            # Получаем пачку действий типа 'create_promo', 'modify_promo', 'check_promo', 'promo_management'
            actions = actions_repo.get_pending_actions_by_type_parsed(
                ['create_promo', 'modify_promo', 'check_promo', 'promo_management'], 
                limit=self.queue_batch_size
            )
            
            if actions:
                for action in actions:
                    await self._handle_promo_action(action, actions_repo, promo_repo, users_repo, session)
    
    async def _handle_promo_action(self, action: Dict[str, Any], actions_repo: Any, promo_repo: Any, users_repo: Any, session: Any):
        """Обрабатывает одно действие промокода"""
        try:
            action_id = action.get('id')
            action_type = action.get('action_type', '')
            
            # Определяем тип действия и вызываем соответствующий метод
            if action_type == 'create_promo':
                result = await self.promo_operations.create_promo(action, promo_repo)
            elif action_type == 'modify_promo':
                result = await self.promo_operations.modify_promo(action, promo_repo)
            elif action_type == 'check_promo':
                result = await self.promo_operations.check_promo(action, promo_repo)
            elif action_type == 'promo_management':
                result = await self.promo_management.handle_promo_management(action, promo_repo, users_repo)
            else:
                self.logger.warning(f"Неизвестный тип действия: {action_type}")
                result = {'error': f'Неизвестный тип действия: {action_type}'}
            
            # Обновляем статус действия
            if result.get('error'):
                actions_repo.update_action(action_id, status='failed', response_data=result)
            else:
                actions_repo.update_action(action_id, status='completed', response_data=result)
            
            session.commit()
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки действия {action.get('id')}: {e}")
            # Помечаем действие как неудачное
            actions_repo.update_action(
                action.get('id'), 
                status='failed',
                response_data={'error': str(e)}
            )
            session.rollback()
