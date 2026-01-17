"""
Модуль для работы с Docker и docker-compose
Фасад, использующий специализированные модули
"""

from pathlib import Path
from typing import Dict, Optional

from modules.update.compose_config_manager import ComposeConfigManager
from modules.update.compose_manager import ComposeManager
from modules.update.container_manager import ContainerManager
from modules.update.docker_checker import DockerChecker
from modules.update.image_manager import ImageManager


class DockerManager:
    """Класс для работы с Docker и docker-compose (фасад)"""
    
    def __init__(self, project_root: Path, logger, config: Optional[Dict] = None):
        """Инициализация Docker менеджера"""
        self.project_root = project_root
        self.logger = logger
        self.config = config or {}
        
        # Инициализируем специализированные модули
        self.checker = DockerChecker(logger, config)
        self.compose_config_manager = ComposeConfigManager(config, logger)
        self.compose_manager = ComposeManager(project_root, logger, config, self.compose_config_manager)
        self.container_manager = ContainerManager(project_root, logger, config, self.compose_manager, self.compose_config_manager)
        self.image_manager = ImageManager(project_root, logger, config, self.compose_manager, self.container_manager)
        
        # Устанавливаем команду docker-compose в compose_manager
        compose_command = self.checker.get_compose_command()
        self.compose_manager.set_compose_command(compose_command)
        
        # Получаем настройки из конфига
        docker_compose_config = self.config.get('docker_compose', {})
        self.dc_config_path = self._resolve_path(docker_compose_config.get('dc_config_path', '~/.dc_config'))
    
    def _resolve_path(self, path_str: str) -> Path:
        """Разрешает путь с ~ в абсолютный Path"""
        if path_str.startswith('~'):
            return Path.home() / path_str[2:].lstrip('/')
        return Path(path_str)
    
    # Методы проверки Docker (делегируются DockerChecker)
    def check_docker(self) -> bool:
        """Проверяет Docker"""
        return self.checker.check_docker()
    
    def check_docker_compose(self) -> bool:
        """Проверяет docker-compose"""
        return self.checker.check_docker_compose()
    
    def is_docker_running(self) -> bool:
        """Проверяет работу Docker daemon"""
        return self.checker.is_docker_running()
    
    def get_compose_command(self) -> list:
        """Возвращает команду docker-compose"""
        return self.checker.get_compose_command()
    
    # Методы работы с образами (делегируются ImageManager)
    def build_with_compose(self, environment: str = "test", version: Optional[str] = None) -> bool:
        """
        Собирает Docker образ через docker-compose
        Для prod окружения тегирует образ версией для возможности отката
        """
        compose_command = self.get_compose_command()
        return self.image_manager.build_with_compose(environment, version, compose_command)
    
    def rollback_image(self, environment: str, version: str) -> bool:
        """
        Откатывает Docker образ на указанную версию (только для prod)
        """
        compose_command = self.get_compose_command()
        return self.image_manager.rollback_image(environment, version, compose_command, self.container_manager)
    
    def list_available_versions(self, environment: str) -> list:
        """
        Возвращает список доступных версий образов (только для prod)
        """
        return self.image_manager.list_available_versions(environment)
    
    def list_images_with_info(self, environment: str) -> list:
        """
        Возвращает список образов с информацией (версия, размер, дата создания)
        """
        return self.image_manager.list_images_with_info(environment)
    
    def cleanup_old_images(self, environment: str = "prod", keep_versions: int = 5, versions_to_remove: Optional[list] = None) -> dict:
        """
        Очищает старые Docker образы
        Возвращает словарь с результатами очистки
        """
        return self.image_manager.cleanup_old_images(environment, keep_versions, versions_to_remove)
    
    # Методы управления контейнерами (делегируются ContainerManager)
    def restart_with_compose(self, environment: str = "test") -> bool:
        """Перезапускает контейнеры через docker-compose"""
        compose_command = self.get_compose_command()
        return self.container_manager.restart_with_compose(environment, compose_command)
    
    def stop_with_compose(self, environment: str = "test") -> bool:
        """Останавливает контейнеры через docker-compose"""
        compose_command = self.get_compose_command()
        return self.container_manager.stop_with_compose(environment, compose_command)
    
    def remove_environment(self, environment: str = "test", remove_images: bool = False) -> bool:
        """
        Полностью удаляет окружение: контейнеры и опционально образы
        Volumes не удаляются - их можно удалить вручную при необходимости
        """
        compose_command = self.get_compose_command()
        return self.container_manager.remove_environment(environment, compose_command, remove_images)
    
    # Вспомогательные методы для обратной совместимости
    def _get_compose_file(self, environment: str):
        """Возвращает путь к файлу docker-compose для окружения (для обратной совместимости)"""
        return self.compose_manager.get_compose_file(environment)
    
    def _get_image_name(self, compose_file):
        """Получает имя образа из docker-compose файла (для обратной совместимости)"""
        return self.compose_manager.get_image_name(compose_file)
    
    def restore_resources_config(self, environment: str) -> bool:
        """
        Восстанавливает docker-compose.override.yml из ~/.dc_config после обновления
        Читает настройки ресурсов из конфига в формате <container-name>.<parameter>=<value>
        и генерирует override файл для всех сервисов окружения
        """
        try:
            
            # Путь к конфигу (из конфига)
            config_file = self.dc_config_path
            if not config_file.exists():
                # Конфиг не найден, пропускаем восстановление ресурсов
                return True  # Не критично, если конфига нет
            
            # Читаем конфиг
            config_values = {}
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Пропускаем комментарии и пустые строки
                        if not line or line.startswith('#'):
                            continue
                        # Парсим KEY=VALUE (формат: <container-name>.<parameter>=<value>)
                        if '=' in line:
                            key, value = line.split('=', 1)
                            config_values[key.strip()] = value.strip()
            except Exception as e:
                self.logger.warning(f"Не удалось прочитать ~/.dc_config: {e}")
                return False
            
            # Получаем список всех сервисов для окружения из compose файлов
            compose_command = self.get_compose_command()
            base_config, env_config, override_config = self.compose_config_manager.get_base_config_path(), \
                                                      self.compose_config_manager.get_config_path(environment), \
                                                      self.compose_config_manager.get_override_path(environment)
            
            if not base_config.exists() or not env_config.exists():
                self.logger.warning("Compose файлы не найдены, пропускаем восстановление ресурсов")
                return True
            
            # Получаем список сервисов через container_manager
            from modules.update.container_manager import ContainerManager
            container_manager = ContainerManager(
                self.project_root,
                self.logger,
                self.config,
                self.compose_manager,
                self.compose_config_manager
            )
            cmd_files = ['-f', str(base_config), '-f', str(env_config)]
            if override_config.exists():
                cmd_files.extend(['-f', str(override_config)])
            services_for_env = container_manager._get_services_for_environment(environment, compose_command, cmd_files)
            if not services_for_env:
                self.logger.error("Не удалось получить список сервисов из compose файлов")
                # Пробуем получить хотя бы один сервис для приложения
                service_name = self.compose_manager.get_service_name(environment)
                if not service_name:
                    self.logger.error(
                        f"Не удалось определить имя сервиса для окружения {environment} из compose файлов. "
                        f"Проверьте наличие файлов docker-compose.{environment}.yml и корректность их структуры."
                    )
                    return False
                services_for_env = [service_name]
            
            # Собираем настройки для всех сервисов
            services_config = {}
            for service_name in services_for_env:
                # Ищем настройки в формате <service-name>.<parameter>
                cpus = config_values.get(f"{service_name}.cpus", "")
                memory = config_values.get(f"{service_name}.memory", "")
                cpus_reserve = config_values.get(f"{service_name}.cpus_reserve", "")
                memory_reserve = config_values.get(f"{service_name}.memory_reserve", "")
                
                if cpus or memory or cpus_reserve or memory_reserve:
                    services_config[service_name] = {
                        'cpus': cpus,
                        'memory': memory,
                        'cpus_reserve': cpus_reserve,
                        'memory_reserve': memory_reserve
                    }
            
            # Если нет настроек для сервисов - удаляем override файл если он существует
            if not services_config:
                override_file = self.compose_config_manager.get_override_path(environment)
                if override_file.exists():
                    try:
                        override_file.unlink()
                    except Exception:
                        pass  # Игнорируем ошибки удаления
                return True
            
            # Генерируем override файл в глобальной папке
            override_file = self.compose_config_manager.get_override_path(environment)
            override_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Формируем содержимое файла для всех сервисов
            lines = ["services:"]
            
            for service_name, settings in services_config.items():
                lines.append(f"  {service_name}:")
                lines.append("    deploy:")
                lines.append("      resources:")
                
                # Добавляем limits если есть
                if settings['cpus'] or settings['memory']:
                    lines.append("        limits:")
                    if settings['cpus']:
                        lines.append(f"          cpus: '{settings['cpus']}'")
                    if settings['memory']:
                        lines.append(f"          memory: '{settings['memory']}'")
                
                # Добавляем reservations если есть
                if settings['cpus_reserve'] or settings['memory_reserve']:
                    lines.append("        reservations:")
                    if settings['cpus_reserve']:
                        lines.append(f"          cpus: '{settings['cpus_reserve']}'")
                    if settings['memory_reserve']:
                        lines.append(f"          memory: '{settings['memory_reserve']}'")
            
            # Записываем файл
            with open(override_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + '\n')
            
            # Логируем что было восстановлено
            self.logger.info(f"Восстановлен docker-compose.override-{environment}.yml из ~/.dc_config для окружения {environment}")
            self.logger.info(f"  Путь: {override_file}")
            for service_name, settings in services_config.items():
                self.logger.info(f"  Сервис: {service_name}")
                if settings['cpus']:
                    self.logger.info(f"    CPU: {settings['cpus']}")
                if settings['memory']:
                    self.logger.info(f"    Memory: {settings['memory']}")
                if settings['cpus_reserve']:
                    self.logger.info(f"    CPU Reserve: {settings['cpus_reserve']}")
                if settings['memory_reserve']:
                    self.logger.info(f"    Memory Reserve: {settings['memory_reserve']}")
            return True
            
        except Exception as e:
            self.logger.warning(f"Не удалось восстановить настройки ресурсов: {e}")
            return False  # Не критично, но логируем