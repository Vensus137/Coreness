"""
Модуль для работы с Git репозиториями
Фасад, использующий специализированные модули
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from modules.deploy.deploy_utils import TempDirectoryManager, VersionManager
from modules.deploy.file_manager import FileCopier, RepositoryCleaner
from modules.deploy.git_operations import BranchManager, CommitManager, GitRepository
from modules.deploy.github_api import MergeRequestManager


class GitHandler:
    """Класс для работы с Git репозиториями (фасад)"""
    
    def __init__(self, config: dict, logger, project_root: Optional[Path] = None):
        self.config = config
        self.logger = logger
        
        # Получаем project_root из базового модуля или используем переданный
        if project_root is None:
            from modules.base import get_base
            self.project_root = get_base().get_project_root()
        else:
            self.project_root = project_root
        
        # Инициализируем специализированные модули
        self.temp_manager = TempDirectoryManager(config, logger)
        self.git_repo = GitRepository(config, logger)
        self.branch_manager = BranchManager(logger)
        self.commit_manager = CommitManager(config, logger)
        self.mr_manager = MergeRequestManager(config, logger)
        self.file_copier = FileCopier(self.project_root, logger)
        self.repo_cleaner = RepositoryCleaner(logger)
        # VersionManager только для validate_version_format (статический метод)
        self.version_manager = VersionManager
        
        # Сохраняем ссылку на temp_dir для cleanup
        self.temp_dir = None
    
    def deploy_to_repository(self, repo_name: str, repo_config: Dict, files_to_deploy: List[str], 
                           branch_name: str, version: str, date: str, force: bool = False, 
                           deployment_config: Dict = None) -> bool:
        """Деплой в репозиторий"""
        repo = None  # Инициализируем для finally блока
        try:
            # Устанавливаем безопасное значение по умолчанию
            if deployment_config is None:
                deployment_config = {}
            
            # 1. ПРЕДВАРИТЕЛЬНАЯ ПРОВЕРКА ВЕТКИ (до клонирования)
            if not force:
                print(f"🔍 Проверка существования ветки {branch_name}...")
                branch_exists = self.mr_manager.check_branch_exists_via_api(repo_config, branch_name)
                
                if branch_exists:
                    print(f"\n{'='*60}")
                    print(f"🔍 ОБНАРУЖЕНА СУЩЕСТВУЮЩАЯ ВЕТКА")
                    print(f"{'='*60}")
                    print(f"🌿 Ветка: {branch_name}")
                    print(f"📊 Статус: В REMOTE")
                    
                    # Показываем информацию о существующем MR
                    existing_mr = self.mr_manager.check_existing(repo_config, branch_name)
                    if existing_mr['exists']:
                        print(f"📋 MR: {existing_mr['url']}")
                        print(f"📝 Статус MR: {existing_mr['status'].upper()}")
                        if existing_mr['merged']:
                            print(f"✅ MR был мержен!")
                        elif existing_mr['status'] == 'closed':
                            print(f"❌ MR был закрыт!")
                        elif existing_mr['status'] == 'open':
                            print(f"⚠️ MR открыт и ожидает ревью!")
                    
                    print(f"\n💡 Рекомендуется:")
                    print(f"   1. Создать новую версию (3.0 -> 3.0.1)")
                    print(f"   2. Принудительно перезаписать (--force)")
                    print(f"   3. Отменить деплой")
                    
                    choice = input(f"\nВыберите действие:\n"
                                  f"1. Создать новую версию\n"
                                  f"2. Принудительно перезаписать (--force)\n"
                                  f"3. Отменить деплой\n"
                                  f"Выбор (1/2/3): ").strip()
                    
                    if choice == "1":
                        print(f"💡 Введите новую версию вручную")
                        version, branch_name = self._handle_manual_version_input(repo_config, version)
                        if not version:
                            return False
                    
                    elif choice == "2":
                        print(f"⚠️ Переключаемся в режим --force")
                        force = True
                    elif choice == "3":
                        print("❌ Деплой отменен")
                        sys.exit(0)
                    else:
                        print("❌ Неверный выбор. Отменяем деплой")
                        sys.exit(0)
                    
                    print(f"{'='*60}\n")
            
            # 2. Создание временной директории
            self.temp_dir = self.temp_manager.create()
            temp_dir = self.temp_dir
            
            # 3. Клонирование репозитория
            repo_path = os.path.join(temp_dir, repo_name)
            token = self.mr_manager.api_client.get_token(repo_config)
            repo = self.git_repo.clone(repo_config, repo_path, token)
            if not repo:
                return False
            
            # 4. Создание и переключение на ветку
            if not self.branch_manager.create(repo, branch_name, force):
                return False
            
            # 5. ОЧИСТКА РЕПОЗИТОРИЯ (зависит от режима синхронизации)
            full_sync = deployment_config.get('full_sync', True)
            if full_sync:
                # ПОЛНАЯ ОЧИСТКА: удаляем все файлы кроме .git
                print("🗑️ Полная очистка репозитория...")
                self.logger.info("Полная очистка репозитория (режим: full_sync=true)")
                if not self.repo_cleaner.clean_completely(repo):
                    return False
            else:
                # АДДИТИВНЫЙ РЕЖИМ: только добавляем/обновляем, остальное не трогаем
                print("📝 Аддитивная синхронизация (только обновление)...")
                self.logger.info("Аддитивная синхронизация репозитория (режим: full_sync=false)")
                self.repo_cleaner.clean_synced_directories(repo, files_to_deploy)
            
            # 6. Копирование новых файлов
            print("📁 Копирование файлов...")
            self.logger.info("Копирование файлов")
            copied_files = self.file_copier.copy_files(repo, files_to_deploy, deployment_config)
            if not copied_files:
                self.logger.error("Не удалось скопировать файлы")
                return False
            
            # 7. Проверка изменений ДО коммита
            has_untracked = len(repo.untracked_files) > 0
            has_modified = repo.is_dirty()
            
            # 8. Создание коммита
            if not self.commit_manager.commit(repo, version, date, repo_name):
                return False
            
            # 9. Отправка ветки (только если были изменения)
            if has_untracked or has_modified:
                if not self.commit_manager.push(repo, branch_name, force):
                    print(f"\n{'='*60}")
                    print(f"❌ ОШИБКА ОТПРАВКИ ВЕТКИ")
                    print(f"{'='*60}")
                    print(f"🔗 Ветка: {branch_name}")
                    print(f"📝 Причина: Не удалось отправить ветку в репозиторий")
                    print(f"💡 Проверьте права токена и доступность репозитория")
                    print(f"{'='*60}")
                    return False
                
                # 10. Создание Merge Request
                if self.config['deploy_settings']['create_mr']:
                    if not self.mr_manager.create(repo_config, branch_name, version, date, repo_name):
                        return False
                    
                    # 11. Создание тега версии (если включено в конфиге)
                    create_tag = deployment_config.get('create_tag', False)
                    if create_tag:
                        self.logger.info(f"Создание тега версии {version} для {repo_name}...")
                        if not self.mr_manager.create_tag(repo_config, version, branch_name):
                            # Не критично, продолжаем даже если тег не создался
                            self.logger.warning(f"Не удалось создать тег версии {version}, продолжаем деплой")
            else:
                print("ℹ️ Ветка не отправлена - нет изменений")
                print("ℹ️ MR не создан - нет изменений")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка деплоя в репозиторий: {e}")
            return False
            
        finally:
            # Явно закрываем repo для освобождения файловых дескрипторов (критично для Windows)
            if repo is not None:
                try:
                    repo.close()
                    self.logger.debug("Объект Repo закрыт")
                except Exception as e:
                    self.logger.debug(f"Ошибка при закрытии Repo: {e}")
            
            # Принудительная сборка мусора для освобождения ресурсов
            import gc
            gc.collect()
            
            # Небольшая задержка для Windows (дать время закрыться дескрипторам)
            import time
            time.sleep(0.5)
            
            # Очищаем временную директорию
            self.temp_manager.cleanup()
    
    def _handle_manual_version_input(self, repo_config: Dict, current_version: str) -> Optional[tuple]:
        """Обрабатывает ручной ввод версии пользователем"""
        while True:
            manual_version = input(f"Введите версию (например, 3.0.5): ").strip()
            if self.version_manager.validate_version_format(manual_version):
                manual_branch_name = f"{self.config['git_settings']['branch_prefix']}{manual_version}"
                manual_branch_exists = self.mr_manager.check_branch_exists_via_api(repo_config, manual_branch_name)
                
                if not manual_branch_exists:
                    print(f"✅ Версия {manual_version} свободна!")
                    
                    # Дополнительно проверяем, нет ли уже MR для этой версии
                    manual_mr_exists = self.mr_manager.check_existing(repo_config, manual_branch_name)
                    if manual_mr_exists['exists']:
                        print(f"⚠️ Для версии {manual_version} уже существует MR!")
                        print(f"📋 MR: {manual_mr_exists['url']}")
                        print(f"📝 Статус: {manual_mr_exists['status'].upper()}")
                        print(f"💡 Попробуйте другую версию")
                        continue
                    
                    return (manual_version, manual_branch_name)
                else:
                    print(f"⚠️ Версия {manual_version} тоже занята, попробуйте другую")
            else:
                print("❌ Неверный формат версии. Используйте формат X.Y.Z")
    
    def cleanup(self):
        """Очищает временные файлы"""
        self.temp_manager.cleanup()
