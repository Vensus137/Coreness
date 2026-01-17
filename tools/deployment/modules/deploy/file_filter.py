"""
Модуль для фильтрации файлов согласно правилам деплоя
"""

import glob
import os
from pathlib import Path
from typing import Dict, List, Optional, Set


class FileFilter:
    """Класс для фильтрации файлов по правилам деплоя"""
    
    def __init__(self, config: dict, logger, project_root: Optional[Path] = None):
        self.config = config
        self.logger = logger
        
        # Получаем project_root из базового модуля или используем переданный
        if project_root is None:
            from modules.base import get_base
            self.project_root = get_base().get_project_root()
        else:
            self.project_root = project_root
    
    def _expand_patterns(self, patterns: List[str]) -> Set[str]:
        """Расширяет паттерны в список файлов"""
        files = set()
        
        for pattern in patterns:
            if pattern == "*":
                # Все файлы в проекте
                for root, dirs, filenames in os.walk(self.project_root):
                    # Исключаем .git и другие системные папки
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv']]
                    
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_path, self.project_root)
                        files.add(rel_path)
                        
            elif pattern.endswith('/'):
                # Папка целиком
                folder_path = os.path.join(self.project_root, pattern[:-1])
                if os.path.exists(folder_path):
                    for root, dirs, filenames in os.walk(folder_path):
                        # Исключаем системные папки
                        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__']]
                        
                        for filename in filenames:
                            file_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(file_path, self.project_root)
                            files.add(rel_path)
                            
            else:
                # Конкретный файл или паттерн
                pattern_path = os.path.join(self.project_root, pattern)
                if os.path.exists(pattern_path):
                    if os.path.isfile(pattern_path):
                        files.add(pattern)
                    elif os.path.isdir(pattern_path):
                        # Рекурсивно добавляем все файлы из папки
                        for root, dirs, filenames in os.walk(pattern_path):
                            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__']]
                            
                            for filename in filenames:
                                file_path = os.path.join(root, filename)
                                rel_path = os.path.relpath(file_path, self.project_root)
                                files.add(rel_path)
                else:
                    # Пробуем glob паттерн
                    glob_pattern = os.path.join(self.project_root, pattern)
                    for file_path in glob.glob(glob_pattern, recursive=True):
                        if os.path.isfile(file_path):
                            rel_path = os.path.relpath(file_path, self.project_root)
                            files.add(rel_path)
        
        return files
    
    def _apply_excludes(self, files: Set[str], excludes: List[str]) -> Set[str]:
        """Применяет исключения к списку файлов с поддержкой рекурсивных паттернов"""
        excluded_files = set()
        
        for exclude_pattern in excludes:
            pattern_excluded = set()
            
            # Нормализуем паттерн (заменяем обратные слеши на прямые)
            normalized_pattern = exclude_pattern.replace('\\', '/')
            
            # Рекурсивный паттерн (начинается с **/)
            if normalized_pattern.startswith('**/'):
                # Убираем **/ из начала
                pattern_suffix = normalized_pattern[3:]  # Убираем '**/'
                
                for file_path in files:
                    normalized_file_path = file_path.replace('\\', '/')
                    
                    # Проверяем, содержит ли путь паттерн в любой позиции
                    if pattern_suffix.endswith('/'):
                        # Паттерн для папки (например, **/tests/)
                        folder_name = pattern_suffix[:-1]  # Убираем завершающий /
                        # Проверяем наличие /folder_name/ или /folder_name в пути
                        # Также проверяем, начинается ли путь с folder_name/ (папка в корне проекта)
                        if (f'/{folder_name}/' in normalized_file_path or 
                            normalized_file_path.endswith(f'/{folder_name}') or
                            normalized_file_path.startswith(f'{folder_name}/')):
                            pattern_excluded.add(file_path)
                    else:
                        # Паттерн для файла или имени (например, **/*.pyc)
                        # Проверяем, заканчивается ли путь на паттерн
                        if normalized_file_path.endswith(pattern_suffix) or f'/{pattern_suffix}' in normalized_file_path:
                            pattern_excluded.add(file_path)
            
            # Паттерн для папки (заканчивается на /)
            elif normalized_pattern.endswith('/'):
                folder_path = normalized_pattern[:-1]  # Убираем завершающий /
                
                for file_path in files:
                    normalized_file_path = file_path.replace('\\', '/')
                    
                    # Проверяем, начинается ли путь с папки (точное совпадение в начале)
                    if normalized_file_path.startswith(folder_path + '/'):
                        pattern_excluded.add(file_path)
                    # Также проверяем рекурсивно (папка может быть в любом месте)
                    elif f'/{folder_path}/' in normalized_file_path or normalized_file_path.endswith(f'/{folder_path}'):
                        pattern_excluded.add(file_path)
            
            # Паттерн с wildcard в конце (например, tests/*)
            elif normalized_pattern.endswith('*'):
                pattern = normalized_pattern[:-1]  # Убираем *
                for file_path in files:
                    normalized_file_path = file_path.replace('\\', '/')
                    if normalized_file_path.startswith(pattern):
                        pattern_excluded.add(file_path)
            
            # Точное совпадение
            else:
                normalized_pattern_for_match = normalized_pattern
                for file_path in files:
                    normalized_file_path = file_path.replace('\\', '/')
                    if normalized_file_path == normalized_pattern_for_match:
                        pattern_excluded.add(file_path)
            
            # Добавляем исключенные файлы
            if pattern_excluded:
                excluded_files.update(pattern_excluded)
        
        result = files - excluded_files
        
        return result
    
    def get_files_for_repo(self, repo_name: str, deployment_config: Dict) -> List[str]:
        """Получает список файлов для деплоя в указанный репозиторий"""
        self.logger.info(f"Фильтрация файлов для {repo_name}")
        
        # Разрешаем пресеты и объединяем правила
        resolved_rules = self._resolve_deployment_rules(deployment_config)
        
        includes = resolved_rules.get('include', [])
        excludes = resolved_rules.get('exclude', [])
        
        if not includes:
            self.logger.warning(f"Нет правил include для {repo_name}")
            return []
        
        # Расширяем паттерны include (DEBUG логи убраны для уменьшения шума)
        included_files = self._expand_patterns(includes)
        
        # Применяем исключения
        if excludes:
            self.logger.info(f"Применяем {len(excludes)} исключений для {repo_name}: {excludes}")
            included_files = self._apply_excludes(included_files, excludes)
            self.logger.info(f"Осталось {len(included_files)} файлов после исключений")
        else:
            self.logger.info(f"Нет исключений для {repo_name}")
        
        # Сортируем для предсказуемости
        result = sorted(included_files)
        
        self.logger.info(f"Итого файлов для {repo_name}: {len(result)}")
        
        # Отладочная информация (DEBUG логи убраны для уменьшения шума)
        
        return result
    
    def _resolve_deployment_rules(self, deployment_config: Dict) -> Dict:
        """Разрешает пресеты и объединяет правила деплоя"""
        resolved_rules = {
            'include': [],
            'exclude': []
        }
        
        # Получаем пресеты
        presets = deployment_config.get('presets', [])
        custom_include = deployment_config.get('custom_include', [])
        custom_exclude = deployment_config.get('custom_exclude', [])
        
        # Обрабатываем пресеты
        for preset_name in presets:
            if preset_name not in self.config.get('deployment_presets', {}):
                self.logger.warning(f"Пресет '{preset_name}' не найден в конфигурации")
                continue
            
            preset_config = self.config['deployment_presets'][preset_name]
            
            # Добавляем include из пресета
            preset_includes = preset_config.get('include', [])
            resolved_rules['include'].extend(preset_includes)
            
            # Добавляем exclude из пресета
            preset_excludes = preset_config.get('exclude', [])
            resolved_rules['exclude'].extend(preset_excludes)
        
        # Добавляем кастомные правила (они имеют приоритет)
        resolved_rules['include'].extend(custom_include)
        resolved_rules['exclude'].extend(custom_exclude)
        
        # Удаляем дубликаты, сохраняя порядок
        resolved_rules['include'] = list(dict.fromkeys(resolved_rules['include']))
        resolved_rules['exclude'] = list(dict.fromkeys(resolved_rules['exclude']))
        
        # Удаляем исключения, которые также указаны в include (кастомные правила имеют приоритет)
        resolved_rules['exclude'] = [ex for ex in resolved_rules['exclude'] 
                                   if ex not in custom_include]
        
        return resolved_rules
    
    def validate_files_exist(self, files: List[str]) -> List[str]:
        """Проверяет существование файлов"""
        missing_files = []
        
        for file_path in files:
            full_path = os.path.join(self.project_root, file_path)
            if not os.path.exists(full_path):
                missing_files.append(file_path)
                self.logger.warning(f"Файл не найден: {file_path}")
        
        return missing_files

