"""
Модуль для работы с версиями
Управление версиями из git tags и файла .version
"""

from pathlib import Path
from typing import Optional

import yaml
from git import GitCommandError, Repo
from modules.utils.version_utils import get_clean_version


class VersionManager:
    """Класс для управления версиями"""
    
    def __init__(self, project_root: Path, logger):
        """Инициализация менеджера версий"""
        self.project_root = project_root
        self.logger = logger
        self.version_file = project_root / "config" / ".version"
    
    def read_version(self) -> Optional[str]:
        """Читает версию из config/.version"""
        try:
            if not self.version_file.exists():
                # Файл версии не найден
                pass
                return None
            
            with open(self.version_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return None
            
            version = data.get('version')
            
            # Прочитана версия
            pass
            return version
            
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла версии: {e}")
            return None
    
    def write_version(self, version: str) -> bool:
        """Записывает версию в config/.version"""
        try:
            # Создаем директорию config если её нет
            self.version_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'version': version
            }
            
            with open(self.version_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"Записана версия: {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка записи файла версии: {e}")
            return False
    
    def get_current_version(self) -> Optional[str]:
        """Получает текущую версию из config/.version"""
        return self.read_version()
    
    
    def compare_versions(self, old_version: str, new_version: str) -> int:
        """
        Сравнивает две версии по основной части (без суффикса). Возвращает -1/0/1
        
        Использует чистые версии для сравнения, чтобы миграции работали корректно
        """
        try:
            # Используем чистые версии для сравнения
            old_clean = get_clean_version(old_version)
            new_clean = get_clean_version(new_version)
            
            old_parts = [int(x) for x in old_clean.split('.')]
            new_parts = [int(x) for x in new_clean.split('.')]
            
            # Дополняем до одинаковой длины нулями
            max_len = max(len(old_parts), len(new_parts))
            old_parts.extend([0] * (max_len - len(old_parts)))
            new_parts.extend([0] * (max_len - len(new_parts)))
            
            for old_part, new_part in zip(old_parts, new_parts, strict=True):
                if old_part < new_part:
                    return -1
                elif old_part > new_part:
                    return 1
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Ошибка сравнения версий: {e}")
            return 0
    
    def needs_migration(self, current_version: Optional[str], target_version: Optional[str]) -> bool:
        """
        Проверяет необходимость миграций БД
        
        Использует чистые версии (без суффиксов) для определения необходимости миграций
        """
        if not current_version or not target_version:
            # Если версии нет - считаем что миграции не нужны (первый запуск)
            return False
        
        # Используем чистые версии для сравнения
        current_clean = get_clean_version(current_version)
        target_clean = get_clean_version(target_version)
        
        # Если версии разные - нужны миграции
        return self.compare_versions(current_clean, target_clean) != 0
    
    def tag_exists_in_git(self, repo_path: Path, version: str) -> bool:
        """
        Проверяет существование тега версии в Git репозитории
        """
        try:
            repo = Repo(str(repo_path))
            all_tags = [tag.name for tag in repo.tags]
            
            # Проверяем тег с префиксом 'v' и без
            tag_with_v = f"v{version}"
            tag_without_v = version
            
            return tag_with_v in all_tags or tag_without_v in all_tags
            
        except Exception as e:
            self.logger.warning(f"Ошибка проверки существования тега: {e}")
            return False
    
    def get_version_from_repo(self, repo_path: Path, branch: Optional[str] = None) -> Optional[str]:
        """
        Получает версию из git tag последнего коммита в ветке
        Если branch не указан, используется дефолтная из конфига
        """
        if not branch:
            from modules.base import get_base
            branch = get_base().get_default_branch()
        
        try:
            # Открываем репозиторий через GitPython
            repo = Repo(str(repo_path))
            
            # Получаем ссылку на remote ветку
            try:
                # Пробуем получить коммит из remote ветки
                remote_ref = f'origin/{branch}'
                commit = repo.commit(remote_ref)
            except (GitCommandError, ValueError):
                # Если remote ветка не найдена, пробуем локальную
                try:
                    commit = repo.commit(branch)
                except (GitCommandError, ValueError):
                    self.logger.error(f"Не удалось найти ветку {branch} или origin/{branch}")
                    return None
            
            commit_hash = commit.hexsha
            
            # Получаем все теги репозитория
            all_tags = repo.tags
            
            # Находим теги, которые указывают на этот коммит
            tags_for_commit = []
            for tag in all_tags:
                try:
                    # Проверяем, указывает ли тег на наш коммит
                    tag_commit = tag.commit
                    if tag_commit.hexsha == commit_hash:
                        tags_for_commit.append(tag.name)
                except Exception:
                    # Пропускаем теги, которые не удалось обработать
                    continue
            
            if not tags_for_commit:
                self.logger.error(
                    f"Для коммита {commit_hash[:8]} не найдено тегов версии. "
                    f"Убедитесь, что последний коммит в ветке {branch} имеет тег версии (например, v1.0.0)"
                )
                return None
            
            # Берем последний тег (по дате создания или просто первый)
            latest_tag = tags_for_commit[0]
            
            # Если тегов несколько, берем последний по дате создания
            if len(tags_for_commit) > 1:
                # Получаем теги с датами
                tags_with_dates = []
                for tag_name in tags_for_commit:
                    try:
                        tag_ref = repo.tags[tag_name]
                        tag_date = tag_ref.commit.committed_datetime
                        tags_with_dates.append((tag_date, tag_name))
                    except Exception:
                        tags_with_dates.append((None, tag_name))
                
                # Сортируем по дате (новые первыми)
                tags_with_dates.sort(key=lambda x: x[0] if x[0] else None, reverse=True)
                latest_tag = tags_with_dates[0][1]
            
            # Извлекаем "чистую" версию из тега (убираем префикс 'v' если есть)
            # Тег: v1.0.0-beta -> версия: 1.0.0-beta
            # Используем явную проверку startswith вместо lstrip для корректной обработки
            clean_version = latest_tag[1:] if latest_tag.startswith('v') else latest_tag
            
            self.logger.info(f"Найден тег: {latest_tag}, чистая версия: {clean_version}")
            return clean_version
                
        except Exception as e:
            self.logger.error(f"Ошибка получения версии из репозитория: {e}")
            return None
    
    def list_available_tags(self, repo_path: Path, limit: int = 20) -> list:
        """
        Возвращает список доступных тегов версий (последние N тегов)
        """
        try:
            repo = Repo(str(repo_path))
            all_tags = list(repo.tags)
            
            # Получаем теги с датами
            tags_with_dates = []
            for tag in all_tags:
                try:
                    tag_date = tag.commit.committed_datetime
                    tag_name = tag.name
                    # Убираем префикс 'v' для отображения
                    clean_version = tag_name[1:] if tag_name.startswith('v') else tag_name
                    tags_with_dates.append((tag_date, clean_version, tag_name))
                except Exception:
                    continue
            
            # Сортируем по дате (новые первыми)
            tags_with_dates.sort(key=lambda x: x[0] if x[0] else None, reverse=True)
            
            # Возвращаем только последние N тегов
            return [tag[1] for tag in tags_with_dates[:limit]]
            
        except Exception as e:
            self.logger.error(f"Ошибка получения списка тегов: {e}")
            return []
    
    def get_version_by_tag(self, repo_path: Path, version: str) -> Optional[str]:
        """
        Получает версию по конкретному тегу (не обязательно последний коммит)
        Проверяет существование тега и возвращает чистую версию
        
        Примечание: Если тег был удален в GitHub, он не будет найден в клонированном репозитории.
        Это нормальное поведение - удаленные теги становятся недоступными для деплоя.
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
                return None
            
            # Извлекаем "чистую" версию из тега
            clean_version = tag_name[1:] if tag_name.startswith('v') else tag_name
            
            self.logger.info(f"Найден тег: {tag_name}, чистая версия: {clean_version}")
            return clean_version
                
        except Exception as e:
            self.logger.error(f"Ошибка получения версии по тегу: {e}")
            return None
    

