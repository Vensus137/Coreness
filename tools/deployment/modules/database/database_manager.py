"""
Менеджер для работы с БД
Интерактивное меню для миграций, бэкапов и восстановления
"""

from pathlib import Path

from modules.migrations.migration_manager import MigrationManager
from modules.ui.menu import Menu, MenuItem
from modules.ui.output import get_formatter
from modules.update.version_manager import VersionManager


class DatabaseManager:
    """Класс для работы с БД через интерактивное меню"""
    
    def __init__(self, project_root: Path, config: dict, logger):
        """Инициализация менеджера БД"""
        self.project_root = project_root
        self.config = config
        self.logger = logger
        self.formatter = get_formatter()
        
        # Инициализируем менеджер миграций
        self.migration_manager = MigrationManager(
            config,
            project_root,
            logger,
            self.formatter
        )
        
        # Инициализируем менеджер версий
        self.version_manager = VersionManager(project_root, logger)
    
    def _ensure_environment_set(self):
        """
        Убеждается, что переменная ENVIRONMENT установлена
        Запрашивает у пользователя, если не установлена
        """
        import os
        environment = os.getenv('ENVIRONMENT', '').lower()
        if not environment or environment not in ['test', 'prod']:
            self.formatter.print_info("Выберите окружение для работы с БД:")
            while True:
                env_input = input("Окружение (test/prod): ").strip().lower()
                if env_input in ['test', 'prod']:
                    environment = env_input
                    # Устанавливаем переменную окружения для использования в DatabaseConnection
                    os.environ['ENVIRONMENT'] = environment
                    break
                else:
                    self.formatter.print_error("Используйте 'test' или 'prod'")
        return environment
    
    def _handle_universal_migration(self):
        """Обработка универсальной миграции"""
        try:
            self.formatter.print_section("🔄 УНИВЕРСАЛЬНАЯ МИГРАЦИЯ")
            
            # Определяем окружение для корректного подключения к БД
            self._ensure_environment_set()
            
            # Подтверждение
            from modules.utils.user_input import confirm
            if not confirm("Запустить универсальную миграцию?", default=False):
                self.formatter.print_info("Миграция отменена")
                return
            
            # Создаем бэкап перед миграцией
            backup_path = None
            if self.migration_manager.auto_backup:
                self.formatter.print_info("Создание бэкапа БД...")
                backup_path = self.migration_manager.backup_database()
                if backup_path:
                    self.formatter.print_success(f"Бэкап создан: {backup_path}")
                else:
                    self.formatter.print_warning("Не удалось создать бэкап, продолжаем без него")
            
            # Запускаем миграцию, передаем путь к бэкапу для удаления после успешной миграции
            if self.migration_manager.run_universal_migration(backup_path=backup_path):
                self.formatter.print_success("✅ Универсальная миграция завершена успешно")
            else:
                self.formatter.print_error("❌ Ошибка универсальной миграции")
                # Автоматически восстанавливаем бэкап при ошибке (без подтверждения)
                if backup_path:
                    self.formatter.print_info("Автоматическое восстановление БД из последнего бэкапа...")
                    if self.migration_manager.restore_database():
                        self.formatter.print_success("✅ БД восстановлена из бэкапа")
                    else:
                        self.formatter.print_error("❌ Ошибка восстановления БД")
        except KeyboardInterrupt:
            self.formatter.print_info("\nМиграция отменена пользователем")
        except Exception as e:
            self.formatter.print_error(f"❌ Критическая ошибка при миграции: {e}")
            self.logger.error(f"Ошибка универсальной миграции: {e}")
    
    def _handle_specific_migration(self):
        """Обработка специфической миграции"""
        try:
            self.formatter.print_section("🔄 СПЕЦИФИЧЕСКАЯ МИГРАЦИЯ")
            
            # Определяем окружение для корректного подключения к БД
            self._ensure_environment_set()
            
            # Получаем текущую версию
            current_version = self.version_manager.get_current_version()
            if not current_version:
                self.formatter.print_warning("Текущая версия не найдена")
                version_input = input("Введите версию для миграции (или '0' для отмены): ").strip()
                if version_input == '0':
                    return
                version = version_input
            else:
                self.formatter.print_info(f"Текущая версия: {current_version}")
                version_input = input(f"Введите версию для миграции (Enter для {current_version}): ").strip()
                version = version_input if version_input else current_version
            
            # Проверяем наличие специфической миграции
            if not self.migration_manager.check_specific_migration_needed(version):
                self.formatter.print_warning(f"Специфическая миграция для версии {version} не найдена")
                return
            
            # Подтверждение
            from modules.utils.user_input import confirm
            if not confirm(f"Запустить специфическую миграцию для версии {version}?", default=False):
                self.formatter.print_info("Миграция отменена")
                return
            
            # Создаем бэкап перед миграцией
            backup_path = None
            if self.migration_manager.auto_backup:
                self.formatter.print_info("Создание бэкапа БД...")
                backup_path = self.migration_manager.backup_database()
                if backup_path:
                    self.formatter.print_success(f"Бэкап создан: {backup_path}")
                else:
                    self.formatter.print_warning("Не удалось создать бэкап, продолжаем без него")
            
            # Запускаем миграцию
            if self.migration_manager.run_specific_migration(version):
                self.formatter.print_success(f"✅ Специфическая миграция для версии {version} завершена успешно")
            else:
                self.formatter.print_error(f"❌ Ошибка специфической миграции для версии {version}")
                # Автоматически восстанавливаем бэкап при ошибке (без подтверждения)
                if backup_path:
                    self.formatter.print_info("Автоматическое восстановление БД из последнего бэкапа...")
                    if self.migration_manager.restore_database():
                        self.formatter.print_success("✅ БД восстановлена из бэкапа")
                    else:
                        self.formatter.print_error("❌ Ошибка восстановления БД")
        except KeyboardInterrupt:
            self.formatter.print_info("\nМиграция отменена пользователем")
        except Exception as e:
            self.formatter.print_error(f"❌ Критическая ошибка при миграции: {e}")
            self.logger.error(f"Ошибка специфической миграции: {e}")
    
    def _handle_backup_database(self):
        """Обработка создания бэкапа БД"""
        try:
            self.formatter.print_section("💾 СОЗДАНИЕ БЭКАПА БД")
            
            # Определяем окружение для корректного подключения к БД
            self._ensure_environment_set()
            
            from modules.utils.user_input import confirm
            if not confirm("Создать бэкап БД?", default=False):
                self.formatter.print_info("Создание бэкапа отменено")
                return
            
            backup_path = self.migration_manager.backup_database()
            if backup_path:
                self.formatter.print_success(f"✅ Бэкап создан: {backup_path}")
            else:
                self.formatter.print_error("❌ Ошибка создания бэкапа")
        except KeyboardInterrupt:
            self.formatter.print_info("\nСоздание бэкапа отменено пользователем")
        except Exception as e:
            self.formatter.print_error(f"❌ Критическая ошибка при создании бэкапа: {e}")
            self.logger.error(f"Ошибка создания бэкапа: {e}")
    
    def _handle_restore_database(self):
        """Обработка восстановления БД из бэкапа"""
        self.formatter.print_section("🔄 ВОССТАНОВЛЕНИЕ БД ИЗ БЭКАПА")
        
        # Определяем окружение для корректного подключения к БД
        self._ensure_environment_set()
        
        # Получаем список доступных бэкапов из директории из глобальных настроек
        from modules.base import get_base
        base = get_base()
        global_settings = base.get_global_settings()
        backup_dir_config = global_settings.get('backup_dir', 'data/backups')
        backups_dir = self.project_root / backup_dir_config
        if not backups_dir.exists():
            self.formatter.print_warning("Директория бэкапов не найдена")
            return
        
        # Получаем тип БД для фильтрации файлов
        db_connection = self.migration_manager._get_db_connection()
        db_config = db_connection.get_database_config()
        db_type = db_config.get('type')
        
        # Определяем расширение файла в зависимости от типа БД
        if db_type == 'sqlite':
            extension = '.bak.gz'
        elif db_type == 'postgresql':
            extension = '.sql.gz'
        else:
            self.formatter.print_error(f"Неподдерживаемый тип БД: {db_type}")
            return
        
        # Получаем список файлов бэкапов
        backup_files = []
        for file_path in backups_dir.iterdir():
            if file_path.is_file() and file_path.name.endswith(extension):
                backup_files.append((file_path.name, file_path.stat().st_mtime))
        
        if not backup_files:
            self.formatter.print_warning("Нет доступных бэкапов")
            return
        
        # Сортируем по времени модификации (новые первыми)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # Показываем список бэкапов
        self.formatter.print_info("Доступные бэкапы:")
        for i, (backup_file, _) in enumerate(backup_files[:10], 1):  # Показываем последние 10
            self.formatter.print_info(f"  {i}. {backup_file}")
        
        # Запрашиваем выбор
        try:
            choice = input("\nВыберите бэкап для восстановления (или '0' для отмены): ").strip()
            if choice == '0':
                self.formatter.print_info("Восстановление отменено")
                return
            
            index = int(choice) - 1
            if index < 0 or index >= len(backup_files):
                self.formatter.print_error("Неверный выбор")
                return
            
            selected_backup_file = backup_files[index][0]
            
            # Подтверждение
            self.formatter.print_warning(f"⚠️  Вы собираетесь восстановить БД из бэкапа: {selected_backup_file}")
            self.formatter.print_warning("⚠️  Все текущие данные будут заменены!")
            from modules.utils.user_input import confirm_required
            
            if not confirm_required("Продолжить?"):
                self.formatter.print_info("Восстановление отменено")
                return
            
            # Восстанавливаем
            if self.migration_manager.restore_database(selected_backup_file):
                self.formatter.print_success("✅ БД восстановлена из бэкапа")
            else:
                self.formatter.print_error("❌ Ошибка восстановления БД")
                
        except ValueError:
            self.formatter.print_error("Неверный формат ввода")
        except KeyboardInterrupt:
            self.formatter.print_info("\nВосстановление отменено")
    
    def run(self):
        """Запускает интерактивное меню работы с БД"""
        menu_items = [
            MenuItem("1", "🔄 Универсальная миграция", self._handle_universal_migration, "Автоматическая миграция всех таблиц"),
            MenuItem("2", "📦 Специфическая миграция", self._handle_specific_migration, "Версионированная миграция для конкретной версии"),
            MenuItem("3", "💾 Создать бэкап БД", self._handle_backup_database, "Создание резервной копии базы данных"),
            MenuItem("4", "🔄 Восстановить из бэкапа", self._handle_restore_database, "Восстановление БД из резервной копии"),
            MenuItem("0", "Выход", lambda: None, "Возврат в главное меню"),
        ]
        
        menu = Menu("🗄️ РАБОТА С БАЗОЙ ДАННЫХ", menu_items)
        menu.run()

