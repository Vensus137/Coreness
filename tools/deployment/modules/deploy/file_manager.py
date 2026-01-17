"""
Управление файлами: копирование и очистка репозитория
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from git import Repo


class FileCopier:
    """Копирование файлов в репозиторий"""
    
    def __init__(self, project_root: Path, logger):
        self.project_root = project_root
        self.logger = logger
    
    def copy_files(self, repo: Repo, files_to_deploy: List[str], deployment_config: Optional[Dict] = None) -> List[str]:
        """
        Копирует файлы в репозиторий с поддержкой подмены файлов
        
        Подмена файлов работает в двух режимах:
        1. Замена существующих файлов из files_to_deploy на файлы-источники
        2. Добавление новых файлов из file_replacements, которых нет в files_to_deploy
        """
        copied_files = []
        
        # Получаем настройки подмены файлов из конфига
        file_replacements = {}
        if deployment_config:
            file_replacements = deployment_config.get('file_replacements', {})
        
        # Обрабатываем файлы из files_to_deploy (с подменой или без)
        for file_path in files_to_deploy:
            try:
                # Проверяем, нужно ли подменить файл
                replacement_source = file_replacements.get(file_path)
                
                if replacement_source:
                    # Используем файл-источник для подмены
                    source_path = os.path.join(self.project_root, replacement_source)
                    self.logger.info(f"Подмена файла/директории {file_path} -> {replacement_source}")
                    
                    # Проверяем существование файла-источника
                    if not os.path.exists(source_path):
                        self.logger.warning(f"Файл-источник для подмены не найден: {source_path}, используем оригинальный файл")
                        source_path = os.path.join(self.project_root, file_path)
                else:
                    # Используем оригинальный файл
                    source_path = os.path.join(self.project_root, file_path)
                
                target_path = os.path.join(repo.working_dir, file_path)
                
                # Проверяем существование исходного файла/директории
                if not os.path.exists(source_path):
                    self.logger.warning(f"Исходный файл/директория не найден: {source_path}")
                    continue
                
                # Создаем директории если нужно
                target_dir = os.path.dirname(target_path)
                if target_dir and not os.path.exists(target_dir):
                    os.makedirs(target_dir, exist_ok=True)
                
                # Копируем файл или директорию
                if os.path.isdir(source_path):
                    # Удаляем целевую директорию, если она существует
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    if replacement_source:
                        self.logger.debug(f"Скопирована директория с подменой: {file_path} (источник: {replacement_source})")
                    else:
                        self.logger.debug(f"Скопирована директория: {file_path}")
                else:
                    shutil.copy2(source_path, target_path)
                    if replacement_source:
                        self.logger.debug(f"Скопирован файл с подменой: {file_path} (источник: {replacement_source})")
                    else:
                        self.logger.debug(f"Скопирован файл: {file_path}")
                copied_files.append(file_path)
                
                
            except Exception as e:
                self.logger.error(f"Ошибка копирования файла {file_path}: {e}")
                continue
        
        # Обрабатываем файлы из file_replacements, которых нет в files_to_deploy
        # Это позволяет добавлять файлы, которых нет в исходном списке
        files_to_deploy_set = set(files_to_deploy)
        for file_path, replacement_source in file_replacements.items():
            if file_path not in files_to_deploy_set:
                try:
                    # Это новый файл/директория, которого нет в files_to_deploy
                    source_path = os.path.join(self.project_root, replacement_source)
                    item_type = "директории" if os.path.isdir(source_path) else "файла"
                    self.logger.info(f"Добавление нового {item_type} {file_path} из {replacement_source}")
                    
                    # Проверяем существование файла-источника
                    if not os.path.exists(source_path):
                        self.logger.warning(f"Файл-источник для добавления не найден: {source_path}, пропускаем")
                        continue
                    
                    target_path = os.path.join(repo.working_dir, file_path)
                    
                    # Создаем директории если нужно
                    target_dir = os.path.dirname(target_path)
                    if target_dir and not os.path.exists(target_dir):
                        os.makedirs(target_dir, exist_ok=True)
                    
                    # Копируем файл или директорию
                    if os.path.isdir(source_path):
                        # Удаляем целевую директорию, если она существует
                        if os.path.exists(target_path):
                            shutil.rmtree(target_path)
                        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                        self.logger.debug(f"Добавлена новая директория: {file_path} (источник: {replacement_source})")
                    else:
                        shutil.copy2(source_path, target_path)
                        self.logger.debug(f"Добавлен новый файл: {file_path} (источник: {replacement_source})")
                    copied_files.append(file_path)
                    
                except Exception as e:
                    self.logger.error(f"Ошибка добавления файла {file_path}: {e}")
                    continue
        
        self.logger.info(f"Скопировано файлов: {len(copied_files)}")
        return copied_files


class RepositoryCleaner:
    """Очистка репозитория"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def clean_completely(self, repo: Repo) -> bool:
        """Полная очистка репозитория - удаляет все файлы кроме .git"""
        try:
            self.logger.info("Полная очистка репозитория")
            
            # Получаем список всех файлов в репозитории
            all_files = []
            for root, dirs, files in os.walk(repo.working_dir):
                # Исключаем папку .git из обхода
                if '.git' in dirs:
                    dirs.remove('.git')
                
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), repo.working_dir)
                    # Нормализуем путь для Windows
                    rel_path = rel_path.replace('\\\\', '/')
                    
                    # Исключаем .gitignore из удаления
                    if rel_path == '.gitignore':
                        self.logger.debug(f"Пропускаем .gitignore: {rel_path}")
                        continue
                    
                    all_files.append(rel_path)
            
            # Удаляем все файлы
            removed_count = 0
            for file_path in all_files:
                full_path = os.path.join(repo.working_dir, file_path)
                try:
                    os.unlink(full_path)
                    removed_count += 1
                    self.logger.debug(f"Удален файл: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Не удалось удалить файл {file_path}: {e}")
            
            # Удаляем пустые директории (кроме .git)
            self.remove_empty_dirs(repo.working_dir)
            
            self.logger.info(f"Полная очистка завершена. Удалено файлов: {removed_count}")
            print(f"🗑️ Удалено {removed_count} файлов/папок из репозитория")
            print(f"📝 Сохранен .gitignore (пользовательские настройки)")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка полной очистки репозитория: {e}")
            return False
    
    def clean_synced_directories(self, repo: Repo, files_to_deploy: List[str]) -> bool:
        """Очищает файлы внутри синхронизируемых директорий в режиме additive"""
        try:
            self.logger.info("Очистка файлов внутри синхронизируемых директорий")
            
            # Находим все синхронизируемые корневые директории
            synced_dirs = set()
            for file_path in files_to_deploy:
                # Извлекаем корневую директорию (например, "docs/", "plugins/")
                parts = file_path.replace('\\', '/').split('/')
                if len(parts) > 1:
                    synced_dirs.add(parts[0])
            
            if not synced_dirs:
                self.logger.info("Нет синхронизируемых директорий для очистки")
                return True
            
            self.logger.debug(f"Синхронизируемые директории: {synced_dirs}")
            
            # Создаем множество путей файлов для быстрого поиска
            files_to_deploy_set = {f.replace('\\', '/') for f in files_to_deploy}
            
            # Обходим синхронизируемые директории в репозитории
            removed_count = 0
            for root, dirs, files in os.walk(repo.working_dir):
                # Исключаем .git
                if '.git' in dirs:
                    dirs.remove('.git')
                
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(file_path, repo.working_dir)
                    normalized_path = rel_path.replace('\\', '/')
                    
                    # Проверяем, синхронизируется ли эта директория
                    first_dir = normalized_path.split('/')[0]
                    
                    if first_dir in synced_dirs:
                        # Если файл в синхронизируемой директории, но его нет в списке для деплоя
                        if normalized_path not in files_to_deploy_set:
                            try:
                                os.unlink(file_path)
                                removed_count += 1
                                self.logger.debug(f"Удален файл: {normalized_path}")
                            except Exception as e:
                                self.logger.warning(f"Не удалось удалить файл {normalized_path}: {e}")
            
            # Удаляем пустые директории внутри синхронизируемых
            for synced_dir in synced_dirs:
                synced_dir_path = os.path.join(repo.working_dir, synced_dir)
                if os.path.exists(synced_dir_path):
                    self.remove_empty_dirs(synced_dir_path)
            
            self.logger.info(f"Очистка завершена. Удалено файлов: {removed_count}")
            print(f"🗑️ Удалено {removed_count} файлов внутри синхронизируемых директорий")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки синхронизируемых директорий: {e}")
            return False
    
    def remove_empty_dirs(self, path: str):
        """Рекурсивно удаляет пустые директории"""
        try:
            for root, dirs, _files in os.walk(path, topdown=False):
                # Исключаем папку .git из удаления
                if '.git' in dirs:
                    dirs.remove('.git')
                
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        # Проверяем, что директория действительно пустая
                        # (исключаем .gitignore из проверки)
                        remaining_files = [f for f in os.listdir(dir_path) if f != '.gitignore']
                        if not remaining_files:  # Если директория пустая (кроме .gitignore)
                            os.rmdir(dir_path)
                            self.logger.debug(f"Удалена пустая директория: {dir_path}")
                    except OSError:
                        pass  # Игнорируем ошибки доступа
        except Exception as e:
            self.logger.warning(f"Ошибка удаления пустых директорий: {e}")

