"""
Smart GitHub Sync - умная синхронизация с GitHub репозиторием
- Определяет изменения через GitHub Compare API
- Использует базовые операции из base.py для клонирования и копирования
- Трехуровневая защита от системных тенантов
- Инкрементальная синхронизация только измененных тенантов
"""

from typing import Any, Dict, List, Optional

import aiohttp

from .base import GitHubSyncBase


class SmartGitHubSync(GitHubSyncBase):
    """
    Умная синхронизация публичных тенантов из GitHub репозитория
    Использует GitHub API для определения изменений и базовые операции для обновления
    """
    
    def __init__(self, logger, settings_manager):
        # Инициализируем базовый класс
        super().__init__(logger, settings_manager)
        
        # Последний обработанный SHA (хранится в памяти, обновляется после синхронизации)
        self.last_processed_sha: Optional[str] = None
        
        # ETag для оптимизации запросов (304 Not Modified)
        self.last_etag: Optional[str] = None
        
        # Извлекаем owner и repo из URL
        self.repo_owner, self.repo_name = self._parse_github_url()
    
    # === Публичные методы ===
    
    def update_processed_sha(self, sha: str) -> None:
        """Обновляет последний обработанный SHA"""
        self.last_processed_sha = sha
    
    async def get_changed_tenants(self) -> Dict[str, Any]:
        """
        Определяет какие тенанты изменились через GitHub Compare API
        С ЗАЩИТОЙ: автоматически фильтрует системные тенанты
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
            
            # Получаем текущий HEAD коммит через API (с оптимизацией ETag)
            current_sha = await self.get_latest_commit_sha()
            
            # Если current_sha None и есть last_processed_sha - это 304 Not Modified (нет изменений)
            if not current_sha:
                # Проверяем, есть ли сохраненный SHA (значит это не ошибка, а 304)
                if self.last_processed_sha:
                    # Нет изменений (304 Not Modified)
                    return {
                        "result": "success",
                        "response_data": {
                            "changed_tenants": {},
                            "sync_all": False,
                            "has_changes": False,
                            "current_sha": self.last_processed_sha
                        }
                    }
                else:
                    # Это ошибка - не удалось получить коммит и нет сохраненного
                    return {
                        "result": "error",
                        "error": {
                            "code": "API_ERROR",
                            "message": "Не удалось получить текущий коммит"
                        }
                    }
            
            # Используем SHA из памяти (или None если это первый запуск)
            last_sha = self.last_processed_sha
            
            # Если SHA совпадают - изменений нет
            if last_sha and last_sha == current_sha:
                return {
                    "result": "success",
                    "response_data": {
                        "changed_tenants": {},
                        "sync_all": False,
                        "has_changes": False,
                        "current_sha": current_sha
                    }
                }
            
            # Если это первый запуск (нет сохраненного SHA)
            if not last_sha:
                self.logger.info("Первая синхронизация - все публичные тенанты будут обновлены")
                # Возвращаем пустой словарь + флаг sync_all для явного указания полной синхронизации
                return {
                    "result": "success",
                    "response_data": {
                        "changed_tenants": {},  # Пустой словарь, т.к. список неизвестен до клонирования
                        "sync_all": True,  # Явный флаг - нужно обновить все публичные тенанты
                        "has_changes": True,
                        "current_sha": current_sha
                    }
                }
            
            # Используем Compare API для получения ВСЕХ измененных файлов
            compare_result = await self._compare_commits(last_sha, current_sha)
            
            if compare_result.get("result") != "success":
                return compare_result
            
            # Извлекаем tenant_id и блоки изменений из путей файлов с ЗАЩИТОЙ
            changed_tenants_data = self._extract_tenant_changes_with_protection(
                compare_result.get('files', [])
            )
            
            changed_tenants = sorted(changed_tenants_data.keys())
            
            return {
                "result": "success",
                "response_data": {
                    "changed_tenants": changed_tenants_data,  # {tenant_id: {"bot": bool, "scenarios": bool}}
                    "sync_all": False,  # Явно указываем что это не полная синхронизация
                    "has_changes": len(changed_tenants) > 0,
                    "current_sha": current_sha
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка определения измененных тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_changed_tenants(self, changed_tenant_ids: Optional[List[int]] = None, current_sha: str = None, sync_all: bool = False) -> Dict[str, Any]:
        """
        Синхронизирует измененные тенанты напрямую в config/tenant/
        Использует базовые операции из GitHubSyncBase
        С ЗАЩИТОЙ: двойная проверка на системные тенанты
        """
        try:
            if not current_sha:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "current_sha обязателен"
                    }
                }
            
            # ЗАЩИТА УРОВЕНЬ 2: Фильтруем системные тенанты
            if sync_all:
                # Синхронизируем все публичные тенанты
                public_tenants = None
            elif changed_tenant_ids:
                # Фильтруем только публичные из переданного списка
                public_tenants = [
                    tenant_id for tenant_id in changed_tenant_ids
                    if tenant_id > self.max_system_tenant_id
                ]
                
                if len(public_tenants) < len(changed_tenant_ids):
                    blocked_count = len(changed_tenant_ids) - len(public_tenants)
                    self.logger.warning(
                        f"[SECURITY] Заблокировано {blocked_count} системных тенантов от синхронизации"
                    )
                
                if not public_tenants:
                    self.logger.info("Нет публичных тенантов для синхронизации")
                    # Обновляем SHA в памяти даже если нечего обновлять
                    self.update_processed_sha(current_sha)
                    return {
                        "result": "success",
                        "response_data": {
                            "updated_tenants": 0
                        }
                    }
            else:
                # Не переданы ни тенанты, ни флаг sync_all
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указаны тенанты для синхронизации или sync_all=False"
                    }
                }
            
            # Используем базовый метод для клонирования и копирования
            if sync_all:
                updated_count = await self.clone_and_copy_tenants(sync_all=True)
            else:
                updated_count = await self.clone_and_copy_tenants(tenant_ids=public_tenants)
            
            # Обновляем SHA в памяти после успешной синхронизации
            self.update_processed_sha(current_sha)
            
            return {
                "result": "success",
                "response_data": {
                    "updated_tenants": updated_count
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации измененных тенантов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    # === Внутренние методы ===
    
    def _parse_github_url(self) -> tuple:
        """Извлекает owner и repo из GitHub URL"""
        try:
            # Формат: https://github.com/owner/repo или https://github.com/owner/repo.git
            url = self.github_url.replace('.git', '').rstrip('/')
            parts = url.split('/')
            if len(parts) >= 2:
                owner = parts[-2]
                repo = parts[-1]
                return owner, repo
            return None, None
        except Exception as e:
            self.logger.error(f"Ошибка парсинга GitHub URL: {e}")
            return None, None
    
    def _validate_github_config(self) -> Optional[str]:
        """
        Проверяет корректность конфигурации GitHub (расширенная проверка для API)
        """
        # Используем базовую проверку
        base_error = super()._validate_github_config()
        if base_error:
            return base_error
        
        # Дополнительная проверка для API
        if not self.repo_owner or not self.repo_name:
            return "Не удалось извлечь owner и repo из GitHub URL"
        
        return None
    
    async def get_latest_commit_sha(self) -> Optional[str]:
        """
        Получает SHA последнего коммита через GitHub Events API с оптимизацией ETag.
        Использует ETag для минимизации трафика: если изменений нет, получает 304 Not Modified.
        """
        try:
            # Используем Events API - более эффективен для отслеживания изменений
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/events"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # Добавляем ETag для проверки без загрузки данных
            if self.last_etag:
                headers['If-None-Match'] = self.last_etag
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={"per_page": 5}) as response:
                    # Если нет изменений - возвращаем None (не нужно обрабатывать)
                    if response.status == 304:
                        # Нет изменений, возвращаем текущий SHA (если есть) для сравнения
                        return self.last_processed_sha
                    
                    if response.status == 200:
                        # Сохраняем ETag для следующего запроса
                        etag = response.headers.get('ETag')
                        if etag:
                            self.last_etag = etag
                        
                        events = await response.json()
                        
                        # Ищем последний PushEvent (push в репозиторий)
                        for event in events:
                            if event.get('type') == 'PushEvent':
                                payload = event.get('payload', {})
                                commits = payload.get('commits', [])
                                if commits:
                                    # Возвращаем SHA последнего коммита из push
                                    return commits[-1].get('sha')
                        
                        # Если нет PushEvent в последних событиях, используем Commits API как fallback
                        return await self._get_sha_via_commits_api()
                    
                    elif response.status == 404:
                        self.logger.error(f"Репозиторий не найден: {self.repo_owner}/{self.repo_name}")
                    else:
                        self.logger.error(f"Ошибка получения событий: HTTP {response.status}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка получения последнего коммита: {e}")
            return None
    
    async def _get_sha_via_commits_api(self) -> Optional[str]:
        """Fallback метод: получает SHA через Commits API (если Events API не вернул PushEvent)"""
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/commits"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={"per_page": 1}) as response:
                    if response.status == 200:
                        commits = await response.json()
                        if commits and len(commits) > 0:
                            return commits[0].get("sha")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка получения коммита через Commits API: {e}")
            return None
    
    async def _compare_commits(self, base_sha: str, head_sha: str) -> Dict[str, Any]:
        """
        Сравнивает два коммита через GitHub Compare API
        Возвращает список всех измененных файлов между коммитами
        """
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/compare/{base_sha}...{head_sha}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        compare_data = await response.json()
                        files = compare_data.get("files", [])
                        
                        return {
                            "result": "success",
                            "files": files
                        }
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Ошибка Compare API: HTTP {response.status}, {error_text}")
                        return {
                            "result": "error",
                            "error": {
                                "code": "API_ERROR",
                                "message": f"Ошибка Compare API: HTTP {response.status}"
                            }
                        }
            
        except Exception as e:
            self.logger.error(f"Ошибка сравнения коммитов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    def _extract_tenant_changes_with_protection(self, files: List[Dict[str, Any]]) -> Dict[int, Dict[str, bool]]:
        """
        Извлекает tenant_id и информацию об измененных блоках из путей файлов с ЗАЩИТОЙ от системных тенантов
        
        ЗАЩИТА УРОВЕНЬ 1: Фильтруем системные тенанты на этапе извлечения
        """
        changed_tenants: Dict[int, Dict[str, bool]] = {}
        
        for file_info in files:
            file_path = file_info.get('filename', '')
            
            # Извлекаем tenant_id из пути
            tenant_id = self._extract_tenant_id_from_path(file_path)
            
            if tenant_id is None:
                continue  # Не является файлом тенанта
            
            # ЗАЩИТА: Фильтруем системные тенанты
            if tenant_id <= self.max_system_tenant_id:
                self.logger.warning(
                    f"[SECURITY] Обнаружен системный тенант {tenant_id} в GitHub репозитории - игнорируем"
                )
                continue  # НЕ добавляем в список
            
            # Определяем какие блоки изменились
            if tenant_id not in changed_tenants:
                changed_tenants[tenant_id] = {"bot": False, "scenarios": False, "storage": False}
            
            # Определяем тип изменения по пути
            block_type = self._determine_block_type(file_path)
            if block_type == "bot":
                changed_tenants[tenant_id]["bot"] = True
            elif block_type == "scenarios":
                changed_tenants[tenant_id]["scenarios"] = True
            elif block_type == "storage":
                changed_tenants[tenant_id]["storage"] = True
        
        return changed_tenants
    
    def _determine_block_type(self, file_path: str) -> Optional[str]:
        """
        Определяет тип блока по пути файла
        """
        # Путь имеет формат: tenant/tenant_XXX/...
        if not file_path.startswith('tenant/tenant_'):
            return None
        
        parts = file_path.split('/')
        if len(parts) < 3:
            return None
        
        # Строгая проверка:
        # - bot: только точное изменение файла tg_bot.yaml в корне тенанта
        # - scenarios: любые изменения внутри папки scenarios
        # - storage: любые изменения внутри папки storage
        if parts[2] == "tg_bot.yaml":
            return "bot"
        
        if parts[2] == "scenarios" and len(parts) > 3:
            return "scenarios"
        
        if parts[2] == "storage" and len(parts) > 3:
            return "storage"
        
        return None
    
    def _extract_tenant_id_from_path(self, file_path: str) -> Optional[int]:
        """
        Извлекает tenant_id из пути файла
        """
        try:
            # Путь имеет формат: tenant/tenant_XXX/...
            if not file_path.startswith('tenant/tenant_'):
                return None
            
            # Извлекаем часть tenant_XXX
            parts = file_path.split('/')
            if len(parts) < 2:
                return None
            
            tenant_folder = parts[1]  # tenant_XXX
            if not tenant_folder.startswith('tenant_'):
                return None
            
            # Извлекаем ID
            tenant_id_str = tenant_folder.replace('tenant_', '')
            tenant_id = int(tenant_id_str)
            return tenant_id
            
        except (ValueError, IndexError):
            return None

