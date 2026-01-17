"""
Модуль для обновления файлов на сервере
Клонирование репозитория и замена файлов с использованием системы пресетов
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from git import Repo

# Импортируем FileFilter для унифицированной фильтрации
from modules.deploy.file_filter import FileFilter


class ServerUpdater:
    """Класс для обновления файлов на сервере"""
    
    def __init__(self, config: dict, project_root: Path, logger):
        """Инициализация обновлятора сервера"""
        self.config = config
        self.project_root = project_root
        self.logger = logger
        self.temp_dir = None
        
        # Настройки из конфига
        self.server_config = config.get('server_update', {})
        self.deployment_config = self.server_config.get('deployment', {})
        self.update_settings = self.server_config.get('settings', {})
        
        # Инициализируем FileFilter для унифицированной фильтрации
        self.file_filter = FileFilter(config, logger, project_root)
        
        # Список файлов будет получен из клонированного репозитория, не из текущего проекта
        self.files_to_update = []
        
        # Настройки процесса обновления
        self.non_critical_paths = self.update_settings.get('non_critical_paths', [])
        self.backup_dir = self.update_settings.get('backup_dir', '.core_update_backup')
    
    def _get_files_to_update(self, repo_path: Path) -> List[str]:
        """Получает список файлов для обновления через FileFilter из клонированного репозитория"""
        try:
            # Создаем временный FileFilter с путем к клонированному репозиторию
            repo_file_filter = FileFilter(self.config, self.logger, repo_path)
            
            # Используем FileFilter с конфигурацией обновления сервера
            files = repo_file_filter.get_files_for_repo("server_update", self.deployment_config)
            
            if not files:
                self.logger.warning("Не найдено файлов для обновления. Проверьте конфигурацию deployment в server_update")
                # Fallback на пустой список - будет ошибка, но это лучше чем обновить все
                return []
            
            self.logger.info(f"Определено {len(files)} файлов для обновления через систему пресетов")
            return files
            
        except Exception as e:
            self.logger.error(f"Ошибка получения списка файлов для обновления: {e}")
            return []
    
    def clone_repository(self, environment: str, branch: Optional[str] = None) -> Optional[Path]:
        """Клонирует репозиторий во временную директорию с нужной ветки"""
        try:
            # Получаем настройки репозитория
            repo_config = self.server_config.get('repository', {})
            if not repo_config:
                self.logger.error("Конфигурация репозитория не найдена")
                return None
            
            repo_url = repo_config.get('url')
            if not repo_url:
                self.logger.error("URL репозитория не указан")
                return None
            
            # Определяем ветку
            if not branch:
                branches = repo_config.get('branches', {})
                branch = branches.get(environment)
                if not branch:
                    self.logger.error(f"Ветка для окружения {environment} не найдена")
                    return None
            
            # Получаем токен (уже разрешенный из переменных окружения при загрузке конфига)
            token = repo_config.get('token', '').strip()
            
            # Проверяем наличие токена
            if not token:
                self.logger.error("Токен не установлен. Установите переменную окружения GITHUB_TOKEN")
                self.logger.error("Пример: export GITHUB_TOKEN='your_token_here'")
                return None
            
            # Создаем временную директорию
            self.temp_dir = tempfile.mkdtemp(prefix="server_update_")
            repo_path = Path(self.temp_dir) / "repo"
            
            self.logger.info(f"Клонирование репозитория {repo_url} (ветка: {branch})")
            
            # Формируем URL с токеном для GitHub
            if "github.com" in repo_url:
                # Для GitHub используем правильный формат с токеном
                # Формат: https://x-access-token:{token}@github.com/... или https://{token}@github.com/...
                if repo_url.startswith("https://"):
                    auth_url = repo_url.replace("https://", f"https://x-access-token:{token}@")
                else:
                    auth_url = repo_url
            else:
                # Для других репозиториев используем стандартный формат
                auth_url = repo_url.replace("https://", f"https://{token}@") if token else repo_url
            
            # Клонируем репозиторий
            repo = Repo.clone_from(auth_url, str(repo_path))
            
            # Переключаемся на нужную ветку
            repo.git.checkout(branch)
            
            self.logger.info(f"Репозиторий успешно клонирован в {repo_path}")
            return repo_path
            
        except Exception as e:
            self.logger.error(f"Ошибка клонирования репозитория: {e}")
            return None
    
    def checkout_to_tag(self, repo_path: Path, version: str) -> bool:
        """
        Переключается на коммит с указанным тегом версии
        
        Примечание: Если тег был удален в GitHub, он не будет найден.
        Это нормальное поведение - удаленные теги (например, бета-версии) недоступны для деплоя.
        """
        try:
            repo = Repo(str(repo_path))
            
            # Проверяем тег с префиксом 'v' и без
            tag_with_v = f"v{version}"
            tag_without_v = version
            
            # Ищем тег
            tag_name = None
            if tag_with_v in [tag.name for tag in repo.tags]:
                tag_name = tag_with_v
            elif tag_without_v in [tag.name for tag in repo.tags]:
                tag_name = tag_without_v
            
            if not tag_name:
                self.logger.error(f"Тег версии {version} не найден в репозитории")
                self.logger.info("💡 Тег мог быть удален в GitHub. Удаленные теги недоступны для деплоя.")
                return False
            
            # Переключаемся на коммит с тегом
            repo.git.checkout(tag_name)
            self.logger.info(f"Переключено на тег: {tag_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка переключения на тег {version}: {e}")
            return False
    
    def backup_files(self) -> Optional[str]:
        """Создает бэкап текущих файлов"""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.project_root / f"{self.backup_dir}_{timestamp}"
            
            self.logger.info(f"Создание бэкапа в {backup_path}")
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Копируем файлы из списка для обновления
            copied_count = 0
            for file_path in self.files_to_update:
                source_path = self.project_root / file_path
                
                if not source_path.exists():
                    # Пропускаем несуществующий файл
                    pass
                    continue
                
                dest_path = backup_path / file_path
                
                try:
                    if source_path.is_dir():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, dest_path)
                    
                    copied_count += 1
                    # Скопирован в бэкап
                    pass
                    
                except Exception as e:
                    # Для некритичных путей продолжаем
                    if self._is_non_critical(file_path):
                        self.logger.warning(f"Не удалось скопировать {file_path} в бэкап: {e}")
                        continue
                    else:
                        raise
            
            self.logger.info(f"Бэкап создан: {copied_count} файлов в {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа: {e}")
            return None
    
    def update_files(self, repo_path: Path) -> bool:
        """Обновляет файлы на сервере используя систему пресетов"""
        try:
            self.logger.info("Начало обновления файлов")
            
            # Получаем список файлов для обновления из клонированного репозитория
            self.files_to_update = self._get_files_to_update(repo_path)
            
            if not self.files_to_update:
                self.logger.error("Список файлов для обновления пуст. Проверьте конфигурацию.")
                return False
            
            # 1. Удаляем старые файлы из списка для обновления
            removed_count = 0
            for file_path in self.files_to_update:
                target_path = self.project_root / file_path
                
                if target_path.exists():
                    try:
                        if target_path.is_dir():
                            shutil.rmtree(target_path)
                        else:
                            target_path.unlink()
                        
                        removed_count += 1
                        # Удален
                        pass
                        
                    except Exception as e:
                        # Для некритичных путей продолжаем
                        if self._is_non_critical(file_path):
                            self.logger.warning(f"Не удалось удалить {file_path}: {e}")
                            continue
                        else:
                            raise
            
            self.logger.info(f"Удалено старых файлов: {removed_count}")
            
            # 2. Копируем новые файлы из репозитория
            copied_count = 0
            for file_path in self.files_to_update:
                source_path = repo_path / file_path
                target_path = self.project_root / file_path
                
                if not source_path.exists():
                    # Пропускаем несуществующий файл в репозитории
                    pass
                    continue
                
                try:
                    if source_path.is_dir():
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, target_path)
                    
                    copied_count += 1
                    # Скопирован
                    pass
                    
                except Exception as e:
                    # Для некритичных путей продолжаем
                    if self._is_non_critical(file_path):
                        self.logger.warning(f"Не удалось скопировать {file_path}: {e}")
                        continue
                    else:
                        raise
            
            self.logger.info(f"Скопировано новых файлов: {copied_count}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления файлов: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """Восстанавливает файлы из бэкапа"""
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                self.logger.error(f"Директория бэкапа не найдена: {backup_path}")
                return False
            
            self.logger.info(f"Восстановление из бэкапа: {backup_path}")
            
            # Восстанавливаем все файлы из бэкапа
            restored_count = 0
            for item in backup_dir.rglob('*'):
                if item.is_dir():
                    continue
                
                # Получаем относительный путь
                rel_path = item.relative_to(backup_dir)
                target_path = self.project_root / rel_path
                
                try:
                    # Удаляем существующий файл если есть
                    if target_path.exists():
                        if target_path.is_dir():
                            shutil.rmtree(target_path)
                        else:
                            target_path.unlink()
                    
                    # Копируем из бэкапа
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target_path)
                    
                    restored_count += 1
                    # Восстановлен
                    pass
                    
                except Exception as e:
                    self.logger.warning(f"Не удалось восстановить {rel_path}: {e}")
                    continue
            
            self.logger.info(f"Восстановлено элементов: {restored_count}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка восстановления из бэкапа: {e}")
            return False
    
    def cleanup(self):
        """Очищает временные файлы"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                # Временная директория удалена
                pass
            except Exception as e:
                self.logger.warning(f"Ошибка удаления временной директории: {e}")
    
    def _is_non_critical(self, path: str) -> bool:
        """Проверяет некритичность пути"""
        normalized_path = path.replace('\\', '/')
        
        for non_critical in self.non_critical_paths:
            normalized_non_critical = non_critical.replace('\\', '/')
            
            if normalized_path == normalized_non_critical:
                return True
            
            if normalized_path.startswith(normalized_non_critical + '/'):
                return True
        
        return False

