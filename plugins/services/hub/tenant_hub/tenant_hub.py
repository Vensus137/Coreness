"""
Tenant Hub - сервис для управления конфигурациями тенантов
Координатор загрузки данных тенантов через специализированные сервисы
"""

from typing import Any, Dict

from .core_sync.block_sync_executor import BlockSyncExecutor
from .core_sync.sync_orchestrator import SyncOrchestrator
from .github_sync.base import GitHubSyncBase
from .github_sync.smart_sync import SmartGitHubSync
from .storage.storage_manager import StorageManager
from .utils.tenant_cache import TenantCache
from .utils.tenant_data_manager import TenantDataManager
from .utils.tenant_parser import TenantParser


class TenantHub:
    """
    Сервис для управления конфигурациями тенантов
    - Координирует загрузку данных тенантов
    - Делегирует загрузку конкретных частей специализированным сервисам
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        self.condition_parser = kwargs['condition_parser']
        self.task_manager = kwargs['task_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.http_server = kwargs.get('http_server')
        
        # Получаем максимальный ID системного тенанта из глобальных настроек
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 100)
        
        # Настройки вебхуков
        plugin_settings = self.settings_manager.get_plugin_settings('tenant_hub')
        use_webhooks_setting = plugin_settings.get('use_webhooks', False)
        
        # Автоматически переключаем на пулинг, если вебхуки недоступны
        self.use_webhooks = use_webhooks_setting and self.http_server is not None
        
        if use_webhooks_setting and not self.use_webhooks:
            self.logger.warning("Вебхуки GitHub включены в настройках, но http_server недоступен - автоматически используется пулинг")
        
        self.github_webhook_secret = plugin_settings.get('github_webhook_secret', '')
        self.github_webhook_endpoint = plugin_settings.get('github_webhook_endpoint', '/webhooks/github')
        
        # Регистрируем эндпоинт для GitHub вебхука (если вебхуки включены и доступны)
        if self.use_webhooks:
            self._register_github_webhook_endpoint()
        
        # Создаем менеджер данных тенанта
        self.tenant_data_manager = TenantDataManager(self.database_manager, self.logger)
        
        # Создаем кэш тенанта
        self.tenant_cache = TenantCache(self.database_manager, self.logger, self.datetime_formatter, kwargs['cache_manager'], self.settings_manager)
        
        # Создаем папку для тенантов (один раз при инициализации)
        self._ensure_tenants_directory_exists()
        
        # Создаем подмодули
        self.tenant_parser = TenantParser(self.logger, self.settings_manager, self.condition_parser)
        
        # Создаем менеджер хранилища тенанта
        self.storage_manager = StorageManager(
            self.database_manager,
            self.logger,
            self.tenant_parser,
            self.settings_manager
        )
        self.github_sync = GitHubSyncBase(self.logger, self.settings_manager)
        self.smart_github_sync = SmartGitHubSync(self.logger, self.settings_manager)
        
        # Создаем исполнитель синхронизации блоков
        self.block_sync_executor = BlockSyncExecutor(
            self.logger,
            self.tenant_parser,
            self.action_hub,
            self.github_sync,
            self.settings_manager,
            self.tenant_cache,
            self.storage_manager
        )
        
        # Создаем оркестратор синхронизации
        self.sync_orchestrator = SyncOrchestrator(
            self.logger,
            self.smart_github_sync,
            self.github_sync,
            self.block_sync_executor,
            self.settings_manager,
            self.task_manager
        )
        
        # Регистрируем себя в ActionHub
        self.action_hub.register('tenant_hub', self)
    
    def _ensure_tenants_directory_exists(self):
        """Создает папку для тенантов если её нет"""
        try:
            from pathlib import Path
            global_settings = self.settings_manager.get_global_settings()
            tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
            project_root = self.settings_manager.get_project_root()
            self.tenants_path = Path(project_root) / tenants_config_path
            
            if not self.tenants_path.exists():
                self.tenants_path.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Создана папка тенантов: {self.tenants_path}")
                
        except Exception as e:
            self.logger.error(f"Ошибка создания папки тенантов: {e}")
    
    async def run(self):
        """Основной цикл работы сервиса с регулярной синхронизацией в фоне"""
        try:
            import asyncio
            
            # Получаем настройки синхронизации
            plugin_settings = self.settings_manager.get_plugin_settings("tenant_hub")
            sync_interval = plugin_settings.get('sync_interval', 60)
            
            # Первая синхронизация при запуске (выполняем напрямую, не через очередь)
            # Синхронизируем все тенанты (системные локально + публичные из GitHub)
            self.logger.info("Первоначальная синхронизация всех тенантов...")
            await self.sync_all_tenants({})
            
            # Если вебхуки включены - эндпоинт уже зарегистрирован при инициализации
            # Сервер запустится через http_api_service (если доступен)
            if self.use_webhooks:
                if self.http_server:
                    self.logger.info("Вебхуки включены, эндпоинт зарегистрирован, сервер запустится через http_api_service")
                    # Сервис завершается - HTTP сервер работает в фоне, события обрабатываются через вебхуки
                    return
                else:
                    self.logger.warning("Вебхуки включены, но http_server недоступен - используется пулинг как fallback")
            
            # Если вебхуки выключены - работаем как раньше (пулинг)
            # Если интервал = 0, автосинхронизация отключена
            if sync_interval <= 0:
                self.logger.info("Автоматическая синхронизация отключена (sync_interval = 0)")
                return
            
            # Цикл регулярной синхронизации - отправляем задачи в фоне
            self.logger.info(f"Запущен цикл фонового обновления (интервал: {sync_interval} сек)")
            
            while True:
                await asyncio.sleep(sync_interval)
                
                # Последовательная проверка и обновление публичных тенантов без фоновой задачи
                try:
                    await self.sync_orchestrator.sync_public_tenants()
                except Exception as e:
                    self.logger.error(f"Ошибка фоновой синхронизации публичных тенантов: {e}")
                    
        except asyncio.CancelledError:
            self.logger.info("Цикл синхронизации прерван")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле: {e}")
            raise
    
    # === Методы управления вебхуками ===
    
    def _register_github_webhook_endpoint(self):
        """Регистрация эндпоинта для GitHub вебхука (вызывается при инициализации)"""
        try:
            from .handlers.github_webhook import GitHubWebhookHandler
            
            if not self.http_server:
                self.logger.warning("http_server не найден, не удалось зарегистрировать эндпоинт GitHub вебхука")
                return
            
            # Проверяем наличие секрета
            if not self.github_webhook_secret:
                self.logger.warning("GitHub webhook secret не установлен, вебхуки могут быть небезопасны")
            
            # Создаем обработчик
            handler_instance = GitHubWebhookHandler(
                self.action_hub,
                self.github_webhook_secret,
                self.logger
            )
            
            # Регистрируем эндпоинт (синхронно, при инициализации)
            success = self.http_server.register_endpoint(
                'POST',
                self.github_webhook_endpoint,
                handler_instance.handle
            )
            
            if success:
                self.logger.info(f"Эндпоинт GitHub вебхука зарегистрирован на {self.github_webhook_endpoint}")
            else:
                self.logger.error("Не удалось зарегистрировать эндпоинт GitHub вебхука")
                
        except Exception as e:
            self.logger.error(f"Ошибка регистрации эндпоинта GitHub вебхука: {e}")
            
    # === Actions для ActionHub ===
    
    async def sync_tenant(self, data: Dict[str, Any], pull_from_github: bool = True) -> Dict[str, Any]:
        """
        Синхронизация конфигурации тенанта с базой данных
        По умолчанию обновляет данные из GitHub перед синхронизацией
        Делегирует выполнение оркестратору синхронизации
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Используем оркестратор для синхронизации тенанта (оба блока)
            return await self.sync_orchestrator.sync_tenant(tenant_id, pull_from_github)
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_all_tenants(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизация всех тенантов: системных (локально) + публичных (из GitHub)
        Делегирует выполнение оркестратору синхронизации
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.sync_orchestrator.sync_all_tenants()
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации всех тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_tenant_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Синхронизация данных тенанта: создание/обновление тенанта"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Используем TenantDataManager для синхронизации данных тенанта
            # Передаем data напрямую, так как он уже содержит все данные тенанта
            return await self.tenant_data_manager.sync_tenant_data(data)
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации данных тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_tenant_scenarios(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизация сценариев тенанта: pull из GitHub + парсинг + синхронизация
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Единая точка входа: синхронизируем только сценарии
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": False, "scenarios": True, "storage": False, "config": False},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации сценариев: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_tenant_bot(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизация бота тенанта: pull из GitHub + парсинг + синхронизация
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Единая точка входа: синхронизируем только бота
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": True, "scenarios": False, "storage": False, "config": False},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_tenant_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизация storage тенанта: pull из GitHub + парсинг + синхронизация
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Единая точка входа: синхронизируем только storage
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": False, "scenarios": False, "storage": True, "config": False},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизация конфига тенанта: pull из GitHub + парсинг + синхронизация
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Единая точка входа: синхронизируем только конфиг
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": False, "scenarios": False, "storage": False, "config": True},
                pull_from_github=True
            )
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации конфига: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
            
    async def sync_tenants_from_files(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Синхронизация тенантов из списка измененных файлов (универсальный метод для вебхуков и пуллинга)
        Принимает список файлов в формате [{"filename": "path"}, ...] или ["path1", "path2", ...]
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            files = data.get('files', [])
            
            if not files:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Список файлов пуст"
                    }
                }
            
            # Преобразуем формат в универсальный (если нужно)
            normalized_files = []
            for file_item in files:
                if isinstance(file_item, str):
                    # Формат из вебхука: ["path1", "path2"]
                    normalized_files.append({"filename": file_item})
                elif isinstance(file_item, dict):
                    # Формат из Compare API: [{"filename": "path"}, ...]
                    normalized_files.append(file_item)
            
            # Используем существующую логику из smart_sync для парсинга
            changed_tenants = self.smart_github_sync._extract_tenant_changes_with_protection(normalized_files)
            
            if not changed_tenants:
                self.logger.info("Нет измененных тенантов в списке файлов")
                return {"result": "success", "response_data": {"synced_tenants": 0}}
            
            # Синхронизируем каждый измененный тенант
            self.logger.info(f"Обнаружены изменения в {len(changed_tenants)} тенантах")
            synced_count = 0
            errors = []
            
            for tenant_id, blocks in changed_tenants.items():
                try:
                    blocks_str = f"(bot: {'+' if blocks.get('bot') else '-'}, scenarios: {'+' if blocks.get('scenarios') else '-'}, storage: {'+' if blocks.get('storage') else '-'}, config: {'+' if blocks.get('config') else '-'})"
                    self.logger.info(f"[Tenant-{tenant_id}] Синхронизация по вебхуку {blocks_str}")
                    
                    # Используем существующий метод синхронизации блоков
                    result = await self.block_sync_executor.sync_blocks(
                        tenant_id,
                        blocks,
                        pull_from_github=True  # Всегда обновляем из GitHub при вебхуке
                    )
                    
                    if result.get('result') == 'success':
                        synced_count += 1
                    else:
                        error_obj = result.get('error', {})
                        errors.append(f"Tenant-{tenant_id}: {error_obj.get('message', 'Неизвестная ошибка')}")
                        
                except Exception as e:
                    self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации по вебхуку: {e}")
                    errors.append(f"Tenant-{tenant_id}: {str(e)}")
            
            if errors:
                return {
                    "result": "partial_success",
                    "response_data": {
                        "synced_tenants": synced_count,
                        "total_tenants": len(changed_tenants),
                        "errors": errors
                    }
                }
            
            return {
                "result": "success",
                "response_data": {
                    "synced_tenants": synced_count,
                    "total_tenants": len(changed_tenants)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации тенантов из файлов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_tenant_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение статуса тенанта:
        - bot_is_active, bot_is_polling, bot_is_webhook_active, bot_is_working (через bot_hub)
        - last_updated_at, last_failed_at, last_error (из TenantCache)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Получаем bot_id для тенанта
            bot_id = await self.tenant_cache.get_bot_id_by_tenant_id(tenant_id)
            
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Бот для тенанта {tenant_id} не найден"
                    }
                }
            
            # Получаем статус бота через bot_hub
            bot_status = await self.action_hub.execute_action('get_bot_status', {'bot_id': bot_id})
            
            if bot_status.get('result') != 'success':
                return bot_status
            
            # Переименовываем поля для понятности и дополняем метаданными кэша
            response_data = bot_status.get('response_data', {})
            cache_meta = await self.tenant_cache.get_tenant_cache(tenant_id)

            return {
                "result": "success",
                "response_data": {
                    "bot_is_active": response_data.get('is_active'),
                    "bot_is_polling": response_data.get('is_polling'),
                    "bot_is_webhook_active": response_data.get('is_webhook_active'),
                    "bot_is_working": response_data.get('is_working'),
                    "last_updated_at": cache_meta.get('last_updated_at'),
                    "last_failed_at": cache_meta.get('last_failed_at'),
                    "last_error": cache_meta.get('last_error')
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения статуса тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Получение значений storage для тенанта"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Преобразуем числа в строки для group_key и key (если переданы числа)
            group_key = data.get('group_key')
            if group_key is not None and not isinstance(group_key, str):
                group_key = str(group_key)
            
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.storage_manager.get_storage(
                data.get('tenant_id'),
                group_key=group_key,
                group_key_pattern=data.get('group_key_pattern'),
                key=key,
                key_pattern=data.get('key_pattern'),
                format_yaml=data.get('format', False)
            )
        except Exception as e:
            self.logger.error(f"Ошибка получения storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }

    async def set_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Установка значений storage для тенанта
        Поддерживает смешанный подход с приоритетом: group_key -> key -> value -> values
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            group_key = data.get('group_key')
            # Преобразуем число в строку для group_key (если передано число)
            if group_key is not None and not isinstance(group_key, str):
                group_key = str(group_key)
            
            key = data.get('key')
            # Преобразуем число в строку для key (если передано число)
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            value = data.get('value')
            values = data.get('values')
            
            return await self.storage_manager.set_storage(
                tenant_id,
                group_key=group_key,
                key=key,
                value=value,
                values=values,
                format_yaml=data.get('format', False)
            )
        except Exception as e:
            self.logger.error(f"Ошибка установки storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def delete_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Удаление значений или групп из storage"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            # Преобразуем числа в строки для group_key и key (если переданы числа)
            group_key = data.get('group_key')
            if group_key is not None and not isinstance(group_key, str):
                group_key = str(group_key)
            
            key = data.get('key')
            if key is not None and not isinstance(key, str):
                key = str(key)
            
            return await self.storage_manager.delete_storage(
                data.get('tenant_id'),
                group_key=group_key,
                group_key_pattern=data.get('group_key_pattern'),
                key=key,
                key_pattern=data.get('key_pattern')
            )
        except Exception as e:
            self.logger.error(f"Ошибка удаления storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_storage_groups(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Получение списка уникальных ключей групп для тенанта"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.storage_manager.get_storage_groups(data.get('tenant_id'))
        except Exception as e:
            self.logger.error(f"Ошибка получения списка групп storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_tenants_list(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение списка всех ID тенантов с разделением на публичные и системные
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            master_repo = self.database_manager.get_master_repository()
            all_tenant_ids = await master_repo.get_all_tenant_ids()
            
            if all_tenant_ids is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось получить список тенантов из базы данных"
                    }
                }
            
            # Сортируем все ID по возрастанию
            all_tenant_ids = sorted(all_tenant_ids)
            
            # Разделяем на публичные (ID > max_system_tenant_id) и системные (ID <= max_system_tenant_id)
            public_tenant_ids = sorted([tid for tid in all_tenant_ids if tid > self.max_system_tenant_id])
            system_tenant_ids = sorted([tid for tid in all_tenant_ids if tid <= self.max_system_tenant_id])
            
            return {
                "result": "success",
                "response_data": {
                    "tenant_ids": all_tenant_ids,
                    "public_tenant_ids": public_tenant_ids,
                    "system_tenant_ids": system_tenant_ids,
                    "tenant_count": len(all_tenant_ids)
                }
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения списка тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def update_tenant_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновление конфига тенанта
        Обновляет только переданные поля, остальные не трогает
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            ai_token = data.get('ai_token')
            
            # Проверяем, что тенант существует
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            if not tenant_data:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Тенант {tenant_id} не найден"
                    }
                }
            
            # Подготавливаем данные для обновления (только переданные поля)
            # Если поле явно передано (даже если None) - обновляем его
            update_data = {}
            updated_fields = []
            
            if 'ai_token' in data:
                update_data['ai_token'] = ai_token  # Может быть None для удаления
                updated_fields.append('ai_token')
            
            if not update_data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет полей для обновления"
                    }
                }
            
            # Обновляем БД
            update_success = await master_repo.update_tenant(tenant_id, update_data)
            if not update_success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Не удалось обновить тенанта {tenant_id}"
                    }
                }
            
            # Обновляем кэш конфига из БД (чтобы все сервисы сразу получили актуальные данные)
            await self.tenant_cache.update_tenant_config_cache(tenant_id)
            
            self.logger.info(f"[Tenant-{tenant_id}] Обновлен конфиг тенанта: {', '.join(updated_fields)}")
            
            return {
                "result": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления атрибутов тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }