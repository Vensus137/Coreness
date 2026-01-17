"""
GitHub Sync Base - базовые операции синхронизации с GitHub
Клонирование репозитория и копирование тенантов
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import Repo


class GitHubSyncBase:
    """
    Базовый класс для синхронизации публичных тенантов из GitHub репозитория
    Содержит операции клонирования и копирования
    """
    
    def __init__(self, logger, settings_manager):
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Получаем настройки из tenant_hub
        plugin_settings = self.settings_manager.get_plugin_settings("tenant_hub")
        
        # Настройки GitHub
        self.github_url = plugin_settings.get('github_url', '')
        self.github_token = plugin_settings.get('github_token', '')
        
        # Получаем глобальные настройки
        global_settings = self.settings_manager.get_global_settings()
        
        # Граница между системными и публичными тенантами
        self.max_system_tenant_id = global_settings.get('max_system_tenant_id', 100)
        
        # Путь к тенантам
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = project_root / tenants_config_path
    
    # === Публичные методы ===
    
    async def pull_tenant(self, tenant_id: int) -> Dict[str, Any]:
        """
        Скачивает конкретный тенант из GitHub репозитория
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
            
            # Проверяем конфигурацию GitHub
            validation_error = self._validate_github_config()
            if validation_error:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": validation_error
                    }
                }
            
            # Проверяем что это публичный тенант (не системный)
            if tenant_id <= self.max_system_tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": f"Тенант {tenant_id} является системным (ID <= {self.max_system_tenant_id}). Синхронизация запрещена."
                    }
                }
            
            tenant_name = f"tenant_{tenant_id}"
            tenant_local_path = self.tenants_path / tenant_name
            
            # Удаляем старую папку тенанта
            if tenant_local_path.exists():
                shutil.rmtree(tenant_local_path)
            
            # Клонируем репозиторий и копируем нужную папку
            success = await self._clone_and_copy_tenant(tenant_id, tenant_local_path)
            if not success:
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": f"Не удалось скачать тенант {tenant_id} из GitHub"
                    }
                }
            
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации тенанта {tenant_id}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def pull_all(self) -> Dict[str, Any]:
        """
        Скачивает все публичные тенанты из GitHub репозитория
        """
        try:
            # Проверяем конфигурацию GitHub
            validation_error = self._validate_github_config()
            if validation_error:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": validation_error
                    }
                }
            
            # Удаляем все публичные тенанты перед загрузкой новых
            self._delete_all_public_tenants()
            
            # Клонируем репозиторий и копируем все публичные тенанты
            updated_count = await self.clone_and_copy_tenants(sync_all=True)
            if updated_count == 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": "Не удалось скачать репозиторий из GitHub"
                    }
                }
            
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации всех публичных тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    # === Методы для переиспользования ===
    
    async def clone_and_copy_tenants(self, tenant_ids: Optional[List[int]] = None, sync_all: bool = False) -> int:
        """
        Клонирует репозиторий и копирует указанные тенанты
        """
        try:
            # Формируем URL с токеном
            auth_url = self._get_auth_url()
            
            # Создаем временную папку для клонирования
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                repo_path = temp_path / "repo"
                
                # Клонируем репозиторий (только последний коммит для скорости)
                self.logger.info("Клонирование репозитория...")
                Repo.clone_from(auth_url, str(repo_path), depth=1)
                
                # Путь к папке tenant в клонированном репозитории
                tenant_repo_path = repo_path / "tenant"
                
                if not tenant_repo_path.exists():
                    self.logger.warning("Папка tenant не найдена в репозитории")
                    return 0
                
                # Определяем какие тенанты обновлять
                if sync_all:
                    # Обновляем все публичные тенанты из репозитория
                    tenant_ids_to_sync = []
                    for tenant_folder in tenant_repo_path.iterdir():
                        if tenant_folder.is_dir() and tenant_folder.name.startswith("tenant_"):
                            try:
                                tenant_id_str = tenant_folder.name.replace("tenant_", "")
                                tenant_id = int(tenant_id_str)
                                # Фильтруем только публичные (в репозитории должны быть только они, но на всякий случай)
                                if tenant_id > self.max_system_tenant_id:
                                    tenant_ids_to_sync.append(tenant_id)
                            except ValueError:
                                continue
                elif tenant_ids:
                    # Используем переданный список
                    tenant_ids_to_sync = tenant_ids
                else:
                    # Нечего синхронизировать
                    return 0
                
                # Копируем каждый тенант напрямую в config/tenant/
                updated_count = 0
                for tenant_id in tenant_ids_to_sync:
                    tenant_name = f"tenant_{tenant_id}"
                    source = tenant_repo_path / tenant_name
                    destination = self.tenants_path / tenant_name
                    
                    if not source.exists():
                        self.logger.warning(f"[Tenant-{tenant_id}] Не найден в репозитории")
                        continue
                    
                    try:
                        # Удаляем старую версию если есть
                        if destination.exists():
                            shutil.rmtree(destination)
                        
                        # Копируем напрямую из временного репозитория
                        shutil.copytree(source, destination)
                        
                        self.logger.info(f"[Tenant-{tenant_id}] Обновлен")
                        updated_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"[Tenant-{tenant_id}] Ошибка копирования: {e}")
                
                return updated_count
                
        except Exception as e:
            self.logger.error(f"Ошибка клонирования и копирования тенантов: {e}")
            return 0
    
    # === Внутренние методы ===
    
    def _validate_github_config(self) -> Optional[str]:
        """
        Проверяет корректность конфигурации GitHub
        Возвращает None если всё ОК, или строку с описанием ошибки
        """
        # Проверяем наличие URL и токена
        if not self.github_url or not self.github_token:
            return "GitHub не настроен или токен отсутствует"
        
        # Проверяем что URL и токен - строки
        if not isinstance(self.github_url, str):
            self.logger.error(f"GitHub URL должен быть строкой, получен: {type(self.github_url)}")
            return "GitHub URL имеет неверный тип"
        
        if not isinstance(self.github_token, str):
            self.logger.error(f"GitHub token должен быть строкой, получен: {type(self.github_token)}")
            return "GitHub token имеет неверный тип"
        
        return None
    
    def _get_auth_url(self) -> str:
        """Формирует URL с токеном для аутентификации"""
        return self.github_url.replace(
            "https://github.com/",
            f"https://{self.github_token}@github.com/"
        )
    
    def _delete_all_public_tenants(self):
        """
        Удаляет все публичные тенанты из локальной папки
        """
        if not self.tenants_path.exists():
            return
        
        deleted_count = 0
        for tenant_folder in self.tenants_path.iterdir():
            if tenant_folder.is_dir() and tenant_folder.name.startswith("tenant_"):
                try:
                    tenant_id_str = tenant_folder.name.replace("tenant_", "")
                    tenant_id = int(tenant_id_str)
                    
                    # Проверяем что это публичный тенант (не системный)
                    if tenant_id > self.max_system_tenant_id:
                        shutil.rmtree(tenant_folder)
                        deleted_count += 1
                        
                except ValueError:
                    self.logger.warning(f"Неверное название папки тенанта: {tenant_folder.name}")
                    continue
        
        if deleted_count > 0:
            self.logger.info(f"Удалено {deleted_count} публичных тенантов перед загрузкой")
    
    async def _clone_and_copy_tenant(self, tenant_id: int, local_path: Path) -> bool:
        """
        Клонирует репозиторий и копирует нужную папку тенанта
        """
        try:
            tenant_name = f"tenant_{tenant_id}"
            
            # Формируем URL с токеном
            auth_url = self._get_auth_url()
            
            # Создаем временную папку для клонирования
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                repo_path = temp_path / "repo"
                
                # Клонируем репозиторий (только последний коммит для скорости)
                Repo.clone_from(auth_url, repo_path, depth=1)
                
                # Проверяем существование папки тенанта в репозитории
                tenant_repo_path = repo_path / "tenant" / tenant_name
                if not tenant_repo_path.exists():
                    self.logger.warning(f"Тенант {tenant_name} не найден в репозитории")
                    return False
                
                # Копируем папку тенанта в локальную директорию
                shutil.copytree(tenant_repo_path, local_path)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка клонирования и копирования тенанта {tenant_id}: {e}")
            return False
    

