"""
Block Sync Executor - исполнитель синхронизации блоков тенантов
Выполняет синхронизацию отдельных блоков (bot/scenarios) для оптимизации производительности
"""

from typing import Any, Dict


class BlockSyncExecutor:
    """
    Исполнитель синхронизации блоков тенантов
    Оптимизирует синхронизацию: синхронизирует только измененные блоки (bot/scenarios)
    """
    
    def __init__(self, logger, tenant_parser, action_hub, github_sync, settings_manager, tenant_cache, storage_manager):
        self.logger = logger
        self.tenant_parser = tenant_parser
        self.action_hub = action_hub
        self.github_sync = github_sync
        self.settings_manager = settings_manager
        self.tenant_cache = tenant_cache
        self.storage_manager = storage_manager
        
        # Получаем границу системных тенантов один раз при инициализации
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 100)
    
    def _extract_error_message(self, error: dict) -> str:
        """
        Извлекает сообщение об ошибке из объекта ошибки
        """
        return error.get('message', 'Неизвестная ошибка') if error else 'Неизвестная ошибка'
    
    async def _prepare_tenant_data(self, tenant_id: int, pull_from_github: bool = False) -> Dict[str, Any]:
        """
        Подготовка данных тенанта: pull из GitHub (опционально) + создание тенанта если его нет
        """
        try:
            # Для системных тенантов всегда пропускаем pull из GitHub
            if pull_from_github and tenant_id <= self.max_system_tenant_id:
                pull_from_github = False
            
            # Обновляем данные из GitHub (если нужно)
            if pull_from_github:
                self.logger.info(f"[Tenant-{tenant_id}] Обновление данных из GitHub...")
                pull_result = await self.github_sync.pull_tenant(tenant_id)
                
                if pull_result.get("result") != "success":
                    error_msg = self._extract_error_message(pull_result.get('error', 'Неизвестная ошибка'))
                    self.logger.warning(f"[Tenant-{tenant_id}] Ошибка обновления из GitHub: {error_msg}, продолжаем с локальными данными")
                else:
                    self.logger.info(f"[Tenant-{tenant_id}] Данные из GitHub обновлены")
            
            # Создаем тенанта если его нет
            sync_tenant_result = await self.action_hub.execute_action('sync_tenant_data', {'tenant_id': tenant_id})
            
            if sync_tenant_result.get('result') != 'success':
                error_obj = sync_tenant_result.get('error', {})
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Ошибка создания/синхронизации тенанта: {error_msg}")
                return {"result": "error", "error": error_obj}
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка подготовки данных тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def _sync_scenarios_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Внутренняя синхронизация блока сценариев (без подготовки данных)
        """
        try:
            # Парсим сценарии
            parse_result = await self.tenant_parser.parse_scenarios(tenant_id)

            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Ошибка парсинга сценариев: {error_msg}")
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Не удалось распарсить сценарии для тенанта {tenant_id}: {error_msg}"
                    }
                }

            scenario_data = parse_result.get('response_data')

            if not scenario_data:
                self.logger.error(f"[Tenant-{tenant_id}] Нет данных сценариев после парсинга")
                return {"result": "error", "error": f"Не удалось получить данные сценариев для тенанта {tenant_id}"}

            # Синхронизация сценариев
            scenarios_count = len(scenario_data.get("scenarios", []))
            if scenarios_count > 0:

                sync_result = await self.action_hub.execute_action('sync_scenarios', {
                    'tenant_id': tenant_id,
                    'scenarios': scenario_data['scenarios']
                })

                if sync_result.get('result') != 'success':
                    error_obj = sync_result.get('error', {})
                    error_msg = self._extract_error_message(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации сценариев: {error_msg}")
                    return {"result": "error", "error": error_obj}

                self.logger.info(f"[Tenant-{tenant_id}] Сценарии успешно синхронизированы")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] Нет сценариев для синхронизации")

            return {"result": "success"}

        except Exception as e:
            self.logger.error(f"Ошибка синхронизации сценариев: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def _sync_bot_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Внутренняя синхронизация блока бота (без подготовки данных)
        """
        try:
            # Парсим данные бота
            parse_result = await self.tenant_parser.parse_bot(tenant_id)

            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Не удалось распарсить данные бота для тенанта {tenant_id}: {error_msg}"
                    }
                }

            bot_data = parse_result.get('response_data')

            if not bot_data:
                return {"result": "error", "error": f"Не удалось получить данные бота для тенанта {tenant_id}"}

            # Синхронизация конфигурации бота
            bot_id = None
            if bot_data.get("bot"):
                self.logger.info(f"[Tenant-{tenant_id}] Синхронизация конфигурации бота...")

                bot_config = bot_data.get('bot', {}).copy()
                bot_config['tenant_id'] = tenant_id

                sync_bot_result = await self.action_hub.execute_action('sync_bot_config', bot_config)

                if sync_bot_result.get('result') != 'success':
                    error_obj = sync_bot_result.get('error', {})
                    error_msg = self._extract_error_message(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации конфигурации бота: {error_msg}")
                    return {"result": "error", "error": error_obj}

                bot_id = sync_bot_result.get('response_data', {}).get('bot_id')
                self.logger.info(f"[Tenant-{tenant_id}] Конфигурация бота успешно синхронизирована")

                # Синхронизация команд бота
                if bot_data.get("bot_commands"):
                    commands_count = len(bot_data.get("bot_commands", []))
                    if commands_count > 0:
                        sync_result = await self.action_hub.execute_action('sync_bot_commands', {
                            'bot_id': bot_id,
                            'command_list': bot_data['bot_commands']
                        })
                        if sync_result.get('result') != 'success':
                            error_msg = self._extract_error_message(sync_result.get('error', 'Неизвестная ошибка'))
                            self.logger.warning(f"[Tenant-{tenant_id}] Ошибка синхронизации команд бота: {error_msg}")
                        else:
                            self.logger.info(f"[Tenant-{tenant_id}] Команды бота успешно синхронизированы")
                    else:
                        self.logger.info(f"[Tenant-{tenant_id}] Нет команд бота для синхронизации")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] Нет конфигурации бота для синхронизации")

            return {"result": "success"}

        except Exception as e:
            self.logger.error(f"Ошибка синхронизации бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_storage_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Внутренняя синхронизация блока storage (без подготовки данных)
        """
        try:
            # Парсим storage
            parse_result = await self.tenant_parser.parse_storage(tenant_id)
            
            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Ошибка парсинга storage: {error_msg}")
                return {
                    "result": "error",
                    "error": {
                        "code": "PARSE_ERROR",
                        "message": f"Не удалось распарсить storage для тенанта {tenant_id}: {error_msg}"
                    }
                }
            
            storage_data = parse_result.get('response_data', {}).get('storage', {})
            
            if not storage_data:
                self.logger.info(f"[Tenant-{tenant_id}] Нет данных storage для синхронизации")
                return {"result": "success"}
            
            # Синхронизация storage
            groups_count = len(storage_data)
            if groups_count > 0:

                success = await self.storage_manager.sync_storage(tenant_id, storage_data)
                
                if not success:
                    self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации storage")
                    return {
                        "result": "error",
                        "error": {
                            "code": "SYNC_ERROR",
                            "message": "Не удалось синхронизировать storage"
                        }
                    }
                
                self.logger.info(f"[Tenant-{tenant_id}] Storage успешно синхронизирован")
            else:
                self.logger.info(f"[Tenant-{tenant_id}] Нет storage для синхронизации")
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_config_block(self, tenant_id: int) -> Dict[str, Any]:
        """
        Внутренняя синхронизация блока конфига тенанта (без подготовки данных)
        """
        try:
            # Парсим конфиг тенанта (config.yaml)
            parse_result = await self.tenant_parser.parse_tenant_config(tenant_id)
            
            config = None
            if parse_result.get("result") != "success":
                error_obj = parse_result.get('error')
                error_msg = self._extract_error_message(error_obj)
                # Файл config.yaml опционален, поэтому не возвращаем ошибку
                self.logger.warning(f"[Tenant-{tenant_id}] Ошибка парсинга конфига тенанта: {error_msg}, обновляем кэш из БД")
            else:
                config = parse_result.get('response_data', {})
            
            if not config:
                # Нет конфига в файле - обновляем кэш из БД (создаст пустой конфиг в кэше, если его нет)
                self.logger.info(f"[Tenant-{tenant_id}] Нет конфига в конфигурации, обновляем кэш из БД")
                await self.tenant_cache.update_tenant_config_cache(tenant_id)
                return {"result": "success"}
            
            # Синхронизация конфига через действие (как в других блоках)
            update_data = {
                'tenant_id': tenant_id,
                **config
            }
            
            sync_result = await self.action_hub.execute_action('update_tenant_config', update_data)
            
            if sync_result.get('result') != 'success':
                error_obj = sync_result.get('error', {})
                error_msg = self._extract_error_message(error_obj)
                self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации конфига тенанта: {error_msg}")
                return {"result": "error", "error": error_obj}
            
            self.logger.info(f"[Tenant-{tenant_id}] Конфиг тенанта успешно синхронизирован")
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации конфига тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "SYNC_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_blocks(self, tenant_id: int, blocks: Dict[str, bool], pull_from_github: bool = False) -> Dict[str, Any]:
        """
        Синхронизирует указанные блоки тенанта с оптимизацией
        """
        try:
            bot_changed = blocks.get("bot", False)
            scenarios_changed = blocks.get("scenarios", False)
            storage_changed = blocks.get("storage", False)
            config_changed = blocks.get("config", False)
            
            if not bot_changed and not scenarios_changed and not storage_changed and not config_changed:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет блоков для синхронизации"
                    }
                }
            
            self.logger.info(
                f"Синхронизация тенанта [Tenant-{tenant_id}] "
                f"(bot: {'+' if bot_changed else '-'}, scenarios: {'+' if scenarios_changed else '-'}, "
                f"storage: {'+' if storage_changed else '-'}, config: {'+' if config_changed else '-'})..."
            )
            
            # Подготовка данных (pull + создание тенанта) выполняется один раз
            prepare_result = await self._prepare_tenant_data(tenant_id, pull_from_github)
            if prepare_result.get("result") != "success":
                error_obj = prepare_result.get("error", {})
                await self.tenant_cache.set_last_failed(tenant_id, error_obj)
                return {"result": "error", "error": error_obj}

            # Синхронизация блоков по необходимости
            # ВАЖНО: Сначала синхронизируем scenarios, storage и config, затем bot (который запускает пулинг)
            # Это гарантирует, что все данные готовы до начала обработки событий
            
            if scenarios_changed:
                scenarios_result = await self._sync_scenarios_block(tenant_id)
                if scenarios_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, scenarios_result.get("error"))
                    return scenarios_result
            
            if storage_changed:
                storage_result = await self._sync_storage_block(tenant_id)
                if storage_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, storage_result.get("error"))
                    return storage_result
            
            if config_changed:
                config_result = await self._sync_config_block(tenant_id)
                if config_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, config_result.get("error"))
                    return config_result
            
            # Синхронизация бота в конце - запускает пулинг/вебхуки после готовности всех данных
            if bot_changed:
                bot_result = await self._sync_bot_block(tenant_id)
                if bot_result.get("result") != "success":
                    await self.tenant_cache.set_last_failed(tenant_id, bot_result.get("error"))
                    return bot_result
            
            await self.tenant_cache.set_last_updated(tenant_id)
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации блоков тенанта {tenant_id}: {e}")
            error_obj = {
                "code": "INTERNAL_ERROR",
                "message": f"Внутренняя ошибка: {str(e)}"
            }
            await self.tenant_cache.set_last_failed(tenant_id, error_obj)
            return {"result": "error", "error": error_obj}
