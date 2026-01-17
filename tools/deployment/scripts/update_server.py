#!/usr/bin/env python3
"""
Скрипт для обновления сервера
Полный флоу обновления: клонирование, обновление файлов, миграции БД, Docker
"""

import os
import platform
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Инициализируем базовый модуль (определяет project_root, загружает config и env)
from modules.base import get_base
from modules.migrations.migration_manager import MigrationManager
from modules.ui.output import get_formatter
from modules.update.compose_config_manager import ComposeConfigManager
from modules.update.docker_manager import DockerManager
from modules.update.server_updater import ServerUpdater
from modules.update.version_manager import VersionManager
from modules.utils.console_logger import ConsoleLogger


class UpdateServerScript:
    """Скрипт для обновления сервера"""
    
    def __init__(self):
        """Инициализация"""
        # Получаем базовый экземпляр (инициализирует все один раз)
        self.base = get_base()
        self.project_root = self.base.get_project_root()
        self.config = self.base.get_config()
        
        # Инициализируем логгер и форматтер
        self.logger = ConsoleLogger("update_server")
        self.formatter = get_formatter()
        
        # Инициализируем менеджеры
        self.version_manager = VersionManager(self.project_root, self.logger)
        self.server_updater = ServerUpdater(self.config, self.project_root, self.logger)
        self.docker_manager = DockerManager(self.project_root, self.logger, self.config)
        self.migration_manager = MigrationManager(self.config, self.project_root, self.logger, self.formatter)
        self.compose_config_manager = ComposeConfigManager(self.config, self.logger)
        
        # Получаем настройки из конфига (сохраняем строки, разрешаем при использовании)
        docker_compose_config = self.config.get('docker_compose', {})
        self.dc_config_path_str = docker_compose_config.get('dc_config_path', '~/.dc_config')
        # Дефолтные имена контейнеров и сервисов больше не используются - имена определяются из compose файлов
        dc_install = docker_compose_config.get('dc_install', {})
        self.dc_install_root_path = dc_install.get('root_path', '/usr/local/bin')
        self.dc_install_user_path_str = dc_install.get('user_path', '~/.local/bin')
        self.dc_install_shell_configs_str = dc_install.get('shell_configs', ['~/.bashrc', '~/.profile'])
        
        # Данные обновления
        self.environment = None
        self.current_version = None
        self.new_version = None
        self.backup_path = None
    
    def _resolve_path(self, path_str: str) -> Path:
        """Разрешает путь с ~ в абсолютный Path"""
        if path_str.startswith('~'):
            return Path.home() / path_str[2:].lstrip('/')
        return Path(path_str)
    
    def _determine_environment(self) -> str:
        """Определяет окружение"""
        # Запрашиваем у пользователя
        while True:
            env = input("Выберите окружение (test/prod): ").strip().lower()
            if env in ['test', 'prod']:
                return env
            print("❌ Неверный выбор. Используйте 'test' или 'prod'")
    
    def _select_version(self, repo_path: Path, branch: str) -> Optional[str]:
        """Выбирает версию: автоматически (последняя) или вручную"""
        # Сначала пытаемся получить последнюю версию
        latest_version = self.version_manager.get_version_from_repo(repo_path, branch)
        
        if latest_version:
            self.formatter.print_info(f"📌 Последняя версия на ветке {branch}: {latest_version}")
            self.formatter.print_separator()
            
            # Предлагаем выбор
            print("Выберите вариант:")
            print("1. Использовать последнюю версию (по умолчанию)")
            print("2. Выбрать версию вручную")
            
            choice = input("\nВаш выбор (1/2, Enter = 1): ").strip()
            
            if not choice or choice == '1':
                return latest_version
            elif choice == '2':
                return self._manual_version_selection(repo_path)
            else:
                self.formatter.print_error("Неверный выбор, используем последнюю версию")
                return latest_version
        else:
            # Если последняя версия не найдена, предлагаем ручной выбор
            self.formatter.print_warning("Не удалось найти версию на последнем коммите")
            self.formatter.print_info("Попробуйте выбрать версию вручную")
            return self._manual_version_selection(repo_path)
    
    def _manual_version_selection(self, repo_path: Path) -> Optional[str]:
        """Ручной выбор версии из списка доступных тегов"""
        # Получаем список доступных тегов (последние 10)
        available_versions = self.version_manager.list_available_tags(repo_path, limit=10)
        
        if not available_versions:
            self.formatter.print_error("Не найдено доступных тегов версий")
            # Предлагаем ввести версию вручную
            manual_version = input("Введите версию вручную (например, 1.0.0): ").strip()
            if manual_version:
                return self.version_manager.get_version_by_tag(repo_path, manual_version)
            return None
        
        self.formatter.print_section("📋 ДОСТУПНЫЕ ВЕРСИИ")
        for i, version in enumerate(available_versions, 1):
            self.formatter.print_info(f"{i}. {version}")
        
        # Запрашиваем выбор
        while True:
            try:
                choice = input(f"\nВыберите версию (1-{len(available_versions)}, или '0' для ввода вручную): ").strip()
                
                if choice == '0':
                    manual_version = input("Введите версию вручную (например, 1.0.0): ").strip()
                    if manual_version:
                        selected_version = self.version_manager.get_version_by_tag(repo_path, manual_version)
                        if selected_version:
                            return selected_version
                        self.formatter.print_error(f"Версия {manual_version} не найдена")
                        continue
                    else:
                        self.formatter.print_error("Версия не введена")
                        continue
                
                index = int(choice) - 1
                if 0 <= index < len(available_versions):
                    selected_version = available_versions[index]
                    self.formatter.print_success(f"Выбрана версия: {selected_version}")
                    return selected_version
                else:
                    self.formatter.print_error(f"Неверный выбор. Используйте число от 1 до {len(available_versions)}")
            except ValueError:
                self.formatter.print_error("Неверный формат. Введите число")
            except KeyboardInterrupt:
                self.formatter.print_info("\nВыбор версии отменен")
                return None
    
    def _confirm_update(self) -> bool:
        """Запрашивает подтверждение обновления"""
        self.formatter.print_section("📋 ПЛАН ОБНОВЛЕНИЯ")
        self.formatter.print_key_value("Окружение", self.environment)
        self.formatter.print_key_value("Текущая версия", self.current_version or 'не установлена')
        self.formatter.print_key_value("Новая версия", self.new_version)
        self.formatter.print_separator()
        
        from modules.utils.user_input import confirm
        return confirm("Продолжить обновление?", default=False)
    
    def _backup_database(self) -> Optional[str]:
        """Создает бэкап базы данных"""
        try:
            if self.migration_manager.auto_backup:
                backup_path = self.migration_manager.backup_database()
                if backup_path:
                    self.logger.info(f"Бэкап БД создан: {backup_path}")
                    return backup_path
                else:
                    self.logger.warning("Бэкап БД не создан")
                    return None
            return None
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа БД: {e}")
            return None
    
    def _is_container_running(self, container_name: str) -> bool:
        """Проверяет, запущен ли Docker контейнер"""
        try:
            import subprocess
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return container_name in result.stdout
        except Exception:
            return False
    
    def _run_subprocess_with_output(self, command: list, description: str = "Выполнение команды") -> int:
        """
        Запускает подпроцесс с выводом логов в реальном времени
        Возвращает код возврата процесса
        """
        subprocess_encoding = os.environ.get('PYTHONIOENCODING', 'utf-8')
        
        self.formatter.print_info(f"🔄 {description}...")
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
                universal_newlines=True,
                env=os.environ,
                encoding=subprocess_encoding,
                errors='replace'
            )
            
            start_time = time.time()
            
            # Читаем вывод в реальном времени
            while True:
                if process.poll() is not None:
                    break
                
                # Определяем платформу для выбора метода чтения
                if platform.system().lower() in ['linux', 'darwin']:
                    # Linux/macOS - используем select для неблокирующего чтения
                    try:
                        ready, _, _ = select.select([process.stdout], [], [], 0.1)
                        if ready:
                            output = process.stdout.readline()
                            if output:
                                # Выводим строку сразу
                                sys.stdout.write(output)
                                sys.stdout.flush()
                    except Exception:
                        time.sleep(0.1)
                else:
                    # Windows и другие системы - используем простой подход
                    try:
                        output = process.stdout.readline()
                        if output:
                            sys.stdout.write(output)
                            sys.stdout.flush()
                        else:
                            time.sleep(0.1)
                    except Exception:
                        time.sleep(0.1)
            
            # Ждем завершения процесса
            process.wait()
            elapsed = int(time.time() - start_time)
            
            if process.returncode == 0:
                self.formatter.print_success(f"✅ {description} завершено за {elapsed}с")
            else:
                self.formatter.print_error(f"❌ {description} завершено с ошибкой за {elapsed}с")
            
            return process.returncode
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска подпроцесса: {e}")
            self.formatter.print_error(f"Ошибка запуска подпроцесса: {e}")
            return 1
    
    def _run_migrations(self, db_backup_path: Optional[str] = None) -> bool:
        """
        Запускает миграции БД в подпроцессе (чтобы использовать новый код после обновления файлов)
        """
        try:
            self.formatter.print_info(f"Версия: {self.new_version}")
            
            # Запрашиваем подтверждение
            if self.migration_manager.require_confirmation:
                from modules.utils.user_input import confirm
                if not confirm("Запустить миграции БД?", default=False):
                    self.formatter.print_warning("Миграции пропущены")
                    return True
            
            # Определяем путь к скрипту deployment_manager.py
            deployment_script = self.project_root / "tools" / "deployment" / "deployment_manager.py"
            if not deployment_script.exists():
                self.formatter.print_error("Не найден скрипт deployment_manager.py")
                return False
            
            # Определяем путь к скрипту внутри контейнера (относительно /workspace)
            script_path_in_container = f"/workspace/tools/deployment/deployment_manager.py"
            
            # Формируем команду для запуска миграции внутри Docker контейнера
            # Это нужно, чтобы миграции видели 'postgres' через Docker сеть
            # Получаем container_name из compose файлов (обязательно)
            try:
                container_name = self.docker_manager.compose_manager.get_container_name(self.environment)
            except Exception as e:
                self.logger.error(f"Не удалось получить container_name из compose файлов: {e}")
                self.formatter.print_error(
                    f"Не удалось определить имя контейнера для окружения {self.environment} из compose файлов. "
                    f"Проверьте наличие файлов docker-compose.{self.environment}.yml и корректность их структуры."
                )
                return False
            
            if not container_name:
                self.formatter.print_error(
                    f"Не удалось определить имя контейнера для окружения {self.environment} из compose файлов. "
                    f"Убедитесь, что в compose файлах указан container_name для сервиса приложения."
                )
                return False
            
            # Проверяем, запущен ли контейнер
            compose_command = self.docker_manager.get_compose_command()
            if not self._is_container_running(container_name):
                self.formatter.print_warning(f"Контейнер {container_name} не запущен, запускаем миграцию на хосте")
                # Fallback: запускаем на хосте (для случаев, когда контейнер не запущен)
                command = [
                    sys.executable,
                    str(deployment_script),
                    "--migrate-only",
                    "--version", self.new_version,
                    "--environment", self.environment
                ]
            else:
                # Запускаем внутри контейнера через docker compose exec
                # Используем глобальные compose файлы
                base_config = self.compose_config_manager.get_base_config_path()
                env_config = self.compose_config_manager.get_config_path(self.environment)
                
                # Получаем имя сервиса из compose файлов (обязательно)
                try:
                    service_name = self.docker_manager.compose_manager.get_service_name(self.environment)
                except Exception as e:
                    self.logger.error(f"Не удалось получить service_name из compose файлов: {e}")
                    self.formatter.print_error(
                        f"Не удалось определить имя сервиса для окружения {self.environment} из compose файлов. "
                        f"Проверьте наличие файлов docker-compose.{self.environment}.yml и корректность их структуры."
                    )
                    return False
                
                if not service_name:
                    self.formatter.print_error(
                        f"Не удалось определить имя сервиса для окружения {self.environment} из compose файлов. "
                        f"Убедитесь, что в compose файлах определены сервисы."
                    )
                    return False
                
                command = compose_command + [
                    "-f", str(base_config),
                    "-f", str(env_config),
                    "exec", "-T",  # -T отключает TTY для автоматического режима
                    service_name,
                    "python", script_path_in_container,
                    "--migrate-only",
                    "--version", self.new_version,
                    "--environment", self.environment
                ]
            
            # Добавляем путь к бэкапу БД, если он есть
            if db_backup_path:
                # Путь к бэкапу внутри контейнера (относительно /workspace)
                backup_path_in_container = str(db_backup_path).replace(str(self.project_root), "/workspace")
                command.extend(["--db-backup", backup_path_in_container])
            
            # Запускаем миграцию в подпроцессе с выводом логов в реальном времени
            self.formatter.print_info("\n🔄 Запуск миграции БД в подпроцессе (используется новый код)...")
            return_code = self._run_subprocess_with_output(
                command,
                "Миграция БД"
            )
            
            if return_code != 0:
                self.formatter.print_error("Ошибка миграции БД в подпроцессе")
                if db_backup_path:
                    self.formatter.print_info("Восстанавливаем БД из последнего бэкапа...")
                    # Восстанавливаем через текущий migration_manager (он еще работает)
                    self.migration_manager.restore_database()
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска миграций в подпроцессе: {e}")
            if db_backup_path:
                self.formatter.print_info("Восстанавливаем БД из последнего бэкапа...")
                self.migration_manager.restore_database()
            return False
    
    def run(self) -> bool:
        """Запускает процесс обновления"""
        try:
            self.formatter.print_header("🔄 ОБНОВЛЕНИЕ СЕРВЕРА")
            
            # 1. Определение окружения
            self.formatter.print_step(1, 13, "Определение окружения")
            self.environment = self._determine_environment()
            # Устанавливаем переменную окружения для корректной работы с БД
            os.environ['ENVIRONMENT'] = self.environment
            self.formatter.print_success(f"Окружение: {self.environment}")
            
            # 1.1. Обновление конфига ~/.dc_config
            if self._update_dc_config():
                # Конфиг ~/.dc_config обновлен
                pass
            
            # 2. Чтение текущей версии
            self.formatter.print_step(2, 13, "Чтение текущей версии")
            self.current_version = self.version_manager.get_current_version()
            if self.current_version:
                self.formatter.print_success(f"Текущая версия: {self.current_version}")
            else:
                self.formatter.print_info("Текущая версия не найдена (первый запуск)")
            
            # 3. Клонирование репозитория
            self.formatter.print_step(3, 13, "Клонирование репозитория")
            repo_path = self.server_updater.clone_repository(self.environment)
            if not repo_path:
                self.formatter.print_error("Ошибка клонирования репозитория")
                return False
            self.formatter.print_success(f"Репозиторий клонирован: {repo_path}")
            
            # 4. Определение новой версии из git tag
            self.formatter.print_step(4, 13, "Определение новой версии")
            repo_config = self.config.get('server_update', {}).get('repository', {})
            branches = repo_config.get('branches', {})
            branch = branches.get(self.environment)
            if not branch:
                # Используем дефолтную ветку из конфига
                from modules.base import get_base
                branch = get_base().get_default_branch(repo_config)
            
            # Предлагаем выбор версии
            self.new_version = self._select_version(repo_path, branch)
            if not self.new_version:
                self.formatter.print_error("Не удалось определить версию")
                return False
            self.formatter.print_success(f"Выбранная версия: {self.new_version}")
            
            # 4.1. Переключение на коммит с выбранным тегом (если версия не последняя)
            latest_version = self.version_manager.get_version_from_repo(repo_path, branch)
            if latest_version and self.new_version != latest_version:
                self.formatter.print_info(f"Переключение на коммит с тегом {self.new_version}...")
                if not self.server_updater.checkout_to_tag(repo_path, self.new_version):
                    self.formatter.print_warning("Не удалось переключиться на тег, используем текущий коммит")
            
            # 5. Подтверждение обновления
            if not self._confirm_update():
                self.formatter.print_error("Обновление отменено пользователем")
                return False
            
            # 6. Создание бэкапа файлов
            self.formatter.print_step(6, 13, "Создание бэкапа файлов")
            self.backup_path = self.server_updater.backup_files()
            if not self.backup_path:
                self.formatter.print_error("Ошибка создания бэкапа файлов")
                return False
            self.formatter.print_success(f"Бэкап создан: {self.backup_path}")
            
            # 7. Создание бэкапа БД
            self.formatter.print_step(7, 13, "Создание бэкапа БД")
            db_backup_path = self._backup_database()
            if not db_backup_path:
                self.formatter.print_warning("Бэкап БД не создан (продолжаем)")
            
            # 8. Обновление файлов
            self.formatter.print_step(8, 13, "Обновление файлов")
            if not self.server_updater.update_files(repo_path):
                self.formatter.print_error("Ошибка обновления файлов")
                self.formatter.print_info("Восстанавливаем из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
                return False
            self.formatter.print_success("Файлы обновлены")
            
            # 8.1. Создание глобальной конфигурации Docker Compose (если нужно)
            if self.docker_manager.check_docker() and self.docker_manager.check_docker_compose():
                self.formatter.print_info("Проверка глобальной конфигурации Docker Compose...")
                if self.compose_config_manager.ensure_config_exists(self.environment, repo_path, self.project_root):
                    self.formatter.print_success("Глобальная конфигурация Docker Compose готова")
                else:
                    self.formatter.print_warning("Не удалось создать глобальную конфигурацию (не критично)")
            
            # 8.2. Восстановление настроек ресурсов Docker
            if self.docker_manager.check_docker() and self.docker_manager.check_docker_compose():
                if self.docker_manager.restore_resources_config(self.environment):
                    self.formatter.print_success("Настройки ресурсов Docker восстановлены из ~/.dc_config")
                else:
                    self.formatter.print_info("Настройки ресурсов Docker не найдены в ~/.dc_config (не критично)")
            
            # 9. Проверка и запуск миграций БД (в подпроцессе с новым кодом)
            self.formatter.print_step(9, 13, "Проверка миграций БД")
            if not self._run_migrations(db_backup_path):
                self.formatter.print_error("Ошибка миграций БД")
                self.formatter.print_info("Восстанавливаем файлы из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
                if db_backup_path:
                    self.formatter.print_info("Восстанавливаем БД из последнего бэкапа...")
                    self.migration_manager.restore_database()
                return False
            
            # 10. Обновление файла .version на сервере (для информации)
            self.formatter.print_step(10, 13, "Обновление версии")
            if not self.version_manager.write_version(self.new_version):
                self.formatter.print_warning("Не удалось обновить файл версии (не критично)")
            else:
                self.formatter.print_success(f"Версия обновлена: {self.new_version}")
            
            # 11. Сборка Docker образа
            self.formatter.print_step(11, 13, "Сборка Docker образа")
            if not self.docker_manager.check_docker():
                self.formatter.print_warning("Docker не найден, пропускаем сборку")
            elif not self.docker_manager.check_docker_compose():
                self.formatter.print_warning("docker-compose не найден, пропускаем сборку")
            else:
                # Для prod тегируем образ версией для возможности отката
                if not self.docker_manager.build_with_compose(self.environment, self.new_version):
                    self.formatter.print_warning("Ошибка сборки Docker образа (не критично)")
            
            # 12. Перезапуск контейнеров
            self.formatter.print_step(12, 13, "Перезапуск контейнеров")
            if self.docker_manager.check_docker() and self.docker_manager.check_docker_compose():
                if not self.docker_manager.restart_with_compose(self.environment):
                    self.formatter.print_warning("Ошибка перезапуска контейнеров (не критично)")
                else:
                    self.formatter.print_success("Контейнеры перезапущены")
            else:
                self.formatter.print_info("Docker не доступен, пропускаем перезапуск")
            
            # 13. Установка команды dc
            self.formatter.print_step(13, 13, "Установка команды dc")
            if self._install_dc_command():
                # Обновляем конфиг после установки команды
                self._update_dc_config()
            
            # Очистка временных файлов
            self.server_updater.cleanup()
            
            # Удаление бэкапа при успешном обновлении
            if self.backup_path:
                try:
                    import shutil
                    backup_path = Path(self.backup_path)
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                        self.logger.info(f"Бэкап удален: {self.backup_path}")
                        # Бэкап удален после успешного обновления
                        pass
                except Exception as e:
                    # Не критично, если не удалось удалить бэкап
                    self.logger.warning(f"Не удалось удалить бэкап {self.backup_path}: {e}")
            
            # Итоги
            self.formatter.print_header("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
            self.formatter.print_key_value("Версия", f"{self.current_version} → {self.new_version}")
            self.formatter.print_key_value("Окружение", self.environment)
            self.formatter.print_separator()
            
            return True
            
        except KeyboardInterrupt:
            self.formatter.print_warning("\nОбновление прервано пользователем")
            if self.backup_path:
                self.formatter.print_info("Восстанавливаем из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
            return False
        except subprocess.TimeoutExpired as e:
            self.formatter.print_error(f"\nТаймаут выполнения команды: {e}")
            self.logger.error(f"Таймаут выполнения команды: {e}")
            if self.backup_path:
                self.formatter.print_info("Восстанавливаем из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
            return False
        except subprocess.CalledProcessError as e:
            self.formatter.print_error(f"\nОшибка выполнения команды: {e}")
            self.logger.error(f"Ошибка выполнения команды: {e}")
            if self.backup_path:
                self.formatter.print_info("Восстанавливаем из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
            return False
        except FileNotFoundError as e:
            self.formatter.print_error(f"\nФайл или команда не найдены: {e}")
            self.logger.error(f"Файл или команда не найдены: {e}")
            if self.backup_path:
                self.formatter.print_info("Восстанавливаем из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
            return False
        except Exception as e:
            self.formatter.print_error(f"\nНеожиданная ошибка: {e}")
            self.logger.error(f"Неожиданная ошибка обновления: {e}")
            if self.backup_path:
                self.formatter.print_info("Восстанавливаем из бэкапа...")
                self.server_updater.restore_backup(self.backup_path)
            return False
    
    def _update_dc_config(self) -> bool:
        """Обновляет только container_name для текущего окружения в ~/.dc_config, сохраняя остальные настройки"""
        try:
            import os
            
            config_file = self._resolve_path(self.dc_config_path_str)
            
            # Если окружение не определено - пропускаем
            if not self.environment or not self.project_root:
                return False
            
            # Формируем ключи для окружения (path больше не нужен)
            container_name_key = f"{self.environment}_container_name"
            
            # Получаем container_name из docker-compose файлов (обязательно)
            try:
                container_name_value = self.docker_manager.compose_manager.get_container_name(self.environment)
            except Exception as e:
                self.logger.error(f"Не удалось получить container_name из docker-compose файлов: {e}")
                self.formatter.print_error(
                    f"Не удалось определить имя контейнера для окружения {self.environment} из compose файлов. "
                    f"Проверьте наличие файлов docker-compose.{self.environment}.yml и корректность их структуры."
                )
                return False
            
            if not container_name_value:
                self.formatter.print_error(
                    f"Не удалось определить имя контейнера для окружения {self.environment} из compose файлов. "
                    f"Убедитесь, что в compose файлах указан container_name для сервиса приложения."
                )
                return False
            
            # Читаем существующий конфиг если есть
            config_lines = []
            has_header = False
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_lines = f.readlines()
                        # Проверяем, есть ли уже заголовок
                        for line in config_lines:
                            if line.strip().startswith('#') and 'Конфигурация для команды dc' in line:
                                has_header = True
                                break
                except Exception as e:
                    self.logger.warning(f"Не удалось прочитать конфиг: {e}")
                    config_lines = []
            
            # Обновляем только конкретные ключи, сохраняя остальные настройки
            new_lines = []
            container_name_updated = False
            
            for line in config_lines:
                line_stripped = line.strip()
                
                # Пропускаем все {env}_path (больше не нужны для всех окружений)
                if line_stripped.endswith("_path=") or (line_stripped.startswith("test_path=") or line_stripped.startswith("prod_path=")):
                    # Удаляем строку с path - больше не нужна
                    continue
                
                # Удаляем старые service_name записи (имя сервиса теперь определяется автоматически)
                if line_stripped.endswith("_service_name=") or line_stripped.startswith("test_service_name=") or line_stripped.startswith("prod_service_name="):
                    # Удаляем строку с service_name - больше не нужна
                    continue
                
                # Обновляем container_name для текущего окружения
                if line_stripped.startswith(f"{container_name_key}="):
                    new_lines.append(f"{container_name_key}={container_name_value}\n")
                    container_name_updated = True
                    continue
                
                # Оставляем все остальные строки как есть (включая комментарии и другие настройки)
                new_lines.append(line)
            
            # Если конфиг был пустой или ключи не найдены - добавляем их
            if not has_header and not config_lines:
                new_lines.insert(0, "# Конфигурация для команды dc\n")
                new_lines.insert(1, "# Формат: KEY=VALUE\n")
                new_lines.insert(2, "\n")
            
            # Добавляем недостающий container_name в конец файла
            if not container_name_updated:
                # Убираем лишние пустые строки в конце
                while new_lines and new_lines[-1].strip() == '':
                    new_lines.pop()
                new_lines.append(f"{container_name_key}={container_name_value}\n")
            
            # Записываем обновленный конфиг
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
                
                # Устанавливаем права доступа (только для владельца)
                try:
                    os.chmod(config_file, 0o600)
                except (OSError, AttributeError):
                    pass  # Игнорируем ошибки на Windows
                
                self.logger.info(f"Конфиг обновлен: {container_name_key}={container_name_value}")
                return True
                
            except Exception as e:
                self.logger.warning(f"Не удалось записать конфиг: {e}")
                return False
                
        except Exception as e:
            self.logger.warning(f"Ошибка обновления конфига: {e}")
            return False
    
    def _install_dc_command(self) -> bool:
        """Устанавливает глобальную команду dc для управления docker-compose"""
        try:
            compose_script = self.project_root / "docker" / "compose"
            
            # Проверяем существование скрипта
            if not compose_script.exists():
                self.formatter.print_warning("Скрипт docker/compose не найден, пропускаем установку")
                return False
            
            # Определяем директорию для установки
            # Проверяем права root (кроссплатформенно)
            is_root = False
            try:
                # Unix/Linux/Mac
                is_root = os.geteuid() == 0
            except AttributeError:
                # Windows - проверяем через переменную окружения
                is_root = os.environ.get('USERNAME', '').lower() == 'administrator' or \
                         os.environ.get('USER', '').lower() == 'root'
            
            if is_root:
                install_dir = Path(self.dc_install_root_path)
            else:
                install_dir = self._resolve_path(self.dc_install_user_path_str)
                install_dir.mkdir(parents=True, exist_ok=True)
            
            target = install_dir / "dc"
            
            # Копируем скрипт
            shutil.copy2(compose_script, target)
            
            # Делаем исполняемым (на Unix системах)
            try:
                os.chmod(target, 0o755)
            except (OSError, AttributeError):
                # Windows - права устанавливаются автоматически
                pass
            
            # Добавляем в PATH если нужно (для обычных пользователей)
            if not is_root:
                path_export = f'export PATH="$PATH:{install_dir}"'
                
                # Проверяем и добавляем в файлы конфигурации shell
                for shell_config_str in self.dc_install_shell_configs_str:
                    shell_config = self._resolve_path(shell_config_str)
                    if shell_config.exists():
                        try:
                            with open(shell_config, 'r', encoding='utf-8') as f:
                                content = f.read()
                            if path_export not in content:
                                with open(shell_config, 'a', encoding='utf-8') as f:
                                    f.write(f"\n{path_export}\n")
                        except Exception:
                            pass  # Игнорируем ошибки записи
            
            self.formatter.print_success(f"Команда 'dc' установлена в {target}")
            self.formatter.print_info("💡 Теперь можно использовать: dc start, dc stop, dc sv status и т.д.")
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Ошибка установки команды dc: {e}")
            self.formatter.print_warning(f"Не удалось установить команду dc: {e}")
            self.formatter.print_info("💡 Можно установить вручную: ./docker/compose install")
            return False


def main():
    """Главная функция"""
    script = UpdateServerScript()
    success = script.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
