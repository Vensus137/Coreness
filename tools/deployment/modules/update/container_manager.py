"""
Модуль для управления Docker контейнерами
Запуск, остановка, перезапуск контейнеров
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ContainerManager:
    """Класс для управления Docker контейнерами"""
    
    def __init__(self, project_root: Path, logger, config: Optional[Dict], compose_manager, compose_config_manager):
        """
        Инициализация менеджера контейнеров
        """
        self.project_root = project_root
        self.logger = logger
        self.config = config or {}
        self.compose_manager = compose_manager
        self.compose_config_manager = compose_config_manager
    
    def _get_timeout(self, timeout_name: str, default: int) -> int:
        """Получает таймаут из конфига или возвращает дефолтное значение"""
        timeouts = self.config.get('deploy_settings', {}).get('timeouts', {})
        return timeouts.get(timeout_name, default)
    
    def _get_service_name(self, environment: str) -> Optional[str]:
        """Получает имя сервиса для окружения из compose файлов"""
        service_name = self.compose_manager.get_service_name(environment)
        if not service_name:
            self.logger.error(
                f"Не удалось определить имя сервиса для окружения {environment} из compose файлов. "
                f"Проверьте наличие файлов docker-compose.{environment}.yml и корректность их структуры."
            )
            return None
        
        return service_name
    
    def _get_services_for_environment(self, environment: str, compose_command: List, cmd_files: List) -> Optional[List[str]]:
        """
        Получает список сервисов для окружения из compose файлов
        Использует docker compose config --services со всеми файлами для разрешения extends,
        затем фильтрует результат по сервисам, определенным в файле окружения
        Возвращает None если не удалось получить список сервисов
        """
        if not compose_command:
            self.logger.error("Команда docker-compose не установлена")
            return None
        
        # Получаем пути к compose файлам
        base_config, env_config, override_config = self._get_compose_files(environment)
        if not base_config or not env_config:
            self.logger.error(f"Не удалось найти compose файлы для окружения {environment}")
            return None
        
        # Парсим файл окружения, чтобы получить список сервисов, определенных в нем
        env_services = self._parse_services_from_compose_file(env_config)
        if not env_services:
            self.logger.error(f"Не найдено сервисов в файле окружения: {env_config}")
            return None
        
        # Используем все файлы для docker compose config, чтобы разрешить extends
        all_cmd_files = ['-f', str(base_config), '-f', str(env_config)]
        if override_config and override_config.exists():
            all_cmd_files.extend(['-f', str(override_config)])
        
        # Используем docker compose config --services со всеми файлами
        timeout = self._get_timeout('docker_info', 10)
        config_cmd = compose_command + all_cmd_files + ['config', '--services']
        
        # Определяем рабочий каталог
        if str(env_config).startswith(str(Path.home() / ".docker-compose")):
            cwd = self.project_root
        else:
            cwd = self.project_root / "docker"
        
        result = subprocess.run(
            config_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Неизвестная ошибка"
            self.logger.error(f"Не удалось получить список сервисов из compose файлов: {error_msg}")
            return None
        
        if not result.stdout.strip():
            self.logger.error("Список сервисов из compose файлов пуст")
            return None
        
        # Парсим список сервисов (каждый сервис на новой строке)
        all_services = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
        
        if not all_services:
            self.logger.error("Не найдено ни одного сервиса в compose файлах")
            return None
        
        # Фильтруем: оставляем только сервисы, определенные в файле окружения
        filtered_services = [s for s in all_services if s in env_services]
        
        if not filtered_services:
            self.logger.error(f"Не найдено сервисов из файла окружения в результате docker compose config")
            return None
        
        self.logger.debug(f"Найдены сервисы для окружения {environment}: {', '.join(filtered_services)}")
        return filtered_services
    
    def _parse_services_from_compose_file(self, compose_file: Path) -> List[str]:
        """
        Парсит YAML файл compose и возвращает список имен сервисов из секции services
        """
        try:
            import yaml
            with open(compose_file, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f) or {}
            
            services = compose_data.get('services', {})
            if not services:
                return []
            
            # Возвращаем список ключей (имен сервисов)
            return list(services.keys())
        except Exception as e:
            self.logger.warning(f"Не удалось распарсить compose файл {compose_file}: {e}")
            return []
    
    def _get_compose_files(self, environment: str) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """Получает пути к compose файлам (базовый, окружения, override)"""
        # Используем глобальные файлы через compose_config_manager
        base_config = self.compose_config_manager.get_base_config_path()
        env_config = self.compose_config_manager.get_config_path(environment)
        override_config = self.compose_config_manager.get_override_path(environment)
        
        # Проверяем существование
        if not base_config.exists():
            self.logger.error(f"Базовый compose файл не найден: {base_config}")
            return None, None, None
        
        if not env_config.exists():
            self.logger.error(f"Compose файл окружения не найден: {env_config}")
            return None, None, None
        
        override = override_config if override_config.exists() else None
        return base_config, env_config, override
    
    def _fix_postgresql_directory_permissions(self, environment: str) -> None:
        """Исправляет права директории PostgreSQL перед запуском контейнера (для bind mount)"""
        try:
            import os
            import stat
            
            # Путь к директории PostgreSQL на хосте
            postgresql_data_dir = self.project_root / "data" / "postgresql"
            
            # ВАЖНО: Создаем директорию ДО запуска контейнера, чтобы Docker не создал её от root
            if not postgresql_data_dir.exists():
                # Создаем директорию если её нет
                postgresql_data_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Создана директория для PostgreSQL: {postgresql_data_dir}")
                # Сразу устанавливаем правильные права при создании
                try:
                    os.chown(postgresql_data_dir, 999, 999)
                    os.chmod(postgresql_data_dir, 0o700)
                    self.logger.info(f"Установлены права директории PostgreSQL: {postgresql_data_dir} (владелец: 999:999, права: 700)")
                    return  # Если создали с правильными правами - выходим
                except PermissionError:
                    self.logger.warning(f"Не удалось установить права директории PostgreSQL (нужны root права): {postgresql_data_dir}")
                    self.logger.warning(f"Выполните вручную: chown -R 999:999 {postgresql_data_dir} && chmod 700 {postgresql_data_dir}")
                    return
                except Exception as e:
                    self.logger.warning(f"Ошибка при установке прав директории PostgreSQL: {e}")
                    return
            
            # Если директория уже существует - проверяем и исправляем права
            current_stat = postgresql_data_dir.stat()
            current_uid = current_stat.st_uid
            current_gid = current_stat.st_gid
            current_mode = stat.filemode(current_stat.st_mode)
            
            # Если директория принадлежит не postgres (999) или права неправильные - исправляем
            if current_uid != 999 or current_gid != 999 or current_mode != 'drwx------':
                try:
                    # Исправляем права (999 - UID пользователя postgres в контейнере)
                    os.chown(postgresql_data_dir, 999, 999)
                    os.chmod(postgresql_data_dir, 0o700)
                    self.logger.info(f"Исправлены права директории PostgreSQL: {postgresql_data_dir} (владелец: 999:999, права: 700)")
                except PermissionError:
                    self.logger.warning(f"Не удалось исправить права директории PostgreSQL (нужны root права): {postgresql_data_dir}")
                    self.logger.warning(f"Выполните вручную: chown -R 999:999 {postgresql_data_dir} && chmod 700 {postgresql_data_dir}")
                except Exception as e:
                    self.logger.warning(f"Ошибка при исправлении прав директории PostgreSQL: {e}")
            else:
                self.logger.debug(f"Права директории PostgreSQL корректны: {postgresql_data_dir}")
        except Exception as e:
            self.logger.warning(f"Не удалось проверить/исправить права директории PostgreSQL: {e}")
    
    def restart_with_compose(self, environment: str = "test", compose_command: List = None) -> bool:
        """Перезапускает контейнеры через docker-compose с учетом всех compose файлов"""
        try:
            if not compose_command:
                self.logger.error("Команда docker-compose не установлена")
                return False
            
            # Получаем пути к compose файлам
            base_config, env_config, override_config = self._get_compose_files(environment)
            if not base_config or not env_config:
                return False
            
            # Строим команду с нужными файлами
            cmd_files = ['-f', str(base_config), '-f', str(env_config)]
            if override_config and override_config.exists():
                cmd_files.extend(['-f', str(override_config)])
                self.logger.debug(f"Используется override файл: {override_config}")
            else:
                self.logger.debug(f"Override файл не найден или не существует, настройки ресурсов будут из базовых файлов")
            
            # Получаем список сервисов для окружения из compose файлов
            # Если не удалось получить - это критическая ошибка, не продолжаем
            services_for_env = self._get_services_for_environment(environment, compose_command, cmd_files)
            if not services_for_env:
                self.logger.error("Не удалось получить список сервисов для окружения")
                return False
            
            # Разделяем сервисы на базу данных и приложение
            # Для базы данных используем простой запуск (up без --force-recreate)
            # Для приложения - перезапуск с --force-recreate
            services_db = [s for s in services_for_env if s.startswith('postgres')]
            services_app = [s for s in services_for_env if not s.startswith('postgres')]
            
            # Определяем рабочий каталог для команд (должен совпадать с каталогом для config)
            if str(env_config).startswith(str(Path.home() / ".docker-compose")):
                up_cwd = self.project_root
            else:
                up_cwd = self.project_root / "docker"
            
            timeout_start = self._get_timeout('docker_start', 120)
            
            # 1. Проверяем и запускаем базу данных (если запущена - не трогаем, если не запущена - запускаем)
            if services_db:
                # Исправляем права директории PostgreSQL перед запуском (для bind mount)
                self._fix_postgresql_directory_permissions(environment)
                
                # Проверяем, запущены ли контейнеры базы данных
                db_containers_running = []
                db_containers_stopped = []
                
                for db_service in services_db:
                    # Получаем имя контейнера из compose файлов
                    try:
                        # Используем docker compose ps для проверки статуса
                        ps_cmd = compose_command + cmd_files + ['ps', '--format', 'json', db_service]
                        ps_result = subprocess.run(
                            ps_cmd,
                            cwd=up_cwd,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        
                        if ps_result.returncode == 0 and ps_result.stdout.strip():
                            # Парсим JSON вывод
                            import json
                            ps_data = json.loads(ps_result.stdout.strip())
                            if isinstance(ps_data, list) and len(ps_data) > 0:
                                container_state = ps_data[0].get('State', '')
                                if container_state == 'running':
                                    db_containers_running.append(db_service)
                                else:
                                    db_containers_stopped.append(db_service)
                            else:
                                db_containers_stopped.append(db_service)
                        else:
                            db_containers_stopped.append(db_service)
                    except Exception as e:
                        self.logger.debug(f"Не удалось проверить статус контейнера {db_service}: {e}, считаем что не запущен")
                        db_containers_stopped.append(db_service)
                
                if db_containers_running:
                    self.logger.info(f"Сервисы базы данных уже запущены, не перезапускаем: {', '.join(db_containers_running)}")
                
                if db_containers_stopped:
                    self.logger.info(f"Запуск сервисов базы данных для окружения {environment}: {', '.join(db_containers_stopped)}")
                    db_up_cmd = compose_command + cmd_files + ['up', '-d'] + db_containers_stopped
                    db_result = subprocess.run(
                        db_up_cmd,
                        cwd=up_cwd,
                        capture_output=False,
                        timeout=timeout_start
                    )
                    if db_result.returncode == 0:
                        self.logger.info(f"Сервисы базы данных запущены: {', '.join(db_containers_stopped)}")
                    else:
                        self.logger.warning(f"Ошибка при запуске сервисов базы данных (код: {db_result.returncode}), продолжаем...")
            
            # 2. Перезапускаем сервисы приложения (stop + up с --force-recreate)
            if services_app:
                # Останавливаем контейнеры приложения (мягкая остановка с graceful shutdown)
                timeout_stop = self._get_timeout('docker_stop', 60)
                self.logger.info(f"Остановка контейнеров приложения для окружения {environment} (graceful shutdown)")
                stop_cmd = compose_command + cmd_files + ['stop'] + services_app
                stop_result = subprocess.run(
                    stop_cmd,
                    cwd=up_cwd,
                    capture_output=False,
                    timeout=timeout_stop
                )
                
                if stop_result.returncode != 0:
                    self.logger.warning(f"Ошибка при остановке контейнеров (код: {stop_result.returncode}), продолжаем...")
                
                # Запускаем контейнеры приложения с --force-recreate для применения новых настроек
                # ВАЖНО: Используем ВСЕ файлы (base + env + override) для команды 'up',
                # чтобы Docker Compose мог разрешить 'extends' и зависимости.
                # НЕ используем --remove-orphans - он удаляет контейнеры другого окружения (test/prod)
                # Используем --no-deps чтобы НЕ пересоздавать зависимости (базу данных) при запуске приложения
                # База данных уже запущена выше, поэтому зависимости не нужны
                self.logger.info(f"Запуск сервисов приложения для окружения {environment}: {', '.join(services_app)}")
                app_up_cmd = compose_command + cmd_files + ['up', '-d', '--force-recreate', '--no-deps'] + services_app
                
                result = subprocess.run(
                    app_up_cmd,
                    cwd=up_cwd,
                    capture_output=False,
                    timeout=timeout_start
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Сервисы приложения для окружения {environment} успешно перезапущены: {', '.join(services_app)}")
                    return True
                else:
                    self.logger.error(f"Ошибка перезапуска контейнеров приложения (код: {result.returncode})")
                    return False
            else:
                # Если нет сервисов приложения, считаем успешным (база данных уже запущена)
                self.logger.info("Нет сервисов приложения для перезапуска")
                return True
                
        except subprocess.TimeoutExpired:
            self.logger.error("Таймаут при перезапуске контейнеров")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка перезапуска контейнеров: {e}")
            return False
    
    def stop_with_compose(self, environment: str = "test", compose_command: List = None) -> bool:
        """Останавливает контейнеры через docker-compose с учетом всех compose файлов"""
        try:
            if not compose_command:
                self.logger.error("Команда docker-compose не установлена")
                return False
            
            # Получаем пути к compose файлам
            base_config, env_config, override_config = self._get_compose_files(environment)
            if not base_config or not env_config:
                return False
            
            # Строим команду с нужными файлами
            cmd_files = ['-f', str(base_config), '-f', str(env_config)]
            if override_config:
                cmd_files.extend(['-f', str(override_config)])
            
            cmd = compose_command + cmd_files + ['down']
            
            timeout = self._get_timeout('docker_stop', 60)
            self.logger.info(f"Остановка контейнеров для окружения {environment}")
            result = subprocess.run(
                cmd,
                capture_output=False,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.logger.info("Контейнеры успешно остановлены")
                return True
            else:
                self.logger.error(f"Ошибка остановки контейнеров (код: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("Таймаут при остановке контейнеров")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка остановки контейнеров: {e}")
            return False
    
    def remove_environment(self, environment: str = "test", compose_command: List = None, remove_images: bool = False) -> bool:
        """
        Полностью удаляет окружение: контейнеры и опционально образы
        Volumes не удаляются - их можно удалить вручную при необходимости
        """
        try:
            compose_file = self.compose_manager.get_compose_file(environment)
            if not compose_file or not compose_file.exists():
                self.logger.error(f"Файл docker-compose не найден: {compose_file}")
                return False
            
            if not compose_command:
                self.logger.error("Команда docker-compose не установлена")
                return False
            
            # 1. Останавливаем и удаляем контейнеры для конкретного окружения
            self.logger.info(f"Остановка и удаление контейнеров для окружения {environment}")
            cmd = compose_command + [
                '-f', str(compose_file),
                'down'
            ]
            # Volumes не удаляем - они остаются для возможности восстановления данных
            
            timeout = self._get_timeout('docker_stop', 60)
            result = subprocess.run(
                cmd,
                cwd=self.project_root / "docker",
                capture_output=False,
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Ошибка удаления контейнеров (код: {result.returncode})")
                return False
            
            # 2. Удаляем образы если нужно
            if remove_images:
                image_name = self.compose_manager.get_image_name(compose_file)
                if image_name:
                    self.logger.info(f"Удаление образов для {image_name}")
                    # Получаем все теги образа
                    timeout = self._get_timeout('docker_info', 10)
                    list_cmd = ['docker', 'images', '--format', '{{.Repository}}:{{.Tag}}', image_name]
                    list_result = subprocess.run(
                        list_cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        timeout=timeout
                    )
                    
                    if list_result.returncode == 0:
                        for line in list_result.stdout.strip().split('\n'):
                            if line.strip():
                                rm_cmd = ['docker', 'rmi', '-f', line.strip()]
                                subprocess.run(
                                    rm_cmd,
                                    capture_output=False,
                                    timeout=timeout
                                )
                        self.logger.info("Образы удалены")
            
            self.logger.info(f"Окружение {environment} полностью удалено")
            return True
                
        except subprocess.TimeoutExpired:
            self.logger.error("Таймаут при удалении окружения")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка удаления окружения: {e}")
            return False

