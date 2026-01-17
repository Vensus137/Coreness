"""
Модуль для работы с docker-compose файлами
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional

import yaml


class ComposeManager:
    """Класс для работы с docker-compose файлами"""
    
    def __init__(self, project_root: Path, logger, config: Optional[Dict] = None, compose_config_manager=None):
        """Инициализация менеджера compose"""
        self.project_root = project_root
        self.logger = logger
        self.config = config or {}
        self.compose_command = None
        self.compose_config_manager = compose_config_manager
    
    def _get_timeout(self, timeout_name: str, default: int) -> int:
        """Получает таймаут из конфига или возвращает дефолтное значение"""
        timeouts = self.config.get('deploy_settings', {}).get('timeouts', {})
        return timeouts.get(timeout_name, default)
    
    def set_compose_command(self, compose_command: list):
        """Устанавливает команду docker-compose"""
        self.compose_command = compose_command
    
    def get_compose_file(self, environment: str) -> Optional[Path]:
        """Возвращает путь к файлу docker-compose для окружения"""
        if not self.compose_config_manager:
            return None
        
        try:
            if self.compose_config_manager.config_exists(environment):
                return self.compose_config_manager.get_config_path(environment)
        except Exception:
            pass
        
        return None
    
    def get_image_name(self, compose_file: Path) -> Optional[str]:
        """Получает имя образа из docker-compose файла"""
        try:
            # Используем docker-compose config для получения финального конфига (с учетом extends)
            if not self.compose_command:
                self.logger.warning("Команда docker-compose не установлена")
                return None
            
            cmd = self.compose_command + [
                '-f', str(compose_file),
                'config'
            ]
            timeout = self._get_timeout('git_operation', 30)
            result = subprocess.run(
                cmd,
                cwd=self.project_root / "docker",
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Не удалось получить конфиг docker-compose: {result.stderr}")
                return None
            
            compose_data = yaml.safe_load(result.stdout)
            
            services = compose_data.get('services', {})
            if not services:
                return None
            
            # Получаем имя первого сервиса
            service_name = list(services.keys())[0]
            service_config = services.get(service_name, {})
            
            # Если есть явное указание image - используем его
            if 'image' in service_config:
                image_name = service_config['image']
                # Убираем тег если есть
                if ':' in image_name:
                    image_name = image_name.split(':')[0]
                return image_name
            
            # Иначе формируем имя по шаблону docker-compose: project-service
            # Docker-compose использует имя директории как префикс проекта
            project_name = self.project_root.name.lower().replace(' ', '-')
            return f"{project_name}-{service_name}"
            
        except Exception as e:
            self.logger.warning(f"Не удалось определить имя образа: {e}")
            return None
    
    def get_built_image_id(self, compose_file: Path) -> Optional[str]:
        """Получает ID собранного образа из docker-compose"""
        try:
            if not self.compose_command:
                return None
            
            cmd = self.compose_command + [
                '-f', str(compose_file),
                'images', '-q'
            ]
            timeout = self._get_timeout('git_operation', 30)
            result = subprocess.run(
                cmd,
                cwd=self.project_root / "docker",
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
            return None
        except Exception as e:
            self.logger.warning(f"Не удалось получить ID образа: {e}")
            return None
    
    def get_service_name(self, environment: str) -> Optional[str]:
        """Получает имя сервиса из docker-compose файла для окружения"""
        try:
            # Сначала пробуем прочитать файл окружения напрямую
            compose_file = self.get_compose_file(environment)
            if not compose_file:
                return None
            
            # Если есть файл окружения - читаем его отдельно
            env_compose_file = None
            if self.compose_config_manager:
                if self.compose_config_manager.config_exists(environment):
                    env_compose_file = self.compose_config_manager.get_config_path(environment)
            else:
                return None
            
            if env_compose_file and env_compose_file.exists():
                try:
                    with open(env_compose_file, 'r', encoding='utf-8') as f:
                        env_compose_data = yaml.safe_load(f) or {}
                    env_services = env_compose_data.get('services', {})
                    
                    # Берем первый сервис из файла окружения
                    if env_services:
                        service_name = list(env_services.keys())[0]
                        return service_name
                except Exception:
                    # Не удалось прочитать файл окружения
                    pass
            
            # Если не нашли в файле окружения - используем docker compose config для получения финального конфига
            if not self.compose_command:
                return None
            
            # Формируем команду с базовым файлом и файлом окружения
            if not self.compose_config_manager:
                return None
            
            base_compose_file = self.compose_config_manager.get_base_config_path()
            
            if not base_compose_file or not base_compose_file.exists():
                return None
            
            cmd = list(self.compose_command) + ['-f', str(base_compose_file)]
            
            # Добавляем файл окружения если есть (и он отличается от базового)
            if env_compose_file and env_compose_file.exists() and env_compose_file != base_compose_file:
                cmd.extend(['-f', str(env_compose_file)])
            
            cmd.append('config')
            
            timeout = self._get_timeout('git_operation', 30)
            result = subprocess.run(
                cmd,
                cwd=self.project_root / "docker" if not self.compose_config_manager else base_compose_file.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                return None
            
            compose_data = yaml.safe_load(result.stdout)
            services = compose_data.get('services', {})
            
            if not services:
                return None
            
            # Берем первый сервис из финального конфига
            service_name = list(services.keys())[0]
            return service_name
            
        except Exception as e:
            self.logger.warning(f"Не удалось определить имя сервиса: {e}")
            return None
    
    def get_container_name(self, environment: str) -> Optional[str]:
        """Получает имя контейнера из docker-compose файла для окружения"""
        try:
            compose_file = self.get_compose_file(environment)
            if not compose_file:
                # Файл docker-compose для окружения не найден
                pass
                return None
            
            # Используем docker-compose config для получения финального конфига (с учетом extends)
            if not self.compose_command:
                self.logger.warning("Команда docker-compose не установлена")
                return None
            
            if not self.compose_config_manager:
                return None
            
            # Формируем команду с базовым файлом и файлом окружения
            base_compose_file = self.compose_config_manager.get_base_config_path()
            if not base_compose_file or not base_compose_file.exists():
                return None
            
            cmd = list(self.compose_command) + ['-f', str(base_compose_file)]
            
            # Добавляем файл окружения если есть (и он отличается от базового)
            env_compose_file = None
            if self.compose_config_manager.config_exists(environment):
                env_compose_file = self.compose_config_manager.get_config_path(environment)
            
            if env_compose_file and env_compose_file.exists() and env_compose_file != base_compose_file:
                cmd.extend(['-f', str(env_compose_file)])
            
            cmd.append('config')
            
            timeout = self._get_timeout('git_operation', 30)
            result = subprocess.run(
                cmd,
                cwd=base_compose_file.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Не удалось получить конфиг docker-compose: {result.stderr}")
                return None
            
            compose_data = yaml.safe_load(result.stdout)
            
            services = compose_data.get('services', {})
            if not services:
                return None
            
            # Определяем сервис из файла окружения (без хардкода)
            # Если есть файл окружения - читаем его отдельно и берем сервисы оттуда
            service_name = None
            
            if env_compose_file and env_compose_file.exists():
                # Читаем файл окружения отдельно
                try:
                    with open(env_compose_file, 'r', encoding='utf-8') as f:
                        env_compose_data = yaml.safe_load(f) or {}
                    env_services = env_compose_data.get('services', {})
                    
                    # Берем первый сервис из файла окружения
                    if env_services:
                        service_name = list(env_services.keys())[0]
                except Exception:
                    # Не удалось прочитать файл окружения
                    pass
            
            # Если не нашли сервис из файла окружения - берем первый из финального конфига
            if not service_name:
                service_name = list(services.keys())[0]
            
            # Проверяем, что сервис существует в финальном конфиге
            if service_name not in services:
                self.logger.warning(f"Сервис {service_name} не найден в финальном конфиге. Доступные: {list(services.keys())}")
                # Пробуем найти сервис, который содержит container_name
                for svc_name, svc_config in services.items():
                    if svc_config.get('container_name'):
                        service_name = svc_name
                        break
                else:
                    # Если не нашли - берем первый
                    service_name = list(services.keys())[0]
            
            service_config = services.get(service_name, {})
            
            # Извлекаем container_name
            container_name = service_config.get('container_name')
            if container_name:
                return container_name
            
            # Если container_name не указан - возвращаем None (будет использован дефолт)
            return None
            
        except Exception as e:
            self.logger.warning(f"Не удалось определить имя контейнера: {e}")
            return None
    
    def get_postgres_service_name(self, environment: str) -> Optional[str]:
        """Получает имя сервиса PostgreSQL из docker-compose файла для окружения"""
        try:
            if not self.compose_config_manager:
                return None
            
            # Сначала читаем файл окружения напрямую, чтобы найти сервис PostgreSQL
            if self.compose_config_manager.config_exists(environment):
                env_compose_file = self.compose_config_manager.get_config_path(environment)
                if env_compose_file and env_compose_file.exists():
                    try:
                        with open(env_compose_file, 'r', encoding='utf-8') as f:
                            env_compose_data = yaml.safe_load(f) or {}
                        env_services = env_compose_data.get('services', {})
                        
                        # Ищем сервис PostgreSQL в файле окружения
                        # Проверяем сервисы, которые могут extends базовый postgres или имеют имя, начинающееся с postgres
                        for service_name, service_config in env_services.items():
                            # Проверяем, extends ли этот сервис базовый postgres
                            extends = service_config.get('extends', {})
                            if isinstance(extends, dict):
                                base_service = extends.get('service')
                                if base_service == 'postgres':
                                    return service_name
                            
                            # Или проверяем имя сервиса
                            if service_name.startswith('postgres'):
                                return service_name
                    except Exception as e:
                        self.logger.warning(f"Не удалось прочитать файл окружения {env_compose_file}: {e}")
            
            # Если не нашли в файле окружения, используем объединенный конфиг как fallback
            if not self.compose_command:
                self.logger.warning("Команда docker-compose не установлена")
                return None
            
            base_compose_file = self.compose_config_manager.get_base_config_path()
            if not base_compose_file or not base_compose_file.exists():
                return None
            
            env_compose_file = None
            if self.compose_config_manager.config_exists(environment):
                env_compose_file = self.compose_config_manager.get_config_path(environment)
            
            # Формируем команду с базовым файлом
            cmd = list(self.compose_command) + ['-f', str(base_compose_file)]
            
            # Добавляем файл окружения если есть (и он отличается от базового)
            if env_compose_file and env_compose_file.exists() and env_compose_file != base_compose_file:
                cmd.extend(['-f', str(env_compose_file)])
            
            cmd.append('config')
            
            # Для глобальных файлов используем директорию базового файла
            cwd = base_compose_file.parent
            
            timeout = self._get_timeout('git_operation', 30)
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.warning(f"Не удалось получить конфиг docker-compose: {result.stderr}")
                return None
            
            compose_data = yaml.safe_load(result.stdout)
            services = compose_data.get('services', {})
            
            if not services:
                return None
            
            # Ищем любой сервис PostgreSQL в объединенном конфиге
            for service_name in services.keys():
                if service_name.startswith('postgres'):
                    return service_name
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Не удалось определить имя сервиса PostgreSQL: {e}")
            return None
    
    def check_service_exists(self, service_name: str, environment: str) -> bool:
        """Проверяет существование сервиса в compose файлах для окружения"""
        try:
            if not self.compose_command:
                return False
            
            if not self.compose_config_manager:
                return False
            
            # Используем глобальные файлы
            base_compose_file = self.compose_config_manager.get_base_config_path()
            if not base_compose_file or not base_compose_file.exists():
                return False
            
            env_compose_file = None
            if self.compose_config_manager.config_exists(environment):
                env_compose_file = self.compose_config_manager.get_config_path(environment)
            
            override_file = None
            override_path = self.compose_config_manager.get_override_path(environment)
            if override_path.exists():
                override_file = override_path
            
            # Формируем команду с базовым файлом
            cmd = list(self.compose_command) + ['-f', str(base_compose_file)]
            
            # Добавляем файл окружения если есть
            if env_compose_file and env_compose_file.exists() and env_compose_file != base_compose_file:
                cmd.extend(['-f', str(env_compose_file)])
            
            # Добавляем override файл если есть
            if override_file and override_file.exists():
                cmd.extend(['-f', str(override_file)])
            
            cmd.extend(['config', '--services'])
            
            # Для глобальных файлов используем директорию базового файла
            cwd = base_compose_file.parent
            
            timeout = self._get_timeout('git_operation', 30)
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            if result.returncode != 0:
                return False
            
            # Проверяем, есть ли сервис в списке
            services = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            return service_name in services
            
        except Exception:
            # Не удалось проверить существование сервиса
            pass
            return False

