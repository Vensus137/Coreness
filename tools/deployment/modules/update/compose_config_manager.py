"""
Модуль для работы с глобальной конфигурацией Docker Compose
Управляет созданием и использованием compose файлов в ~/.docker-compose/
"""

import shutil
from pathlib import Path
from typing import Dict, Optional


class ComposeConfigManager:
    """Класс для управления глобальной конфигурацией Docker Compose"""
    
    def __init__(self, config: Optional[Dict] = None, logger=None):
        """Инициализация менеджера конфигурации"""
        self.config = config or {}
        self.logger = logger
        
        # Получаем настройки из конфига
        docker_compose_config = self.config.get('docker_compose', {})
        global_config_dir = docker_compose_config.get('global_config_dir', '~/.docker-compose')
        
        # Разрешаем ~ в пути
        if global_config_dir.startswith('~'):
            self.global_config_dir = Path.home() / global_config_dir[2:].lstrip('/')
        else:
            self.global_config_dir = Path(global_config_dir)
        
        # Имена файлов конфигурации
        self.config_files = docker_compose_config.get('config_files', {})
        self.override_files = docker_compose_config.get('override_files', {})
    
    def _log(self, message: str, level: str = 'info'):
        """Логирует сообщение если логгер доступен"""
        if self.logger:
            if level == 'debug':
                # Убираем DEBUG логи для уменьшения шума
                pass
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)
            else:
                self.logger.info(message)
    
    def _copy_and_fix_paths(self, source: Path, target: Path, server_project_root: Path) -> None:
        """
        Копирует compose файл и исправляет пути для глобальной конфигурации
        - supervisord.conf: обновляет путь на глобальный
        - build.context: обновляет на путь к проекту на сервере
        - volumes: обновляет пути к проекту на сервере
        """
        import re
        
        # Используем переданный путь к проекту на сервере
        project_root = server_project_root
        
        # Читаем исходный файл
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Исправляем путь к supervisord.conf (относительный -> глобальный)
        # Заменяем ./supervisord.conf на абсолютный путь к глобальному файлу
        supervisord_global = self.global_config_dir / "supervisord.conf"
        content = re.sub(
            r'\./supervisord\.conf',
            str(supervisord_global),
            content
        )
        
        # Исправляем build.context если нужно
        # Если context: .., заменяем на абсолютный путь к проекту
        content = re.sub(
            r'context:\s*\.\.',
            f'context: {project_root}',
            content
        )
        
        # Исправляем dockerfile путь если нужно
        # Если dockerfile: docker/Dockerfile и context изменился, путь остается правильным
        # Но нужно убедиться что путь относительный от context
        
        # Исправляем volumes с относительными путями
        # Заменяем ..:/workspace на абсолютный путь к проекту
        content = re.sub(
            r'-\s+\.\.:/workspace',
            f'- {project_root}:/workspace',
            content
        )
        
        # Также исправляем другие возможные относительные пути в volumes
        # Например, если есть ../data:/workspace/data
        content = re.sub(
            r'-\s+\.\./([^:]+):',
            rf'- {project_root}/\1:',
            content
        )
        
        # Записываем исправленный файл
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def get_base_config_path(self) -> Path:
        """Возвращает путь к базовому compose файлу в глобальной конфигурации"""
        return self.global_config_dir / "docker-compose.yml"
    
    def get_config_path(self, environment: str) -> Path:
        """Возвращает путь к compose файлу окружения в глобальной конфигурации"""
        filename = self.config_files.get(environment)
        if not filename:
            raise ValueError(f"Не найдена конфигурация для окружения {environment}")
        return self.global_config_dir / filename
    
    def get_override_path(self, environment: str) -> Path:
        """Возвращает путь к override файлу для окружения"""
        filename = self.override_files.get(environment)
        if not filename:
            raise ValueError(f"Не найден override файл для окружения {environment}")
        return self.global_config_dir / filename
    
    def config_exists(self, environment: str) -> bool:
        """Проверяет существование конфигурации для окружения"""
        config_path = self.get_config_path(environment)
        return config_path.exists()
    
    def base_config_exists(self) -> bool:
        """Проверяет существование базового compose файла"""
        return self.get_base_config_path().exists()
    
    def override_exists(self, environment: str) -> bool:
        """Проверяет существование override файла для окружения"""
        override_path = self.get_override_path(environment)
        return override_path.exists()
    
    def create_config_from_template(self, environment: str, repo_path: Path, server_project_root: Path) -> bool:
        """
        Создает конфигурацию из шаблона в репозитории
        Копирует базовый файл и файл окружения в глобальную папку
        """
        try:
            # Создаем глобальную директорию если её нет
            self.global_config_dir.mkdir(parents=True, exist_ok=True)
            
            # Пути к шаблонам в репозитории
            repo_docker_dir = repo_path / "docker"
            base_template = repo_docker_dir / "docker-compose.yml"
            env_template = repo_docker_dir / f"docker-compose.{environment}.yml"
            
            # Проверяем существование шаблонов
            if not base_template.exists():
                self._log(f"Базовый шаблон не найден: {base_template}", 'error')
                return False
            
            if not env_template.exists():
                self._log(f"Шаблон окружения не найден: {env_template}", 'error')
                return False
            
            # Копируем supervisord.conf в глобальную папку (всегда обновляем)
            supervisord_template = repo_docker_dir / "supervisord.conf"
            if supervisord_template.exists():
                supervisord_global = self.global_config_dir / "supervisord.conf"
                # Удаляем если это директория (ошибка)
                if supervisord_global.exists() and supervisord_global.is_dir():
                    shutil.rmtree(supervisord_global)
                # Копируем файл
                shutil.copy2(supervisord_template, supervisord_global)
                self._log(f"Скопирован supervisord.conf: {supervisord_global}")
            else:
                self._log(f"Шаблон supervisord.conf не найден: {supervisord_template}", 'warning')
            
            # Копируем файлы конфигурации PostgreSQL (postgresql.*.conf, pg_hba.*.conf)
            postgresql_config_files = [
                f"postgresql.{environment}.conf",
                f"pg_hba.{environment}.conf",
            ]
            for config_file in postgresql_config_files:
                config_template = repo_docker_dir / config_file
                if config_template.exists():
                    config_global = self.global_config_dir / config_file
                    # Удаляем если это директория (ошибка)
                    if config_global.exists() and config_global.is_dir():
                        shutil.rmtree(config_global)
                    # Копируем файл
                    shutil.copy2(config_template, config_global)
                    self._log(f"Скопирован {config_file}: {config_global}")
                else:
                    self._log(f"Шаблон {config_file} не найден: {config_template}", 'warning')
            
            # Копируем базовый файл и обновляем пути (всегда обновляем для исправления путей)
            base_config_path = self.get_base_config_path()
            self._copy_and_fix_paths(base_template, base_config_path, server_project_root)
            self._log(f"Обновлен базовый compose файл: {base_config_path}")
            
            # Копируем файл окружения и обновляем пути (всегда обновляем для исправления путей)
            env_config_path = self.get_config_path(environment)
            self._copy_and_fix_paths(env_template, env_config_path, server_project_root)
            self._log(f"Обновлена конфигурация для {environment}: {env_config_path}")
            
            return True
            
        except Exception as e:
            self._log(f"Ошибка создания конфигурации из шаблона: {e}", 'error')
            return False
    
    def ensure_config_exists(self, environment: str, repo_path: Path, server_project_root: Path) -> bool:
        """
        Убеждается что конфигурация существует
        Всегда обновляет compose файлы для исправления путей (на случай изменения структуры проекта)
        
        Args:
            environment: Окружение (test/prod)
            repo_path: Путь к временной директории с клонированным репозиторием (для чтения шаблонов)
            server_project_root: Путь к реальному проекту на сервере (для build.context и volumes)
        """
        # Всегда обновляем конфигурацию из шаблона для исправления путей
        # Это важно, так как пути могут измениться при обновлении
        if not self.create_config_from_template(environment, repo_path, server_project_root):
            return False
        
        return True

