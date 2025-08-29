import os
import shutil
import subprocess
import tempfile
import zipfile
import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# === ГЛОБАЛЬНАЯ КОНФИГУРАЦИЯ ===
# Настройки репозиториев для разных версий
VERSIONS = {
    'base': {
        'name': "Base",
        'description': "Базовая версия",
        'repo_url': "https://github.com/Vensus137/Coreness",
        'branch': "main",
        'update_token_env': None  # Base версия не требует токена
    },
    'pro': {
        'name': "Pro", 
        'description': "Профессиональная версия",
        'repo_url': "https://github.com/Vensus137/coreness-pro",
        'branch': "main",
        'update_token_env': "UPDATE_TOKEN_PRO"
    }
}

# Папки и файлы для чистой синхронизации (удаляются и пересоздаются)
CLEAN_SYNC_ITEMS = [
    "plugins",              # Полная синхронизация всех плагинов
    "tools",                # Полная синхронизация инструментов
    "app",                  # Полная синхронизация приложения
    # Можно добавить конкретные файлы для удаления
    # "old_config.yaml",   # Удалить устаревший конфиг
    # "deprecated.py",     # Удалить устаревший скрипт
]

# Заводские конфиги (обновляются отдельно по запросу)
FACTORY_CONFIGS = [
    "config",
    "resources"
]

# Папки для исключения из обновления (всегда исключаются)
EXCLUDE_PATHS = [
    "logs",
    "data",
    ".git",
    ".github",
    ".gitignore",
    ".venv",           # Виртуальное окружение Python
    "venv",            # Альтернативное название виртуального окружения
    "__pycache__",     # Кэш Python
    "*.pyc",           # Скомпилированные Python файлы
    ".pytest_cache",   # Кэш pytest
    ".coverage",       # Файлы покрытия тестами
]

# Настройки бэкапа
BACKUP_CONFIG = {
    'default_keep': True,  # По умолчанию сохранять бэкап
    'dir_name': ".core_update_backup"
}

def load_config():
    """Возвращает конфигурацию из глобальных переменных"""
    return {
        'versions': VERSIONS,
        'clean_sync_items': CLEAN_SYNC_ITEMS,
        'factory_configs': FACTORY_CONFIGS,
        'exclude_paths': EXCLUDE_PATHS,
        'backup': BACKUP_CONFIG
    }

def get_available_versions(config):
    """Возвращает список доступных версий"""
    return list(config['versions'].keys())

def validate_version(version, config):
    """Проверяет корректность введенной версии"""
    return version.lower() in config['versions']

def get_version_info(version, config):
    """Возвращает информацию о версии"""
    return config['versions'].get(version.lower())

def get_github_token(version_info):
    """Получает GitHub токен для версии"""
    # Base версия не требует токена (публичный репозиторий)
    if version_info['update_token_env'] is None:
        print("ℹ️ Base версия - публичный репозиторий, токен не требуется")
        return None
    
    # Pro версия требует токен (приватный репозиторий)
    token_env = version_info['update_token_env']
    token = os.getenv(token_env)
    if not token:
        print(f"⚠️ Переменная окружения {token_env} не установлена")
        return None
    return token

def get_unique_backup_dir(base_dir):
    """Создает уникальное имя для папки бэкапа"""
    if not os.path.exists(base_dir):
        return base_dir
    
    # Добавляем временную метку
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_dir = f"{base_dir}_{timestamp}"
    
    # Если и с меткой существует, добавляем счетчик
    counter = 1
    while os.path.exists(unique_dir):
        unique_dir = f"{base_dir}_{timestamp}_{counter}"
        counter += 1
    
    return unique_dir

def request_manual_token():
    """Запрашивает токен вручную"""
    print("\n🔑 Введите GitHub токен:")
    
    while True:
        token = input("GitHub токен: ").strip()
        if token:
            return token
        print("❌ Токен не может быть пустым. Попробуйте снова.")

def find_project_root():
    """Автоматически находит корневую папку проекта"""
    # Начинаем с директории, где лежит скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Проверяем, находится ли скрипт в папке tools/
    is_in_tools = os.path.basename(script_dir) == "tools"
    
    if is_in_tools:
        # Скрипт в папке tools/ - это обновление существующего проекта
        # Разворачиваем в папке над tools/ (корень проекта)
        project_dir = os.path.dirname(script_dir)
        print(f"📍 Режим обновления: разворачиваю в корне проекта: {project_dir}")
        return project_dir
    else:
        # Скрипт не в папке tools/ - это первая установка
        # Разворачиваем в папке скрипта
        print(f"📍 Режим первой установки: разворачиваю в папке скрипта: {script_dir}")
        return script_dir

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def is_excluded(path, config):
    """Проверяет, исключен ли путь из обновления"""
    for excl in config['exclude_paths']:
        # Точное совпадение
        if path == excl:
            return True
        
        # Проверка на начало пути (для папок)
        if excl.endswith(os.sep) or not excl.endswith('*'):
            if path.startswith(excl + os.sep):
                return True
        
        # Проверка wildcard паттернов
        if excl.endswith('*'):
            pattern = excl[:-1]  # Убираем *
            if path.startswith(pattern):
                return True
        
        # Проверка на вхождение в папку (например, __pycache__ в любой папке)
        if excl in path.split(os.sep):
            return True
    
    return False

def is_clean_sync_item(path, config):
    """Проверяет, нужно ли полностью синхронизировать элемент"""
    return path in config['clean_sync_items']

def remove_old(path):
    """Удаляет старый файл или папку"""
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

def copy_new(src, dst):
    """Копирует новый файл или папку"""
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

def backup_paths(backup_dir, config, include_factory_configs=False):
    """Создает резервную копию всех файлов проекта (кроме исключений)"""
    # Получаем абсолютный путь к папке проекта
    project_root = find_project_root()
    
    os.makedirs(backup_dir, exist_ok=True)
    
    total_items = 0
    processed_items = 0
    
    # Подсчитываем общее количество элементов для копирования
    for item in os.listdir(project_root):
        if os.path.exists(os.path.join(project_root, item)):
            # Проверяем исключения
            if is_excluded(item, config):
                continue
            # Проверяем заводские конфиги
            if not include_factory_configs and item in config['factory_configs']:
                continue
            total_items += 1
    
    print(f"📁 Всего элементов для резервного копирования: {total_items}")
    
    # Копируем все файлы и папки из папки проекта
    for item in os.listdir(project_root):
        if not os.path.exists(os.path.join(project_root, item)):
            continue
            
        # Проверяем исключения
        if is_excluded(item, config):
            print(f"⏭ Пропускаю исключённый: {item}")
            continue
            
        # Проверяем заводские конфиги
        if not include_factory_configs and item in config['factory_configs']:
            print(f"⏭ Пропускаю заводской конфиг: {item}")
            continue
            
        try:
            processed_items += 1
            print(f"🗂 Копирую {processed_items}/{total_items}: {item}")
            
            src_path = os.path.join(project_root, item)
            backup_path = os.path.join(backup_dir, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, backup_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, backup_path)
        except Exception as e:
            print(f"⚠️ Ошибка копирования {item}: {e}")
            continue
    
    print(f"✅ Резервное копирование завершено: {processed_items}/{total_items} элементов")

def restore_backup(backup_dir, config, include_factory_configs=False):
    """Восстанавливает из резервной копии"""
    # Получаем абсолютный путь к папке проекта
    project_root = find_project_root()
    
    errors = []
    
    if not os.path.exists(backup_dir):
        print(f"⚠️ Не найден бэкап: {backup_dir}")
        return ["backup_dir_not_found"]
    
    # Восстанавливаем все файлы из бэкапа
    for item in os.listdir(backup_dir):
        try:
            backup_path = os.path.join(backup_dir, item)
            target_path = os.path.join(project_root, item)
            
            # Проверяем исключения
            if is_excluded(item, config):
                print(f"⏭ Пропускаю исключённый при восстановлении: {item}")
                continue
                
            # Проверяем заводские конфиги
            if not include_factory_configs and item in config['factory_configs']:
                print(f"⏭ Пропускаю заводской конфиг при восстановлении: {item}")
                continue
            
            # Удаляем существующий файл/папку
            if os.path.exists(target_path):
                remove_old(target_path)
            
            # Восстанавливаем из бэкапа
            if os.path.isdir(backup_path):
                shutil.copytree(backup_path, target_path)
            else:
                shutil.copy2(backup_path, target_path)
                
        except Exception as e:
            print(f"❌ Ошибка восстановления {item}: {e}")
            errors.append(item)
    
    return errors

def remove_backup(backup_dir):
    """Удаляет резервную копию"""
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)

def install_dependencies():
    """Устанавливает зависимости из requirements.txt"""
    # Получаем абсолютный путь к папке проекта
    project_root = find_project_root()
    requirements_path = os.path.join(project_root, "requirements.txt")
    
    print(f"📦 Устанавливаю зависимости из {requirements_path}...")
    try:
        pip_result = subprocess.run([
            "python", "-m", "pip", "install", "-r", requirements_path
        ], capture_output=True, text=True)
        print(pip_result.stdout)
        if pip_result.returncode != 0:
            print(f"❌ Ошибка установки зависимостей: {pip_result.stderr}")
            raise Exception("Ошибка установки зависимостей")
        print("✅ Зависимости установлены успешно!")
    except Exception as e:
        print(f"❌ Ошибка при установке зависимостей: {e}")
        raise

def run_database_migration():
    """Запускает миграцию базы данных"""
    # Получаем абсолютный путь к папке проекта
    project_root = find_project_root()
    db_manager_path = os.path.join(project_root, "tools", "database_manager.py")
    
    if not os.path.exists(db_manager_path):
        print("⚠️ Скрипт database_manager.py не найден, пропускаю миграцию БД")
        return
    
    print("🗄 Запускаю миграцию базы данных...")
    
    # Проверяем наличие базы данных (но не блокируем миграцию)
    db_path = os.path.join(project_root, "data", "bot_core.db")
    if not os.path.exists(db_path):
        print("⚠️ База данных не найдена, будет создана автоматически")
    
    try:
        # Настройки для корректной работы с Unicode на Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        print(f"🔍 Запускаю: python {db_manager_path} --all --migrate")
        
        # Запускаем миграцию всех таблиц с правильной кодировкой для Windows
        migration_result = subprocess.run([
            "python", db_manager_path, "--all", "--migrate"
        ], capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, cwd=project_root)
        
        print(f"🔍 Код возврата: {migration_result.returncode}")
        
        if migration_result.returncode == 0:
            print("✅ Миграция базы данных завершена успешно!")
            if migration_result.stdout:
                print("📤 Вывод:")
                print(migration_result.stdout)
        else:
            print(f"❌ Ошибка миграции базы данных:")
            if migration_result.stdout:
                print("📤 STDOUT:")
                print(migration_result.stdout)
            if migration_result.stderr:
                print("📤 STDERR:")
                print(migration_result.stderr)
            print("⚠️ Миграция пропущена, но обновление продолжено")
            print("💡 Рекомендуется запустить миграцию вручную:")
            print(f"   cd {project_root}")
            print(f"   python tools\\database_manager.py --all --migrate")
            
    except Exception as e:
        print(f"❌ Ошибка при запуске миграции БД: {e}")
        print("⚠️ Миграция пропущена, но обновление продолжено")
        print("💡 Рекомендуется запустить миграцию вручную:")
        print(f"   cd {project_root}")
        print(f"   python tools\\database_manager.py --all --migrate")

# === ОСНОВНОЙ СКРИПТ ===
def main():
    print("⚡️ Core Updater: сервис обновления ядра\n")
    
    # ⚠️ ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ
    print("⚠️  ВАЖНО: Запускайте скрипт через консоль/терминал!")
    print("   ❌ НЕ запускайте двойным кликом - это может привести к проблемам")
    print("   ✅ Правильный запуск: python core_updater.py")
    print("   💡 Если скрипт уже запущен, закройте его и запустите через консоль\n")

    # Проверяем путь на наличие кириллицы
    project_root = find_project_root()
    if any(ord(char) > 127 for char in project_root):
        print("⚠️ ВНИМАНИЕ: Путь к проекту содержит не-ASCII символы (кириллицу)!")
        print("   Это может вызвать проблемы с кодировкой на Windows.")
        print("   Рекомендуется использовать пути только с латинскими символами.")
        print("   Пример: E:\\Projects\\Coreness\\Development\\Builds\\Coreness Base")
        print()
        continue_update = input("Продолжить обновление? (Y/N): ").strip().lower()
        if continue_update != 'y':
            print("❌ Обновление отменено.")
            return

    # Загружаем конфигурацию
    config = load_config()
    if not config:
        print("❌ Не удалось загрузить конфигурацию. Завершение работы.")
        return

    # Показываем доступные версии
    available_versions = get_available_versions(config)
    print("📋 Доступные версии:")
    for version in available_versions:
        version_info = config['versions'][version]
        print(f"  • {version.upper()}: {version_info['name']} - {version_info['description']}")

    # Запрашиваем версию
    while True:
        selected_version = input(f"\nВведите версию для обновления ({', '.join(available_versions)}): ").strip().lower()
        if validate_version(selected_version, config):
            break
        print(f"❌ Неверная версия. Доступные: {', '.join(available_versions)}")

    version_info = get_version_info(selected_version, config)
    print(f"\n✅ Выбрана версия: {version_info['name']} ({version_info['description']})")

    # Запрашиваем обновление заводских конфигов
    update_factory_configs = input("\nОбновить заводские конфиги? (Y/N, по умолчанию N): ").strip().lower() == 'y'

    if update_factory_configs:
        print("🛠 Включено обновление заводских конфигов!")
    else:
        print("📁 Заводские конфиги будут пропущены (обновляются отдельно)")

    print(f"\n📁 Будут обновлены ВСЕ файлы из репозитория, кроме:")
    print(f"  • Исключений: {', '.join(config['exclude_paths'])}")
    if not update_factory_configs:
        print(f"  • Заводских конфигов: {', '.join(config['factory_configs'])}")
    
    print(f"\n🗑 Чистая синхронизация (полное удаление и пересоздание):")
    print(f"  • {', '.join(config['clean_sync_items'])}")
    print(f"  • Остальные файлы обновляются без удаления устаревших")

    # Создаем резервную копию
    base_backup_dir = os.path.join(project_root, config['backup']['dir_name'])
    backup_dir = get_unique_backup_dir(base_backup_dir)
    print(f"\n🗂 Создаю резервную копию в {backup_dir}...")
    backup_paths(backup_dir, config, update_factory_configs)

    backup_restored = False
    try:
        # Проверяем наличие токена в окружении
        github_token = get_github_token(version_info)
        
        # Определяем заголовки для запроса
        if github_token:
            # Pro версия - используем токен
            print(f"🔑 Подключаюсь с токеном для Pro версии...")
            headers = {"Authorization": f"token {github_token}"}
        else:
            # Base версия - без токена
            print(f"🔓 Скачиваю Base версию без токена (публичный репозиторий)...")
            headers = {}
        
        try:
            # Скачиваем архив с GitHub
            repo_url = version_info['repo_url']
            branch = version_info['branch']
            
            # Пробуем разные методы скачивания
            download_methods = [
                # 1. Archive по ветке (универсальный)
                f"{repo_url}/archive/refs/heads/{branch}.zip",
                # 2. Latest release (если есть)
                f"{repo_url}/releases/latest/download/source.zip",
            ]
            
            print(f"🔽 Скачиваю из репозитория: {repo_url}")
            print(f"   Ветка: {branch}")
            
            # Пробуем разные методы скачивания
            response = None
            for i, zip_url in enumerate(download_methods, 1):
                print(f"   🔍 Метод {i}: {zip_url}")
                
                try:
                    response = requests.get(zip_url, headers=headers)
                    if response.status_code == 200:
                        print(f"   ✅ Успешно! Размер: {len(response.content)} байт")
                        break
                    else:
                        print(f"   ❌ Статус: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")
            
            if not response or response.status_code != 200:
                if github_token:
                    # Pro версия - пробуем с ручным токеном
                    print(f"❌ Не удалось скачать с токеном из окружения")
                    print("ℹ️ Пробую запросить токен вручную...")
                    github_token = request_manual_token()
                    headers = {"Authorization": f"token {github_token}"}
                    
                    # Повторяем попытку с ручным токеном
                    print(f"🔽 Повторная попытка скачивания с ручным токеном...")
                    
                    response = None
                    for i, zip_url in enumerate(download_methods, 1):
                        print(f"   🔍 Метод {i}: {zip_url}")
                        
                        try:
                            response = requests.get(zip_url, headers=headers)
                            if response.status_code == 200:
                                print(f"   ✅ Успешно! Размер: {len(response.content)} байт")
                                break
                            else:
                                print(f"   ❌ Статус: {response.status_code}")
                        except Exception as e:
                            print(f"   ❌ Ошибка: {e}")
                    
                    if not response or response.status_code != 200:
                        raise Exception("Ошибка скачивания: все методы не удались")
                else:
                    # Base версия - показываем детали ошибки
                    print(f"❌ Не удалось скачать Base версию")
                    print("ℹ️ Проверьте:")
                    print("   • Доступность репозитория")
                    print("   • Наличие ветки main")
                    print("   • Сетевые настройки")
                    raise Exception("Ошибка скачивания Base версии: все методы не удались")
                    
        except Exception as e:
            if github_token:
                # Pro версия - показываем ошибки с токеном
                print(f"❌ Ошибка скачивания Pro версии: {e}")
                print("ℹ️ Проверьте:")
                print("   • Правильность GitHub токена")
                print("   • Доступ к приватному репозиторию")
                print("   • Наличие релиза с архивом source.zip")
            else:
                # Base версия - показываем ошибки без токена
                print(f"❌ Ошибка скачивания Base версии: {e}")
                print("ℹ️ Проверьте:")
                print("   • Доступность публичного репозитория")
                print("   • Сетевые настройки")
            raise
        
        # Обрабатываем скачанный архив
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "repo.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)

            # Распаковываем архив
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            # Определяем корневую папку исходников
            repo_root = None
            for name in os.listdir(tmpdir):
                if os.path.isdir(os.path.join(tmpdir, name)) and name.endswith(f"-{branch}"):
                    repo_root = os.path.join(tmpdir, name)
                    break
            
            if not repo_root:
                raise Exception("Не удалось найти корневую папку исходников после распаковки!")


            
            # Обновляем все файлы и папки из репозитория
            print("♻️ Обновляю все файлы и папки...")
            for item in os.listdir(repo_root):
                # Проверяем исключения
                if is_excluded(item, config):
                    print(f"⏭ Пропускаю исключённый: {item}")
                    continue
                
                # Проверяем заводские конфиги
                if not update_factory_configs and item in config['factory_configs']:
                    print(f"⏭ Пропускаю заводской конфиг: {item}")
                    continue
                
                abs_old = os.path.join(project_root, item)
                abs_new = os.path.join(repo_root, item)
                
                # Проверяем тип синхронизации
                if is_clean_sync_item(item, config):
                    print(f"🗑 Чистая синхронизация: {item}")
                    remove_old(abs_old)
                    copy_new(abs_new, abs_old)
                else:
                    print(f"♻️ Обновляю: {item}")
                    remove_old(abs_old)
                    copy_new(abs_new, abs_old)

        # Устанавливаем зависимости
        install_dependencies()

        # Запускаем миграцию базы данных
        run_database_migration()

        print("✅ Обновление завершено успешно!")

        # Спрашиваем про удаление бэкапа
        if config['backup']['default_keep']:
            keep_backup = input("\nУдалить резервную копию? (Y/N, по умолчанию N): ").strip().lower() == 'y'
            if keep_backup:
                remove_backup(backup_dir)
                print("🗑 Резервная копия удалена.")
            else:
                print(f"💾 Резервная копия сохранена в {backup_dir}")
        else:
            remove_backup(backup_dir)

        # Если это первая установка (скрипт не в tools/), удаляем сам скрипт
        script_dir = os.path.dirname(os.path.abspath(__file__))
        is_in_tools = os.path.basename(script_dir) == "tools"
        
        if not is_in_tools:
            script_path = os.path.abspath(__file__)
            try:
                os.remove(script_path)
                print(f"🗑 Скрипт установки удален: {script_path}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить скрипт установки: {e}")

        print("\n🚀 Перезапустите бота для применения обновлений!")

    except Exception as e:
        print(f"❌ Ошибка обновления: {e}")
        print("⏪ Восстанавливаю из резервной копии...")
        
        errors = restore_backup(backup_dir, config, update_factory_configs)
        if errors:
            print(f"❌ Не удалось восстановить следующие файлы/папки: {errors}")
            print(f"❗ Бэкап сохранён в {backup_dir}. Восстановите вручную!")
        else:
            print("✅ Откат завершён. Проект восстановлен.")
            if config['backup']['default_keep']:
                print(f"💾 Резервная копия сохранена в {backup_dir}")
            else:
                remove_backup(backup_dir)
        backup_restored = True

    finally:
        # Чистим бэкап только если восстановление прошло успешно и не нужно сохранять
        if not backup_restored and not config['backup']['default_keep']:
            remove_backup(backup_dir)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("🔍 Детали ошибки:")
        import traceback
        traceback.print_exc()
        print("\n" + "="*50)
        print("💡 Нажмите Enter для выхода...")
        try:
            input()
        except:
            # Если input() не работает, используем os.system
            import os
            os.system("pause") 