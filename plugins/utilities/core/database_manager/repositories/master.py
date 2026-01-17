"""
Мастер-репозиторий для всех операций с БД
Единая точка входа для всех репозиториев
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class MasterRepository:
    """
    Мастер-репозиторий - единая точка входа для всех операций с БД
    Делегирует вызовы соответствующим специализированным репозиториям
    """
    
    def __init__(self, database_manager):
        self.database_manager = database_manager
        self._tenant_repo = None
        self._scenario_repo = None
        self._bot_repo = None
        self._user_repo = None
        self._tenant_storage_repo = None
        self._user_storage_repo = None
        self._invoice_repo = None
        self._id_sequence_repo = None
        self._vector_storage_repo = None
        self._repositories_cache = {}
    
    # === Lazy loading репозиториев ===
    
    def _get_repository(self, repo_name: str):
        """Получить репозиторий с кэшированием"""
        if repo_name not in self._repositories_cache:
            # Ленивая загрузка репозитория через относительный импорт
            import importlib
            module = importlib.import_module(f'.{repo_name}', package=__package__)
            repo_class = getattr(module, f'{repo_name.title()}Repository')
            
            self._repositories_cache[repo_name] = repo_class(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        
        return self._repositories_cache[repo_name]
    
    @property
    def tenant(self):
        """Ленивая загрузка TenantRepository"""
        if self._tenant_repo is None:
            self._tenant_repo = self._get_repository('tenant')
        return self._tenant_repo
    
    @property
    def scenario(self):
        """Ленивая загрузка ScenarioRepository"""
        if self._scenario_repo is None:
            self._scenario_repo = self._get_repository('scenario')
        return self._scenario_repo
    
    @property
    def bot(self):
        """Ленивая загрузка BotRepository"""
        if self._bot_repo is None:
            self._bot_repo = self._get_repository('bot')
        return self._bot_repo
    
    @property
    def user(self):
        """Ленивая загрузка UserRepository"""
        if self._user_repo is None:
            self._user_repo = self._get_repository('user')
        return self._user_repo
    
    @property
    def tenant_storage(self):
        """Ленивая загрузка TenantStorageRepository"""
        if self._tenant_storage_repo is None:
            from .tenant_storage import TenantStorageRepository
            self._tenant_storage_repo = TenantStorageRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._tenant_storage_repo
    
    @property
    def user_storage(self):
        """Ленивая загрузка UserStorageRepository"""
        if self._user_storage_repo is None:
            from .user_storage import UserStorageRepository
            self._user_storage_repo = UserStorageRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._user_storage_repo
    
    @property
    def invoice(self):
        """Ленивая загрузка InvoiceRepository"""
        if self._invoice_repo is None:
            from .invoice import InvoiceRepository
            self._invoice_repo = InvoiceRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._invoice_repo
    
    @property
    def id_sequence(self):
        """Ленивая загрузка IdSequenceRepository"""
        if self._id_sequence_repo is None:
            from .id_sequence import IdSequenceRepository
            self._id_sequence_repo = IdSequenceRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._id_sequence_repo
    
    @property
    def vector_storage(self):
        """Ленивая загрузка VectorStorageRepository"""
        if self._vector_storage_repo is None:
            from .vector_storage import VectorStorageRepository
            self._vector_storage_repo = VectorStorageRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._vector_storage_repo
    
    # === Tenant операции ===
    
    async def get_all_tenant_ids(self) -> List[int]:
        """Получить список всех ID тенантов"""
        return await self.tenant.get_all_tenant_ids()
    
    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Получить тенанта по ID"""
        return await self.tenant.get_tenant_by_id(tenant_id)
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Optional[int]:
        """Создать тенанта"""
        return await self.tenant.create_tenant(tenant_data)
    
    async def update_tenant(self, tenant_id: int, tenant_data: Dict[str, Any]) -> bool:
        """Обновить тенанта"""
        return await self.tenant.update_tenant(tenant_id, tenant_data)

    # === Bot операции ===

    async def get_all_bots(self) -> List[Dict[str, Any]]:
        """Получить всех ботов"""
        return await self.bot.get_all_bots()

    async def get_bot_by_id(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Получить конфигурацию бота по ID"""
        return await self.bot.get_bot_by_id(bot_id)

    async def get_bot_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Получить бота по tenant_id"""
        return await self.bot.get_bot_by_tenant_id(tenant_id)

    async def get_bot_by_telegram_id(self, telegram_bot_id: int) -> Optional[Dict[str, Any]]:
        """Получить бота по telegram_bot_id"""
        return await self.bot.get_bot_by_telegram_id(telegram_bot_id)

    async def get_commands_by_bot(self, bot_id: int) -> List[Dict[str, Any]]:
        """Получить команды бота"""
        return await self.bot.get_commands_by_bot(bot_id)
    
    async def delete_commands_by_bot(self, bot_id: int) -> bool:
        """Удалить все команды бота"""
        return await self.bot.delete_commands_by_bot(bot_id)
    
    async def save_commands_by_bot(self, bot_id: int, command_list: List[Dict[str, Any]]) -> int:
        """Сохранить команды бота"""
        return await self.bot.save_commands_by_bot(bot_id, command_list)
    
    async def create_bot(self, bot_data: Dict[str, Any]) -> Optional[int]:
        """Создать бота"""
        return await self.bot.create_bot(bot_data)
    
    async def update_bot(self, bot_id: int, bot_data: Dict[str, Any]) -> bool:
        """Обновить бота"""
        return await self.bot.update_bot(bot_id, bot_data)
    
    # === Scenario операции ===
    
    async def get_scenarios_by_tenant(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Получить все сценарии для tenant'а"""
        return await self.scenario.get_scenarios_by_tenant(tenant_id)
    
    async def get_triggers_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """Получить триггеры сценария"""
        return await self.scenario.get_triggers_by_scenario(scenario_id)
    
    async def get_steps_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """Получить шаги сценария"""
        return await self.scenario.get_steps_by_scenario(scenario_id)
    
    async def get_transitions_by_step(self, step_id: int) -> List[Dict[str, Any]]:
        """Получить переходы шага"""
        return await self.scenario.get_transitions_by_step(step_id)
    
    # === Методы удаления сценариев ===
    
    async def delete_steps_by_scenario(self, scenario_id: int) -> bool:
        """Удалить все шаги сценария (включая их переходы)"""
        return await self.scenario.delete_steps_by_scenario(scenario_id)
    
    async def delete_triggers_by_scenario(self, scenario_id: int) -> bool:
        """Удалить все триггеры сценария (включая их условия)"""
        return await self.scenario.delete_triggers_by_scenario(scenario_id)
    
    async def delete_scenario(self, scenario_id: int) -> bool:
        """Удалить сценарий"""
        return await self.scenario.delete_scenario(scenario_id)
    
    # === Методы создания сценариев ===
    
    async def create_scenario(self, scenario_data: Dict[str, Any]) -> Optional[int]:
        """Создать сценарий"""
        return await self.scenario.create_scenario(scenario_data)
    
    async def create_trigger(self, trigger_data: Dict[str, Any]) -> Optional[int]:
        """Создать триггер сценария"""
        return await self.scenario.create_trigger(trigger_data)
    
    async def create_step(self, step_data: Dict[str, Any]) -> Optional[int]:
        """Создать шаг сценария"""
        return await self.scenario.create_step(step_data)
    
    async def create_transition(self, transition_data: Dict[str, Any]) -> Optional[int]:
        """Создать переход шага"""
        return await self.scenario.create_transition(transition_data)
    
    # === Методы для scheduled сценариев ===
    
    async def get_scheduled_scenarios(self, tenant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получить все scheduled сценарии (с schedule IS NOT NULL)"""
        return await self.scenario.get_scheduled_scenarios(tenant_id)
    
    async def update_scenario_last_run(self, scenario_id: int, last_run) -> bool:
        """Обновить время последнего запуска scheduled сценария"""
        return await self.scenario.update_scenario_last_run(scenario_id, last_run)
    
    # === User операции ===
    
    async def get_user_ids_by_tenant(self, tenant_id: int) -> List[int]:
        """Получить список всех user_id для указанного тенанта"""
        return await self.user.get_user_ids_by_tenant(tenant_id)
    
    async def get_user_by_id(self, user_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        return await self.user.get_user_by_id(user_id, tenant_id)
    
    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Создание пользователя"""
        return await self.user.create_user(user_data)
    
    async def update_user(self, user_id: int, tenant_id: int, user_data: Dict[str, Any]) -> bool:
        """Обновление пользователя"""
        return await self.user.update_user(user_id, tenant_id, user_data)
    
    # === TenantStorage операции ===
    
    async def get_storage_records(self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None, key: Optional[str] = None, key_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Универсальное получение записей storage"""
        return await self.tenant_storage.get_records(tenant_id, group_key, group_key_pattern, key, key_pattern, limit)
    
    async def delete_storage_records(self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None, key: Optional[str] = None, key_pattern: Optional[str] = None) -> int:
        """Универсальное удаление записей storage (возвращает количество удаленных)"""
        return await self.tenant_storage.delete_records(tenant_id, group_key, group_key_pattern, key, key_pattern)
    
    async def set_storage_records(self, tenant_id: int, values: Dict[str, Dict[str, Any]]) -> bool:
        """Универсальная установка записей storage (batch для всех групп)"""
        return await self.tenant_storage.set_records(tenant_id, values)
    
    async def delete_groups_batch(self, tenant_id: int, group_keys: List[str]) -> Optional[int]:
        """Batch удаление нескольких групп одним запросом (возвращает количество удаленных)"""
        return await self.tenant_storage.delete_groups_batch(tenant_id, group_keys)
    
    async def get_storage_group_keys(self, tenant_id: int, limit: Optional[int] = None) -> Optional[List[str]]:
        """Получение списка уникальных ключей групп для тенанта"""
        return await self.tenant_storage.get_group_keys(tenant_id, limit)
    
    # === UserStorage операции ===
    
    async def get_user_storage_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Универсальное получение записей storage"""
        return await self.user_storage.get_records(tenant_id, user_id, key, key_pattern, limit)
    
    async def set_user_storage_records(self, tenant_id: int, user_id: int, values: Dict[str, Any]) -> bool:
        """Универсальная установка записей storage (batch для всех ключей)"""
        return await self.user_storage.set_records(tenant_id, user_id, values)
    
    async def delete_user_storage_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None) -> int:
        """Универсальное удаление записей storage (возвращает количество удаленных)"""
        return await self.user_storage.delete_records(tenant_id, user_id, key, key_pattern)
    
    async def get_user_storage_by_tenant_and_key(self, tenant_id: int, key: str) -> List[Dict[str, Any]]:
        """Получение всех записей storage для тенанта по ключу (для поиска пользователей)"""
        return await self.user_storage.get_by_tenant_and_key(tenant_id, key)
    
    # === Invoice операции ===
    
    async def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Получение инвойса по ID"""
        return await self.invoice.get_by_id(invoice_id)
    
    async def get_invoices_by_user(self, tenant_id: int, user_id: int, include_cancelled: bool = False) -> List[Dict[str, Any]]:
        """Получение всех инвойсов пользователя"""
        return await self.invoice.get_by_user(tenant_id, user_id, include_cancelled)
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Optional[int]:
        """Создание нового инвойса"""
        return await self.invoice.create(invoice_data)
    
    async def update_invoice(self, invoice_id: int, invoice_data: Dict[str, Any]) -> bool:
        """Обновление инвойса"""
        return await self.invoice.update(invoice_id, invoice_data)
    
    async def mark_invoice_as_paid(self, invoice_id: int, telegram_payment_charge_id: str, paid_at: datetime) -> bool:
        """Отметить инвойс как оплаченный"""
        return await self.invoice.mark_as_paid(invoice_id, telegram_payment_charge_id, paid_at)
    
    async def cancel_invoice(self, invoice_id: int) -> bool:
        """Отменить инвойс"""
        return await self.invoice.cancel(invoice_id)
    
    # === IdSequence операции ===
    
    async def get_id_sequence_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """Получение записи id_sequence по хэшу"""
        return await self.id_sequence.get_by_hash(hash_value)
    
    async def get_id_sequence_id_by_hash(self, hash_value: str) -> Optional[int]:
        """Получение ID по хэшу (быстрый метод)"""
        return await self.id_sequence.get_id_by_hash(hash_value)
    
    async def create_id_sequence(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """Создание новой записи id_sequence"""
        return await self.id_sequence.create(hash_value, seed)
    
    async def get_or_create_id_sequence(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """Получить существующий ID по хэшу или создать новую запись"""
        return await self.id_sequence.get_or_create(hash_value, seed)
    
    # === VectorStorage операции ===
    
    async def get_chunks_by_document(self, tenant_id: int, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """Получить все чанки документа по document_id"""
        return await self.vector_storage.get_chunks_by_document(tenant_id, document_id)
    
    async def get_chunks_by_type(self, tenant_id: int, document_type: str, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Получить чанки по типу документа"""
        return await self.vector_storage.get_chunks_by_type(tenant_id, document_type, limit)
    
    async def get_chunk(self, tenant_id: int, document_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """Получить чанк по составному ключу (tenant_id, document_id, chunk_index)"""
        return await self.vector_storage.get_chunk(tenant_id, document_id, chunk_index)
    
    async def create_chunk(self, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """Создать чанк документа"""
        return await self.vector_storage.create_chunk(chunk_data)
    
    async def create_chunks_batch(self, chunks_data: List[Dict[str, Any]]) -> Optional[int]:
        """Создать несколько чанков одним запросом (batch insert)"""
        return await self.vector_storage.create_chunks_batch(chunks_data)
    
    async def update_chunk(self, tenant_id: int, document_id: str, chunk_index: int, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """Обновить чанк по составному ключу (tenant_id, document_id, chunk_index)"""
        return await self.vector_storage.update_chunk(tenant_id, document_id, chunk_index, chunk_data)
    
    async def delete_document(self, tenant_id: int, document_id: str) -> Optional[int]:
        """Удалить все чанки документа по document_id"""
        return await self.vector_storage.delete_document(tenant_id, document_id)
    
    async def delete_vector_storage_by_date(self, tenant_id: int, until_date=None, since_date=None,
                                            metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Удалить чанки по дате processed_at"""
        return await self.vector_storage.delete_by_date(tenant_id, until_date, since_date, metadata_filter)
    
    async def search_vector_storage_similar(self, tenant_id: int, query_vector: List[float], limit: int = 5,
                                           min_similarity: float = 0.7, document_type=None, document_id=None,
                                           until_date=None, since_date=None, metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Поиск похожих чанков по вектору (cosine similarity)"""
        return await self.vector_storage.search_similar(tenant_id, query_vector, limit, min_similarity, document_type, document_id, until_date, since_date, metadata_filter)
    
    async def get_recent_vector_storage_chunks(self, tenant_id: int, limit: int, document_type=None, document_id=None,
                                               until_date=None, since_date=None, metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Получить последние N чанков по дате processed_at"""
        return await self.vector_storage.get_recent_chunks(tenant_id, limit, document_type, document_id, until_date, since_date, metadata_filter)