#!/usr/bin/env python3
"""
Главный менеджер деплоя - унифицированная система управления деплоем
"""

import argparse
import os
import sys
from pathlib import Path

# Инициализируем базовый модуль (определяет project_root, загружает config и env)
from modules.base import get_base
from modules.ui.menu import Menu, MenuItem
from modules.ui.output import get_formatter


class DeploymentManager:
    """Главный класс менеджера деплоя"""
    
    def __init__(self):
        """Инициализация менеджера деплоя"""
        # Получаем базовый экземпляр (инициализирует все один раз)
        self.base = get_base()
        self.project_root = self.base.get_project_root()
        self.config = self.base.get_config()
        self.formatter = get_formatter()
    
    def _handle_deploy_to_repositories(self):
        """Обработка деплоя в репозитории"""
        self.formatter.print_info("Деплой в репозитории...")
        try:
            from scripts.deploy_to_repositories import DeployToRepositoriesScript
            script = DeployToRepositoriesScript()
            script.run()
        except ImportError:
            self.formatter.print_error("Не удалось импортировать модуль деплоя")
        except Exception as e:
            self.formatter.print_error(f"Ошибка при деплое: {e}")
    
    def _handle_update_server(self):
        """Обработка обновления сервера"""
        self.formatter.print_info("Обновление сервера...")
        try:
            from scripts.update_server import UpdateServerScript
            script = UpdateServerScript()
            success = script.run()
            
            # Если обновление прошло успешно, перезапускаем утилиту для использования нового кода
            if success:
                self._restart_self()
        except ImportError:
            self.formatter.print_error("Не удалось импортировать модуль обновления сервера")
        except Exception as e:
            self.formatter.print_error(f"Ошибка при обновлении сервера: {e}")
    
    def _restart_self(self):
        """
        Перезапускает утилиту деплоя, чтобы использовать новый код после обновления
        """
        try:
            self.formatter.print_info("\n🔄 Перезапуск утилиты деплоя для использования нового кода...")
            self.formatter.print_info("💡 Утилита будет перезапущена через несколько секунд...")
            
            # Небольшая задержка для вывода сообщения
            import time
            time.sleep(1)
            
            # Определяем путь к текущему скрипту
            script_path = Path(__file__).resolve()
            
            # Перезапускаем через os.execv (заменяет текущий процесс)
            os.execv(sys.executable, [sys.executable, str(script_path)])
            
        except Exception as e:
            self.formatter.print_warning(f"⚠️ Не удалось перезапустить утилиту: {e}")
            self.formatter.print_info("💡 Перезапустите утилиту вручную для использования нового кода")
    
    def _handle_rollback_image(self):
        """Обработка отката Docker образа (только для prod)"""
        self.formatter.print_info("Откат Docker образа...")
        try:
            from modules.update.docker_manager import DockerManager
            
            docker_manager = DockerManager(self.project_root, self.base.logger, self.config)
            
            # Проверяем доступность Docker
            if not docker_manager.check_docker():
                self.formatter.print_error("Docker не найден")
                return
            
            if not docker_manager.check_docker_compose():
                self.formatter.print_error("docker-compose не найден")
                return
            
            # Получаем список доступных версий
            available_versions = docker_manager.list_available_versions("prod")
            
            if not available_versions:
                self.formatter.print_warning("Нет доступных версий для отката")
                self.formatter.print_info("Версии создаются автоматически при сборке образа для prod окружения")
                return
            
            # Показываем список версий
            self.formatter.print_section("📋 Доступные версии для отката")
            for i, version in enumerate(available_versions, 1):
                self.formatter.print_info(f"{i}. {version}")
            
            # Запрашиваем выбор версии
            try:
                choice = input("\nВыберите версию для отката (или '0' для отмены): ")
                choice = choice.strip()
                if choice == '0':
                    self.formatter.print_info("Откат отменен")
                    return
                
                index = int(choice) - 1
                if index < 0 or index >= len(available_versions):
                    self.formatter.print_error("Неверный выбор")
                    return
                
                selected_version = available_versions[index]
                
                # Подтверждение
                self.formatter.print_warning(f"⚠️  Вы собираетесь откатить образ на версию {selected_version}")
                from modules.utils.user_input import confirm_required
                
                if not confirm_required("Продолжить?"):
                    self.formatter.print_info("Откат отменен")
                    return
                
                # Выполняем откат
                if docker_manager.rollback_image("prod", selected_version):
                    self.formatter.print_success(f"✅ Откат на версию {selected_version} выполнен успешно")
                else:
                    self.formatter.print_error("Ошибка при откате образа")
                    
            except ValueError:
                self.formatter.print_error("Неверный формат ввода")
            except KeyboardInterrupt:
                self.formatter.print_info("\nОткат отменен")
                
        except ImportError:
            self.formatter.print_error("Не удалось импортировать модули Docker")
        except Exception as e:
            self.formatter.print_error(f"Ошибка при откате образа: {e}")
    
    def _handle_database_work(self):
        """Обработка работы с БД"""
        self.formatter.print_info("Работа с БД...")
        try:
            from modules.database.database_manager import DatabaseManager
            db_manager = DatabaseManager(
                self.project_root,
                self.config,
                self.base.logger
            )
            db_manager.run()
        except Exception as e:
            self.formatter.print_error(f"Ошибка при работе с БД: {e}")
    
    def run_migration_only(self, version: str, environment: str, db_backup_path: str = None) -> bool:
        """
        Запускает только миграцию БД (используется в подпроцессе после обновления файлов)
        Этот метод вызывается с новым кодом, поэтому использует актуальные модели
        """
        import os
        
        # Устанавливаем переменную окружения для корректного определения порта PostgreSQL
        os.environ['ENVIRONMENT'] = environment
        
        try:
            from modules.migrations.migration_manager import MigrationManager
            from modules.utils.console_logger import ConsoleLogger
            
            logger = ConsoleLogger("migration_only")
            migration_manager = MigrationManager(self.config, self.project_root, logger, self.formatter)
            
            # Запускаем все миграции через единый метод migration_manager
            # Логика миграции остается в migration_manager, здесь только обертка
            return migration_manager.run_all_migrations(version, db_backup_path)
            
        except Exception as e:
            self.formatter.print_error(f"Ошибка запуска миграций: {e}")
            if db_backup_path:
                try:
                    from modules.migrations.migration_manager import MigrationManager
                    from modules.utils.console_logger import ConsoleLogger
                    logger = ConsoleLogger("migration_only")
                    migration_manager = MigrationManager(self.config, self.project_root, logger, self.formatter)
                    self.formatter.print_info("Восстанавливаем БД из бэкапа...")
                    migration_manager.restore_database()
                except Exception as restore_error:
                    self.formatter.print_error(f"Ошибка восстановления БД: {restore_error}")
            return False
    
    def _handle_cleanup_images(self):
        """Обработка очистки старых Docker образов"""
        self.formatter.print_info("Очистка старых Docker образов...")
        try:
            from modules.update.docker_manager import DockerManager
            
            docker_manager = DockerManager(self.project_root, self.base.logger, self.config)
            
            # Проверяем доступность Docker
            if not docker_manager.check_docker():
                self.formatter.print_error("Docker не найден")
                return
            
            # Запрашиваем окружение
            while True:
                env = input("Выберите окружение для очистки (test/prod, '0' для отмены): ")
                env = env.strip().lower()
                if env == '0':
                    self.formatter.print_info("Очистка отменена")
                    return
                if env in ['test', 'prod']:
                    break
                print("❌ Неверный выбор. Используйте 'test', 'prod' или '0' для отмены")
            
            # Получаем список образов с информацией
            images = docker_manager.list_images_with_info(env)
            
            if not images:
                self.formatter.print_info("ℹ️  Образы не найдены для очистки")
                return
            
            # Показываем список образов
            self.formatter.print_section("📋 Доступные образы")
            for i, img in enumerate(images, 1):
                self.formatter.print_info(f"{i}. Версия: {img['version']:20s} | Размер: {img['size']:10s} | Создан: {img['created']}")
            
            # Выбор режима очистки
            print("\nРежим очистки:")
            print("1. Автоматический - сохранить последние N версий")
            print("2. Ручной - выбрать конкретные образы для удаления")
            print("0. Отмена")
            
            while True:
                mode = input("Выберите режим (1/2/0): ")
                mode = mode.strip()
                if mode == '0':
                    self.formatter.print_info("Очистка отменена")
                    return
                if mode in ['1', '2']:
                    break
                print("❌ Неверный выбор. Используйте '1', '2' или '0' для отмены")
            
            versions_to_remove = None
            keep_versions = 5
            
            if mode == '1':
                # Автоматический режим
                while True:
                    try:
                        keep = input("Сколько последних версий сохранить? (по умолчанию 5, '0' для отмены): ")
                        keep = keep.strip()
                        if keep == '0':
                            self.formatter.print_info("Очистка отменена")
                            return
                        keep_versions = int(keep) if keep else 5
                        if keep_versions > 0:
                            break
                        print("❌ Количество должно быть больше 0")
                    except ValueError:
                        print("❌ Неверный формат. Используйте число или '0' для отмены")
                
                # Определяем какие версии будут удалены
                if len(images) > keep_versions:
                    versions_to_remove = [img['version'] for img in images[keep_versions:]]
                    self.formatter.print_warning(f"⚠️  Будет выполнена автоматическая очистка")
                    self.formatter.print_info(f"   Сохранятся последние {keep_versions} версий")
                    self.formatter.print_info(f"   Будут удалены {len(versions_to_remove)} старых версий:")
                    for version in versions_to_remove:
                        self.formatter.print_info(f"     - {version}")
                else:
                    self.formatter.print_info(f"ℹ️  Все версии будут сохранены (всего {len(images)}, требуется сохранить {keep_versions})")
                    return
            else:
                # Ручной режим
                self.formatter.print_info("\nВыберите образы для удаления (введите номера через запятую, например: 1,3,5)")
                self.formatter.print_info("Или 'all' для удаления всех, '0' для отмены")
                
                while True:
                    choice = input("Ваш выбор: ")
                    choice = choice.strip()
                    if choice == '0':
                        self.formatter.print_info("Очистка отменена")
                        return
                    if choice.lower() == 'all':
                        versions_to_remove = [img['version'] for img in images]
                        break
                    
                    try:
                        indices = [int(x.strip()) - 1 for x in choice.split(',')]
                        if all(0 <= idx < len(images) for idx in indices):
                            versions_to_remove = [images[idx]['version'] for idx in indices]
                            break
                        else:
                            print("❌ Некоторые номера вне диапазона")
                    except ValueError:
                        print("❌ Неверный формат. Используйте номера через запятую")
                
                self.formatter.print_warning(f"⚠️  Будут удалены следующие образы:")
                for version in versions_to_remove:
                    img = next((i for i in images if i['version'] == version), None)
                    if img:
                        self.formatter.print_info(f"   - {version} ({img['size']})")
            
            # Подтверждение
            self.formatter.print_info("\nТакже будут удалены dangling images (неиспользуемые промежуточные образы)")
            from modules.utils.user_input import confirm_required
            
            if not confirm_required("Продолжить?"):
                self.formatter.print_info("Очистка отменена")
                return
            
            # Выполняем очистку
            self.formatter.print_section("🧹 ОЧИСТКА ОБРАЗОВ")
            result = docker_manager.cleanup_old_images(env, keep_versions, versions_to_remove)
            
            # Выводим результаты
            if result["dangling_removed"] > 0:
                self.formatter.print_success("✅ Dangling images очищены")
            
            if result["old_versions_removed"] > 0:
                self.formatter.print_success(f"✅ Удалено старых версий: {result['old_versions_removed']}")
            
            if result["space_freed"] > 0:
                # Форматируем размер
                size_mb = result["space_freed"] / (1024 * 1024)
                if size_mb > 1024:
                    size_gb = size_mb / 1024
                    self.formatter.print_success(f"✅ Освобождено места: {size_gb:.2f} GB")
                else:
                    self.formatter.print_success(f"✅ Освобождено места: {size_mb:.2f} MB")
            
            if result["errors"]:
                self.formatter.print_warning("⚠️  Некоторые ошибки при очистке:")
                for error in result["errors"]:
                    self.formatter.print_warning(f"   - {error}")
            
            if result["dangling_removed"] == 0 and result["old_versions_removed"] == 0:
                self.formatter.print_info("ℹ️  Нечего очищать - все образы актуальны")
                
        except ImportError:
            self.formatter.print_error("Не удалось импортировать модули Docker")
        except Exception as e:
            self.formatter.print_error(f"Ошибка при очистке образов: {e}")
    
    def _handle_remove_environment(self):
        """Обработка удаления окружения"""
        self.formatter.print_info("Удаление окружения...")
        try:
            from modules.update.docker_manager import DockerManager
            
            docker_manager = DockerManager(self.project_root, self.base.logger, self.config)
            
            # Проверяем доступность Docker
            if not docker_manager.check_docker():
                self.formatter.print_error("Docker не найден")
                return
            
            if not docker_manager.check_docker_compose():
                self.formatter.print_error("docker-compose не найден")
                return
            
            # Запрашиваем окружение
            while True:
                env = input("Выберите окружение для удаления (test/prod, '0' для отмены): ")
                env = env.strip().lower()
                if env == '0':
                    self.formatter.print_info("Удаление отменено")
                    return
                if env in ['test', 'prod']:
                    break
                print("❌ Неверный выбор. Используйте 'test', 'prod' или '0' для отмены")
            
            # Предупреждение
            self.formatter.print_warning(f"⚠️  ВНИМАНИЕ: Будет полностью удалено окружение {env}")
            self.formatter.print_warning("   - Контейнеры будут остановлены и удалены")
            self.formatter.print_info("   - Volumes НЕ будут удалены (данные сохранятся)")
            self.formatter.print_info("   - Volumes можно удалить вручную при необходимости")
            
            # Спрашиваем про образы
            from modules.utils.user_input import confirm
            remove_images = confirm("Удалить образы Docker?", default=False)
            
            # Финальное подтверждение
            self.formatter.print_section("📋 ПЛАН УДАЛЕНИЯ")
            self.formatter.print_key_value("Окружение", env)
            self.formatter.print_key_value("Удалить контейнеры", "Да")
            self.formatter.print_key_value("Удалить volumes", "Нет (сохраняются)")
            self.formatter.print_key_value("Удалить образы", "Да" if remove_images else "Нет")
            
            from modules.utils.user_input import confirm_required
            if not confirm_required("\n⚠️  ВНИМАНИЕ: Это действие необратимо! Продолжить?"):
                self.formatter.print_info("Удаление отменено")
                return
            
            # Выполняем удаление
            self.formatter.print_section("🗑️ УДАЛЕНИЕ ОКРУЖЕНИЯ")
            if docker_manager.remove_environment(env, remove_images):
                self.formatter.print_success(f"✅ Окружение {env} успешно удалено")
                self.formatter.print_info("ℹ️  Volumes сохранены - данные не потеряны")
                if remove_images:
                    self.formatter.print_info("ℹ️  Образы удалены")
            else:
                self.formatter.print_error("❌ Ошибка при удалении окружения")
                
        except ImportError:
            self.formatter.print_error("Не удалось импортировать модули Docker")
        except Exception as e:
            self.formatter.print_error(f"Ошибка при удалении окружения: {e}")
    
    def run(self):
        """Запускает интерактивное меню"""
        # Создаем меню
        menu_items = [
            MenuItem("1", "🚀 Деплой в репозитории", self._handle_deploy_to_repositories, "Деплой кода во внешние репозитории"),
            MenuItem("2", "🔄 Обновление сервера", self._handle_update_server, "Обновление сервера из GitHub"),
            MenuItem("3", "🗄️ Работа с БД", self._handle_database_work, "Миграции и управление базой данных"),
            MenuItem("4", "⏪ Откат Docker образа", self._handle_rollback_image, "Откат образа на предыдущую версию (prod)"),
            MenuItem("5", "🧹 Очистка старых образов", self._handle_cleanup_images, "Удаление неиспользуемых и старых версий образов"),
            MenuItem("6", "🗑️ Удаление окружения", self._handle_remove_environment, "Полное удаление окружения (контейнеры, volumes, образы)"),
            MenuItem("0", "Выход", lambda: None, "Завершение работы"),
        ]
        
        menu = Menu("🚀 МЕНЕДЖЕР ДЕПЛОЯ", menu_items)
        menu.run()


def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(description='Менеджер деплоя')
    parser.add_argument('--migrate-only', action='store_true', help='Запустить только миграцию БД')
    parser.add_argument('--version', type=str, help='Версия для миграции (требуется с --migrate-only)')
    parser.add_argument('--environment', type=str, help='Окружение (требуется с --migrate-only)')
    parser.add_argument('--db-backup', type=str, help='Путь к бэкапу БД (опционально)')
    
    args = parser.parse_args()
    
    try:
        manager = DeploymentManager()
        
        # Если запущен с --migrate-only, запускаем только миграцию
        if args.migrate_only:
            if not args.version or not args.environment:
                formatter = get_formatter()
                formatter.print_error("Для --migrate-only требуются параметры --version и --environment")
                sys.exit(1)
            
            success = manager.run_migration_only(
                version=args.version,
                environment=args.environment,
                db_backup_path=args.db_backup
            )
            sys.exit(0 if success else 1)
        else:
            # Обычный режим - интерактивное меню
            manager.run()
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
        sys.exit(0)
    except Exception as e:
        formatter = get_formatter()
        formatter.print_error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
