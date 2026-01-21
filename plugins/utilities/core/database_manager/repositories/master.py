"""
Master repository for all DB operations
Single entry point for all repositories
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class MasterRepository:
    """
    Master repository - single entry point for all DB operations
    Delegates calls to corresponding specialized repositories
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
    
    # === Lazy loading repositories ===
    
    def _get_repository(self, repo_name: str):
        """Get repository with caching"""
        if repo_name not in self._repositories_cache:
            # Lazy load repository through relative import
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
        """Lazy load TenantRepository"""
        if self._tenant_repo is None:
            self._tenant_repo = self._get_repository('tenant')
        return self._tenant_repo
    
    @property
    def scenario(self):
        """Lazy load ScenarioRepository"""
        if self._scenario_repo is None:
            self._scenario_repo = self._get_repository('scenario')
        return self._scenario_repo
    
    @property
    def bot(self):
        """Lazy load BotRepository"""
        if self._bot_repo is None:
            self._bot_repo = self._get_repository('bot')
        return self._bot_repo
    
    @property
    def user(self):
        """Lazy load UserRepository"""
        if self._user_repo is None:
            self._user_repo = self._get_repository('user')
        return self._user_repo
    
    @property
    def tenant_storage(self):
        """Lazy load TenantStorageRepository"""
        if self._tenant_storage_repo is None:
            from .tenant_storage import TenantStorageRepository
            self._tenant_storage_repo = TenantStorageRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._tenant_storage_repo
    
    @property
    def user_storage(self):
        """Lazy load UserStorageRepository"""
        if self._user_storage_repo is None:
            from .user_storage import UserStorageRepository
            self._user_storage_repo = UserStorageRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._user_storage_repo
    
    @property
    def invoice(self):
        """Lazy load InvoiceRepository"""
        if self._invoice_repo is None:
            from .invoice import InvoiceRepository
            self._invoice_repo = InvoiceRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._invoice_repo
    
    @property
    def id_sequence(self):
        """Lazy load IdSequenceRepository"""
        if self._id_sequence_repo is None:
            from .id_sequence import IdSequenceRepository
            self._id_sequence_repo = IdSequenceRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._id_sequence_repo
    
    @property
    def vector_storage(self):
        """Lazy load VectorStorageRepository"""
        if self._vector_storage_repo is None:
            from .vector_storage import VectorStorageRepository
            self._vector_storage_repo = VectorStorageRepository(
                session_factory=self.database_manager.session_factory,
                **self.database_manager._kwargs
            )
        return self._vector_storage_repo
    
    # === Tenant operations ===
    
    async def get_all_tenant_ids(self) -> List[int]:
        """Get list of all tenant IDs"""
        return await self.tenant.get_all_tenant_ids()
    
    async def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get tenant by ID"""
        return await self.tenant.get_tenant_by_id(tenant_id)
    
    async def create_tenant(self, tenant_data: Dict[str, Any]) -> Optional[int]:
        """Create tenant"""
        return await self.tenant.create_tenant(tenant_data)
    
    async def update_tenant(self, tenant_id: int, tenant_data: Dict[str, Any]) -> bool:
        """Update tenant"""
        return await self.tenant.update_tenant(tenant_id, tenant_data)

    # === Bot operations ===

    async def get_all_bots(self) -> List[Dict[str, Any]]:
        """Get all bots"""
        return await self.bot.get_all_bots()

    async def get_bot_by_id(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get bot configuration by ID"""
        return await self.bot.get_bot_by_id(bot_id)

    async def get_bot_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get bot by tenant_id"""
        return await self.bot.get_bot_by_tenant_id(tenant_id)

    async def get_bot_by_telegram_id(self, telegram_bot_id: int) -> Optional[Dict[str, Any]]:
        """Get bot by telegram_bot_id"""
        return await self.bot.get_bot_by_telegram_id(telegram_bot_id)

    async def get_commands_by_bot(self, bot_id: int) -> List[Dict[str, Any]]:
        """Get bot commands"""
        return await self.bot.get_commands_by_bot(bot_id)
    
    async def delete_commands_by_bot(self, bot_id: int) -> bool:
        """Delete all bot commands"""
        return await self.bot.delete_commands_by_bot(bot_id)
    
    async def save_commands_by_bot(self, bot_id: int, command_list: List[Dict[str, Any]]) -> int:
        """Save bot commands"""
        return await self.bot.save_commands_by_bot(bot_id, command_list)
    
    async def create_bot(self, bot_data: Dict[str, Any]) -> Optional[int]:
        """Create bot"""
        return await self.bot.create_bot(bot_data)
    
    async def update_bot(self, bot_id: int, bot_data: Dict[str, Any]) -> bool:
        """Update bot"""
        return await self.bot.update_bot(bot_id, bot_data)
    
    # === Scenario operations ===
    
    async def get_scenarios_by_tenant(self, tenant_id: int) -> List[Dict[str, Any]]:
        """Get all scenarios for tenant"""
        return await self.scenario.get_scenarios_by_tenant(tenant_id)
    
    async def get_triggers_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """Get scenario triggers"""
        return await self.scenario.get_triggers_by_scenario(scenario_id)
    
    async def get_steps_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        """Get scenario steps"""
        return await self.scenario.get_steps_by_scenario(scenario_id)
    
    async def get_transitions_by_step(self, step_id: int) -> List[Dict[str, Any]]:
        """Get step transitions"""
        return await self.scenario.get_transitions_by_step(step_id)
    
    # === Scenario deletion methods ===
    
    async def delete_steps_by_scenario(self, scenario_id: int) -> bool:
        """Delete all scenario steps (including their transitions)"""
        return await self.scenario.delete_steps_by_scenario(scenario_id)
    
    async def delete_triggers_by_scenario(self, scenario_id: int) -> bool:
        """Delete all scenario triggers (including their conditions)"""
        return await self.scenario.delete_triggers_by_scenario(scenario_id)
    
    async def delete_scenario(self, scenario_id: int) -> bool:
        """Delete scenario"""
        return await self.scenario.delete_scenario(scenario_id)
    
    # === Scenario creation methods ===
    
    async def create_scenario(self, scenario_data: Dict[str, Any]) -> Optional[int]:
        """Create scenario"""
        return await self.scenario.create_scenario(scenario_data)
    
    async def create_trigger(self, trigger_data: Dict[str, Any]) -> Optional[int]:
        """Create scenario trigger"""
        return await self.scenario.create_trigger(trigger_data)
    
    async def create_step(self, step_data: Dict[str, Any]) -> Optional[int]:
        """Create scenario step"""
        return await self.scenario.create_step(step_data)
    
    async def create_transition(self, transition_data: Dict[str, Any]) -> Optional[int]:
        """Create step transition"""
        return await self.scenario.create_transition(transition_data)
    
    # === Methods for scheduled scenarios ===
    
    async def get_scheduled_scenarios(self, tenant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all scheduled scenarios (with schedule IS NOT NULL)"""
        return await self.scenario.get_scheduled_scenarios(tenant_id)
    
    async def update_scenario_last_run(self, scenario_id: int, last_run) -> bool:
        """Update last run time of scheduled scenario"""
        return await self.scenario.update_scenario_last_run(scenario_id, last_run)
    
    # === User operations ===
    
    async def get_user_ids_by_tenant(self, tenant_id: int) -> List[int]:
        """Get list of all user_id for specified tenant"""
        return await self.user.get_user_ids_by_tenant(tenant_id)
    
    async def get_user_by_id(self, user_id: int, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Get user data"""
        return await self.user.get_user_by_id(user_id, tenant_id)
    
    async def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Create user"""
        return await self.user.create_user(user_data)
    
    async def update_user(self, user_id: int, tenant_id: int, user_data: Dict[str, Any]) -> bool:
        """Update user"""
        return await self.user.update_user(user_id, tenant_id, user_data)
    
    # === TenantStorage operations ===
    
    async def get_storage_records(self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None, key: Optional[str] = None, key_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Universal get storage records"""
        return await self.tenant_storage.get_records(tenant_id, group_key, group_key_pattern, key, key_pattern, limit)
    
    async def delete_storage_records(self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None, key: Optional[str] = None, key_pattern: Optional[str] = None) -> int:
        """Universal delete storage records (returns number of deleted)"""
        return await self.tenant_storage.delete_records(tenant_id, group_key, group_key_pattern, key, key_pattern)
    
    async def set_storage_records(self, tenant_id: int, values: Dict[str, Dict[str, Any]]) -> bool:
        """Universal set storage records (batch for all groups)"""
        return await self.tenant_storage.set_records(tenant_id, values)
    
    async def delete_groups_batch(self, tenant_id: int, group_keys: List[str]) -> Optional[int]:
        """Batch delete multiple groups with one query (returns number of deleted)"""
        return await self.tenant_storage.delete_groups_batch(tenant_id, group_keys)
    
    async def get_storage_group_keys(self, tenant_id: int, limit: Optional[int] = None) -> Optional[List[str]]:
        """Get list of unique group keys for tenant"""
        return await self.tenant_storage.get_group_keys(tenant_id, limit)
    
    # === UserStorage operations ===
    
    async def get_user_storage_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Universal get storage records"""
        return await self.user_storage.get_records(tenant_id, user_id, key, key_pattern, limit)
    
    async def set_user_storage_records(self, tenant_id: int, user_id: int, values: Dict[str, Any]) -> bool:
        """Universal set storage records (batch for all keys)"""
        return await self.user_storage.set_records(tenant_id, user_id, values)
    
    async def delete_user_storage_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None) -> int:
        """Universal delete storage records (returns number of deleted)"""
        return await self.user_storage.delete_records(tenant_id, user_id, key, key_pattern)
    
    async def get_user_storage_by_tenant_and_key(self, tenant_id: int, key: str) -> List[Dict[str, Any]]:
        """Get all storage records for tenant by key (for user search)"""
        return await self.user_storage.get_by_tenant_and_key(tenant_id, key)
    
    # === Invoice operations ===
    
    async def get_invoice_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        return await self.invoice.get_by_id(invoice_id)
    
    async def get_invoices_by_user(self, tenant_id: int, user_id: int, include_cancelled: bool = False) -> List[Dict[str, Any]]:
        """Get all user invoices"""
        return await self.invoice.get_by_user(tenant_id, user_id, include_cancelled)
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Optional[int]:
        """Create new invoice"""
        return await self.invoice.create(invoice_data)
    
    async def update_invoice(self, invoice_id: int, invoice_data: Dict[str, Any]) -> bool:
        """Update invoice"""
        return await self.invoice.update(invoice_id, invoice_data)
    
    async def mark_invoice_as_paid(self, invoice_id: int, telegram_payment_charge_id: str, paid_at: datetime) -> bool:
        """Mark invoice as paid"""
        return await self.invoice.mark_as_paid(invoice_id, telegram_payment_charge_id, paid_at)
    
    async def cancel_invoice(self, invoice_id: int) -> bool:
        """Cancel invoice"""
        return await self.invoice.cancel(invoice_id)
    
    # === IdSequence operations ===
    
    async def get_id_sequence_by_hash(self, hash_value: str) -> Optional[Dict[str, Any]]:
        """Get id_sequence record by hash"""
        return await self.id_sequence.get_by_hash(hash_value)
    
    async def get_id_sequence_id_by_hash(self, hash_value: str) -> Optional[int]:
        """Get ID by hash (fast method)"""
        return await self.id_sequence.get_id_by_hash(hash_value)
    
    async def create_id_sequence(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """Create new id_sequence record"""
        return await self.id_sequence.create(hash_value, seed)
    
    async def get_or_create_id_sequence(self, hash_value: str, seed: Optional[str] = None) -> Optional[int]:
        """Get existing ID by hash or create new record"""
        return await self.id_sequence.get_or_create(hash_value, seed)
    
    # === VectorStorage operations ===
    
    async def get_chunks_by_document(self, tenant_id: int, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get all document chunks by document_id"""
        return await self.vector_storage.get_chunks_by_document(tenant_id, document_id)
    
    async def get_chunks_by_type(self, tenant_id: int, document_type: str, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """Get chunks by document type"""
        return await self.vector_storage.get_chunks_by_type(tenant_id, document_type, limit)
    
    async def get_chunk(self, tenant_id: int, document_id: str, chunk_index: int) -> Optional[Dict[str, Any]]:
        """Get chunk by composite key (tenant_id, document_id, chunk_index)"""
        return await self.vector_storage.get_chunk(tenant_id, document_id, chunk_index)
    
    async def create_chunk(self, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """Create document chunk"""
        return await self.vector_storage.create_chunk(chunk_data)
    
    async def create_chunks_batch(self, chunks_data: List[Dict[str, Any]]) -> Optional[int]:
        """Create multiple chunks with one query (batch insert)"""
        return await self.vector_storage.create_chunks_batch(chunks_data)
    
    async def update_chunk(self, tenant_id: int, document_id: str, chunk_index: int, chunk_data: Dict[str, Any]) -> Optional[bool]:
        """Update chunk by composite key (tenant_id, document_id, chunk_index)"""
        return await self.vector_storage.update_chunk(tenant_id, document_id, chunk_index, chunk_data)
    
    async def delete_document(self, tenant_id: int, document_id: str) -> Optional[int]:
        """Delete all document chunks by document_id"""
        return await self.vector_storage.delete_document(tenant_id, document_id)
    
    async def delete_vector_storage_by_date(self, tenant_id: int, until_date=None, since_date=None,
                                            metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """Delete chunks by processed_at date"""
        return await self.vector_storage.delete_by_date(tenant_id, until_date, since_date, metadata_filter)
    
    async def search_vector_storage_similar(self, tenant_id: int, query_vector: List[float], limit: int = 5,
                                           min_similarity: float = 0.7, document_type=None, document_id=None,
                                           until_date=None, since_date=None, metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Search similar chunks by vector (cosine similarity)"""
        return await self.vector_storage.search_similar(tenant_id, query_vector, limit, min_similarity, document_type, document_id, until_date, since_date, metadata_filter)
    
    async def get_recent_vector_storage_chunks(self, tenant_id: int, limit: int, document_type=None, document_id=None,
                                               until_date=None, since_date=None, metadata_filter: Optional[Dict[str, Any]] = None) -> Optional[List[Dict[str, Any]]]:
        """Get last N chunks by processed_at date"""
        return await self.vector_storage.get_recent_chunks(tenant_id, limit, document_type, document_id, until_date, since_date, metadata_filter)