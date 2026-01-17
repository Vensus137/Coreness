"""
Модуль для парсинга версии и даты из CHANGELOG.md
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


class ChangelogParser:
    """Класс для парсинга CHANGELOG.md"""
    
    def __init__(self, project_root: Path, config: Optional[dict] = None):
        self.project_root = project_root
        self.config = config or {}
        # Получаем путь к changelog файлу из конфига, по умолчанию docs/CHANGELOG.md
        changelog_settings = self.config.get('changelog_settings', {})
        changelog_file = changelog_settings.get('changelog_file', 'docs/CHANGELOG.md')
        self.changelog_file = changelog_file
    
    def parse_latest_version(self) -> Tuple[Optional[str], Optional[str]]:
        """Парсит последнюю версию и дату из changelog файла (для деплоя во внешние репозитории)"""
        try:
            changelog_path = self.project_root / self.changelog_file
            if not changelog_path.exists():
                return None, None
            
            version, date = self._parse_file(changelog_path)
            return version, date
            
        except Exception as e:
            print(f"⚠️ Ошибка парсинга {self.changelog_file}: {e}")
            return None, None
    
    def _parse_file(self, file_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Парсит версию из конкретного файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Паттерн для поиска версий: ## [X.Y.Z] - YYYY-MM-DD
            # Исключаем [Unreleased] и другие не-версии
            version_pattern = r'## \[([\d.]+)\](?: - (\d{4}-\d{2}-\d{2}))?'
            matches = re.findall(version_pattern, content)
            
            if not matches:
                return None, None
            
            # Берем первую (последнюю) версию
            version = matches[0][0]
            date = matches[0][1]
            
            # Если даты нет, используем текущую
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            return version, date
            
        except Exception as e:
            print(f"⚠️ Ошибка парсинга файла {file_path}: {e}")
            return None, None
    
    def get_version_info(self) -> dict:
        """Получает информацию о версии для отображения пользователю"""
        version, date = self.parse_latest_version()
        
        if version and date:
            return {
                'version': version,
                'date': date,
                'source': self.changelog_file,
                'found': True
            }
        else:
            return {
                'version': None,
                'date': None,
                'source': self.changelog_file,
                'found': False
            }
    
    def validate_version_format(self, version: str) -> bool:
        """Проверяет корректность формата версии"""
        # Паттерн для версий: X.Y.Z или X.Y или X
        version_pattern = r'^\d+(\.\d+)*$'
        return bool(re.match(version_pattern, version))
    
    def suggest_next_version(self, current_version: str) -> str:
        """Предлагает следующую версию (увеличивает patch версию)"""
        try:
            parts = current_version.split('.')
            if len(parts) >= 3:
                # Увеличиваем patch версию
                parts[2] = str(int(parts[2]) + 1)
            elif len(parts) == 2:
                # Добавляем patch версию
                parts.append('1')
            else:
                # Добавляем minor и patch версии
                parts.extend(['0', '1'])
            
            return '.'.join(parts)
            
        except (ValueError, IndexError):
            # Если что-то пошло не так, просто добавляем .1
            return f"{current_version}.1"

