"""
Sync Orchestrator - оркестратор синхронизации тенантов
Управляет синхронизацией системных и публичных тенантов через GitHub API
"""

from typing import Any, Dict


class SyncOrchestrator:
    """
    Оркестратор синхронизации тенантов
    Координирует синхронизацию системных (локально) и публичных (из GitHub) тенантов
    """
    
    def __init__(self, logger, smart_github_sync, github_sync, block_sync_executor, settings_manager, task_manager):
        self.logger = logger
        self.smart_github_sync = smart_github_sync
        self.github_sync = github_sync
        self.block_sync_executor = block_sync_executor
        self.settings_manager = settings_manager
        self.task_manager = task_manager
        
        # Получаем настройки один раз при инициализации
        global_settings = self.settings_manager.get_global_settings()
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 100)
        
        # Получаем путь к папке тенантов (она уже создана в tenant_hub)
        tenants_config_path = global_settings.get('tenants_config_path', 'config/tenant')
        from pathlib import Path
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
        
        # Флаг для предотвращения параллельных синхронизаций
        self._sync_in_progress = False
    
    async def sync_all_tenants(self) -> Dict[str, Any]:
        """
        Синхронизация всех тенантов: системных (локально) + публичных (из GitHub)
        """
        try:
            # Блок 1: Синхронизация системных тенантов из локальной папки
            system_result = await self.sync_system_tenants()
            
            # Блок 2: Синхронизация публичных тенантов из GitHub
            # Используем умную синхронизацию - она сама определит нужно ли делать полную синхронизацию
            # Если SHA нет - она автоматически сделает полную синхронизацию всех публичных
            public_result = await self.sync_public_tenants()
            
            # Определяем общий результат на основе результатов обоих блоков
            if system_result.get("result") == "error" or public_result.get("result") == "error":
                # Если хотя бы один блок вернул ошибку - возвращаем error с саммари
                errors = []
                if system_result.get("result") == "error":
                    error_obj = system_result.get('error', {})
                    errors.append(f"Системные: {error_obj.get('message', 'Неизвестная ошибка')}")
                if public_result.get("result") == "error":
                    error_obj = public_result.get('error', {})
                    errors.append(f"Публичные: {error_obj.get('message', 'Неизвестная ошибка')}")
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": "; ".join(errors)
                    }
                }
            
            # Оба блока успешно выполнены
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации всех тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_system_tenants(self) -> Dict[str, Any]:
        """
        Синхронизация системных тенантов из локальной папки (без GitHub, fire-and-forget, без ожидания выполнения)
        """
        try:
            system_tenant_ids = []
            for tenant_dir in self.tenants_path.iterdir():
                if tenant_dir.is_dir() and tenant_dir.name.startswith('tenant_'):
                    try:
                        tenant_id = int(tenant_dir.name.replace('tenant_', ''))
                        if tenant_id <= self.max_system_tenant_id:
                            system_tenant_ids.append(tenant_id)
                    except ValueError:
                        continue

            if not system_tenant_ids:
                self.logger.info("Нет системных тенантов для синхронизации")
                return {"result": "success", "response_data": {"updated_tenants": 0}}

            self.logger.info(f"Запускаем синхронизацию {len(system_tenant_ids)} системных тенантов в фоне...")
            errors = []
            for tenant_id in system_tenant_ids:
                res = await self.task_manager.submit_task(
                    task_id=f"sync_tenant_{tenant_id}",
                    coro=(lambda t=tenant_id: self.block_sync_executor.sync_blocks(
                        t, {"bot": True, "scenarios": True, "storage": True, "config": True}, pull_from_github=False)),
                    fire_and_forget=True
                )
                if res.get('result') != 'success':
                    error_obj = res.get('error', {})
                    error_msg = error_obj.get('message', 'Неизвестная ошибка') if isinstance(error_obj, dict) else str(error_obj)
                    self.logger.error(f"[Tenant-{tenant_id}] Не удалось отправить задачу синхронизации: {error_msg}")
                    errors.append(tenant_id)

            if not errors:
                return { "result": "success" }
            else:
                return {
                    "result": "partial_success",
                    "error": f"Не отправлены задачи для: {errors}"
                }
        except Exception as e:
            self.logger.error(f"Ошибка массовой рассылки задач синхронизации: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_tenant(self, tenant_id: int, pull_from_github: bool = True) -> Dict[str, Any]:
        """
        Синхронизация одного тенанта (все блоки: bot + scenarios + storage)
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id не указан"
                    }
                }
            
            # Синхронизируем все блоки
            return await self.block_sync_executor.sync_blocks(
                tenant_id,
                {"bot": True, "scenarios": True, "storage": True, "config": True},
                pull_from_github=pull_from_github
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации тенанта {tenant_id}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_public_tenants(self) -> Dict[str, Any]:
        """
        Синхронизация публичных тенантов из GitHub с защитой от параллельных запусков
        """
        
        
        if self._sync_in_progress:
            self.logger.warning("Синхронизация уже выполняется, пропускаем")
            return {"result": "success"}
        
        try:
            self._sync_in_progress = True
            
            # Используем умную синхронизацию через GitHub API
            # Если SHA нет - она автоматически сделает полную синхронизацию
            sync_result = await self._sync_public_tenants_incremental()          
            if sync_result.get("result") == "success":
                response_data = sync_result.get("response_data", {})
                updated_count = response_data.get("updated_tenants", 0)
                if updated_count > 0:
                    self.logger.info(f"Синхронизировано {updated_count} тенантов")
            elif sync_result.get("result") == "partial_success":
                self.logger.warning("Синхронизация завершена с частичными ошибками")
            else:
                # Для временных ошибок подключения (DNS, сеть) логируем как warning, не error
                error_obj = sync_result.get('error', {})
                error_msg = error_obj.get('message', '') if isinstance(error_obj, dict) else str(error_obj)
                if 'Не удалось получить текущий коммит' in error_msg or 'Не удалось определить изменения через API' in error_msg:
                    # Это временная проблема с сетью/GitHub API - не критично
                    # Детальная ошибка уже залогирована на нижнем уровне
                    pass  # Не логируем повторно, warning уже был на среднем уровне
                else:
                    # Другие ошибки логируем как error
                    self.logger.error(f"Ошибка синхронизации тенантов: {error_msg}")
            
            return sync_result
                
        except Exception:
            raise
        finally:
            self._sync_in_progress = False

    async def _sync_public_tenants_incremental(self) -> Dict[str, Any]:
        """
        Выполняет инкрементальную синхронизацию: определяет изменения через GitHub API и синхронизирует только измененные тенанты
        """
        try:
            # 1. Определяем измененные тенанты через GitHub Compare API
            changed_result = await self.smart_github_sync.get_changed_tenants()

            if changed_result.get("result") != "success":
                # Если не удалось определить изменения - просто пропускаем
                self.logger.warning("Не удалось определить изменения через API, пропускаем синхронизацию")
                error_obj = changed_result.get("error", {})
                if isinstance(error_obj, dict):
                    return {
                        "result": "error",
                        "error": error_obj
                    }
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": str(error_obj) if error_obj else "Не удалось определить изменения через API"
                    }
                }
            
            response_data = changed_result.get("response_data", {})
            current_sha = response_data.get("current_sha")
            changed_tenants_data = response_data.get("changed_tenants", {})
            sync_all = response_data.get("sync_all", False)  # Явный флаг полной синхронизации
            has_changes = response_data.get("has_changes", False)
            
            # 2. Если изменений нет и это не первая синхронизация - возвращаем успех
            if not has_changes and not sync_all:
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # 3. Обработка первой синхронизации (sync_all = True)
            if sync_all:
                return await self._sync_all_public_tenants(current_sha)
            
            # 4. Обновляем файлы из GitHub (только измененные тенанты)
            changed_tenant_ids = list(changed_tenants_data.keys())
            
            sync_files_result = await self.smart_github_sync.sync_changed_tenants(
                changed_tenant_ids=changed_tenant_ids, 
                current_sha=current_sha
            )
            
            if sync_files_result.get("result") != "success":
                return sync_files_result
            
            sync_response_data = sync_files_result.get("response_data", {})
            updated_files_count = sync_response_data.get("updated_tenants", 0)
            
            # 5. Если нет измененных тенантов для синхронизации - завершаем
            if updated_files_count == 0:
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # 6. Синхронизируем только измененные блоки для каждого тенанта
            return await self.sync_changed_blocks(changed_tenants_data)
                
        except Exception as e:
            self.logger.error(f"Ошибка умной синхронизации: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_changed_blocks(self, changed_tenants_data: Dict[int, Dict[str, bool]]) -> Dict[str, Any]:
        """
        Синхронизирует только измененные блоки для указанных тенантов с БД
        Оптимизация: если изменились только сценарии - не перезапускаем пуллинг
        """
        try:
            errors: list[int] = []
            for tenant_id, blocks in changed_tenants_data.items():
                res = await self.task_manager.submit_task(
                    task_id=f"sync_changed_tenant_{tenant_id}",
                    coro=(lambda t=tenant_id, b=blocks: self.block_sync_executor.sync_blocks(
                        t, b, pull_from_github=False
                    )),
                    fire_and_forget=True
                )
                if res.get("result") != "success":
                    self.logger.error(f"[Tenant-{tenant_id}] Не удалось отправить задачу синхронизации: {res.get('error')}")
                    errors.append(tenant_id)

            if not errors:
                return {"result": "success"}
            else:
                return {"result": "partial_success", "error": f"Не отправлены задачи для: {errors}"}
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации конкретных тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def _sync_all_public_tenants(self, current_sha: str) -> Dict[str, Any]:
        """
        Полная синхронизация всех публичных тенантов (для первой синхронизации)
        """
        try:
            # 1. Обновляем все публичные тенанты из GitHub (клонируем и копируем)
            self.logger.info("Первая синхронизация - обновление всех публичных тенантов из GitHub...")
            updated_files_count = await self.github_sync.clone_and_copy_tenants(sync_all=True)
            
            if updated_files_count == 0:
                self.logger.info("Нет публичных тенантов для синхронизации")
                # Обновляем SHA даже если нечего обновлять
                self.smart_github_sync.update_processed_sha(current_sha)
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # Обновляем SHA в памяти после успешной синхронизации
            self.smart_github_sync.update_processed_sha(current_sha)
            
            # 2. Получаем список всех публичных тенантов из локальной папки
            # Папка уже создана при инициализации, проверка не нужна
            
            # Собираем список ID всех публичных тенантов
            public_tenant_ids = []
            max_system_id = self.max_system_tenant_id
            
            for tenant_dir in self.tenants_path.iterdir():
                if tenant_dir.is_dir() and tenant_dir.name.startswith('tenant_'):
                    try:
                        tenant_id = int(tenant_dir.name.replace('tenant_', ''))
                        # Фильтруем только публичные тенанты
                        if tenant_id > max_system_id:
                            public_tenant_ids.append(tenant_id)
                    except ValueError:
                        continue
            
            if not public_tenant_ids:
                self.logger.info("Нет публичных тенантов для синхронизации")
                return {
                    "result": "success",
                    "response_data": {
                        "updated_tenants": 0
                    }
                }
            
            # 3. Синхронизируем все публичные тенанты с БД (асинхронно — fire_and_forget)
            self.logger.info(f"Запускаем синхронизацию {len(public_tenant_ids)} публичных тенантов в фоне...")
            errors = []
            for tenant_id in public_tenant_ids:
                blocks = {"bot": True, "scenarios": True, "storage": True, "config": True}
                res = await self.task_manager.submit_task(
                    task_id=f"sync_public_tenant_{tenant_id}",
                    coro=(lambda t=tenant_id, b=blocks: self.block_sync_executor.sync_blocks(
                        t, b, pull_from_github=False)),
                    fire_and_forget=True
                )
                if res.get("result") != "success":
                    self.logger.error(f"[Tenant-{tenant_id}] Не удалось отправить задачу sync: {res.get('error')}")
                    errors.append(tenant_id)

            if not errors:
                return {
                    "result": "success"
                }
            else:
                return {
                    "result": "partial_success",
                    "error": f"Не отправлены задачи для: {errors}"
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка полной синхронизации тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }


