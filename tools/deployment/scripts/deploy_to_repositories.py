#!/usr/bin/env python3
"""
Скрипт для деплоя в репозитории
Полностью самодостаточный, использует модули напрямую
"""

import sys
from datetime import datetime
from typing import List

# Инициализируем базовый модуль (определяет project_root, загружает config и env)
from modules.base import get_base
from modules.deploy.file_filter import FileFilter
from modules.deploy.git_handler import GitHandler
from modules.docs.changelog_parser import ChangelogParser
from modules.ui.output import Colors, get_formatter
from modules.utils.console_logger import ConsoleLogger


class DeployToRepositoriesScript:
    """Скрипт для деплоя в репозитории"""
    
    def __init__(self):
        """Инициализация"""
        # Получаем базовый экземпляр (инициализирует все один раз)
        self.base = get_base()
        self.project_root = self.base.get_project_root()
        self.config = self.base.get_config()
        
        # Инициализируем логгер и форматтер
        self.logger = ConsoleLogger("deploy_to_repositories")
        self.formatter = get_formatter()
        
        # Инициализируем компоненты (передаем project_root для единообразия)
        self.git_handler = GitHandler(self.config, self.logger, self.project_root)
        self.file_filter = FileFilter(self.config, self.logger, self.project_root)
        self.changelog_parser = ChangelogParser(self.project_root, self.config)
        
        # Инициализируем VersionManager для проверки тегов
        from modules.update.version_manager import VersionManager
        self.version_manager = VersionManager(self.project_root, self.logger)
        
        # Данные деплоя
        self.version = None
        self.date = None
    
    def _get_user_input(self, prompt: str, confirmation_prompt: str) -> str:
        """Получает ввод от пользователя с подтверждением"""
        while True:
            value = input(f"\n{prompt}: ").strip()
            if not value:
                print("❌ Значение не может быть пустым")
                continue
                
            confirm = input(f"{confirmation_prompt} ({value}): ").strip()
            if confirm == value:
                return value
            else:
                print("❌ Значения не совпадают, попробуйте снова")
    
    def _get_version_and_date(self):
        """Запрашивает версию и дату у пользователя с автоматическим определением из docs/CHANGELOG.md"""
        self.formatter.print_header("📋 ОПРЕДЕЛЕНИЕ ВЕРСИИ И ДАТЫ")
        
        # Пытаемся получить версию из docs/CHANGELOG.md
        version_info = self.changelog_parser.get_version_info()
        
        if version_info['found']:
            self.formatter.print_info(f"Найдена версия в {version_info['source']}:")
            self.formatter.print_key_value("Версия", version_info['version'], indent=3)
            self.formatter.print_key_value("Дата", version_info['date'], indent=3)
            
            from modules.utils.user_input import confirm
            if confirm("\nИспользовать найденную версию?", default=True):
                self.version = version_info['version']
                self.date = version_info['date']
                self.formatter.print_success(f"Используем версию: {self.version} от {self.date}")
            else:
                self._manual_version_input()
        else:
            self.formatter.print_warning(f"Версия в {version_info['source']} не найдена")
            self._manual_version_input()
        
        # Валидация даты
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            self.formatter.print_error("Неверный формат даты. Используйте YYYY-MM-DD")
            sys.exit(1)
        
        # Проверка существования тега в Git (предупреждение, но не инкремент)
        self._check_version_tag_exists()
    
    def _manual_version_input(self):
        """Ручной ввод версии и даты"""
        self.version = self._get_user_input(
            "Введите версию для деплоя (например: 1.2.3)",
            "Подтвердите версию"
        )
        self.formatter.print_success(f"Версия подтверждена: {self.version}")
        
        self.date = self._get_user_input(
            "Введите дату сборки (YYYY-MM-DD)",
            "Подтвердите дату"
        )
        self.formatter.print_success(f"Дата подтверждена: {self.date}")
    
    def _check_version_tag_exists(self):
        """
        Проверяет существование тега версии в Git (только предупреждение)
        
        Версия должна быть уже правильной перед деплоем.
        Инкремент версий происходит в GitHub Actions или вручную.
        """
        try:
            if self.version_manager.tag_exists_in_git(self.project_root, self.version):
                self.formatter.print_warning(f"⚠️ Тег версии {self.version} уже существует в Git")
                self.formatter.print_info("💡 Убедитесь, что версия корректна. Инкремент должен быть выполнен заранее.")
        except Exception as e:
            # Если не удалось проверить (например, нет Git репозитория), просто пропускаем
            self.logger.debug(f"Не удалось проверить существование тега: {e}")
    
    def _validate_tokens(self):
        """Проверяет наличие токенов для всех репозиториев"""
        missing_tokens = []
        
        repositories = self.config.get('repositories', {})
        if not repositories:
            self.formatter.print_warning("В конфигурации не найдено репозиториев для деплоя")
            return
        
        for repo_name, repo_config in repositories.items():
            # Пропускаем отключенные репозитории
            if not repo_config.get('enabled', True):
                continue
                
            token = repo_config.get('token')
            if not token:
                missing_tokens.append(f"{repo_name}: не указан token (должен быть в формате ${{VARIABLE_NAME}})")
                continue
            
            # Токен уже разрешен при загрузке конфига, проверяем что он не пустой
            if not token or token.strip() == '':
                # Пытаемся определить имя переменной из оригинального конфига для сообщения об ошибке
                # Но так как конфиг уже разрешен, мы не можем получить имя переменной
                # Поэтому просто указываем что токен пустой
                missing_tokens.append(f"{repo_name}: токен не установлен (проверьте переменную окружения)")
        
        if missing_tokens:
            self.formatter.print_error("Отсутствуют токены для репозиториев:")
            for token_msg in missing_tokens:
                self.formatter.print_error(f"  - {token_msg}")
            self.formatter.print_info("\nУстановите переменные окружения:")
            self.formatter.print_info("  export GITHUB_TOKEN='your_token_here'")
            sys.exit(1)
        
        self.formatter.print_success("Все токены найдены")
    
    def _interactive_repo_selection(self) -> List[str]:
        """Интерактивный выбор репозиториев для деплоя"""
        repositories = self.config.get('repositories', {})
        if not repositories:
            self.formatter.print_error("В конфигурации не найдено репозиториев для деплоя")
            return []
        
        # Фильтруем репозитории: исключаем те, у которых enabled: false
        enabled_repos = {
            repo_name: repo_config 
            for repo_name, repo_config in repositories.items()
            if repo_config.get('enabled', True)  # По умолчанию enabled=True
        }
        
        if not enabled_repos:
            self.formatter.print_error("Нет доступных репозиториев для деплоя (все отключены)")
            return []
        
        self.formatter.print_header("🎯 ВЫБОР РЕПОЗИТОРИЕВ")
        
        repo_list = list(enabled_repos.keys())
        for i, repo_name in enumerate(repo_list, 1):
            repo_config = enabled_repos[repo_name]
            print(f"{i}. {repo_name} - {repo_config.get('name', repo_name)}")
            if repo_config.get('description'):
                print(f"   {self.formatter._colorize(repo_config.get('description'), Colors.DIM)}")
        
        print(f"{len(repo_list) + 1}. Все репозитории")
        print("0. Отмена")
        self.formatter.print_separator()
        
        while True:
            choice = input(f"\nВыберите репозитории (через запятую, например: 1,2 или {len(repo_list) + 1} для всех): ").strip()
            
            if choice == "0":
                return []
            
            if choice == str(len(repo_list) + 1):
                return repo_list
            
            try:
                selected_indices = [int(x.strip()) for x in choice.split(',')]
                selected_repos = []
                
                for idx in selected_indices:
                    if 1 <= idx <= len(repo_list):
                        repo_name = repo_list[idx - 1]
                        if repo_name not in selected_repos:
                            selected_repos.append(repo_name)
                    else:
                        self.formatter.print_error(f"Неверный номер: {idx}")
                        break
                else:
                    if selected_repos:
                        return selected_repos
                    else:
                        self.formatter.print_error("Не выбрано ни одного репозитория")
            except ValueError:
                self.formatter.print_error("Неверный формат. Используйте номера через запятую")
    
    def _confirm_deployment(self, selected_repos: List[str], force: bool):
        """Подтверждение деплоя от пользователя"""
        self.formatter.print_section("📋 ПОДТВЕРЖДЕНИЕ ДЕПЛОЯ")
        
        self.formatter.print_info("Целевые репозитории:")
        repositories = self.config.get('repositories', {})
        for repo_name in selected_repos:
            repo_config = repositories[repo_name]
            deployment_config = repo_config.get('deployment', {})
            full_sync = deployment_config.get('full_sync', True)
            create_tag = deployment_config.get('create_tag', False)
            sync_mode_text = "полная" if full_sync else "частичная"
            tag_info = ", тег: да" if create_tag else ", тег: нет"
            self.formatter.print_key_value(f"{repo_name}", f"{repo_config.get('name', repo_name)} (синхронизация: {sync_mode_text}{tag_info})", indent=3)
        
        self.formatter.print_key_value("Версия", self.version)
        self.formatter.print_key_value("Дата", self.date)
        
        if force:
            self.formatter.print_warning("РЕЖИМ ПРИНУДИТЕЛЬНОЙ ПЕРЕЗАПИСИ")
            print("   - Существующие ветки будут удалены")
            print("   - История коммитов в MR будет потеряна")
        
        from modules.utils.user_input import confirm
        if not confirm("\nНачать деплой?", default=False):
            self.formatter.print_error("Деплой отменен пользователем")
            sys.exit(0)
        
        if force:
            self.formatter.print_section("⚠️ ДОПОЛНИТЕЛЬНОЕ ПОДТВЕРЖДЕНИЕ")
            print("Вы уверены что хотите перезаписать существующие ветки?")
            print("Это действие нельзя отменить!")
            
            if not confirm("Продолжить принудительную перезапись?", default=False):
                self.formatter.print_error("Принудительная перезапись отменена")
                sys.exit(0)
        
        self.formatter.print_success("Деплой подтвержден")
    
    def _deploy_to_selected_repos(self, selected_repos: List[str], force: bool):
        """Выполняет деплой в выбранные репозитории"""
        repositories = self.config.get('repositories', {})
        deploy_settings = self.config.get('deploy_settings', {})
        delay = deploy_settings.get('delay_between_deploys', 2)
        
        self.formatter.print_header("🚀 НАЧАЛО ДЕПЛОЯ")
        
        success_count = 0
        failed_repos = []
        
        for i, repo_name in enumerate(selected_repos, 1):
            self.formatter.print_section(f"📦 Деплой {i}/{len(selected_repos)}: {repo_name}")
            
            repo_config = repositories[repo_name]
            deployment_config = repo_config.get('deployment', {})
            
            # Получаем список файлов для деплоя
            files_to_deploy = self.file_filter.get_files_for_repo(repo_name, deployment_config)
            
            if not files_to_deploy:
                self.formatter.print_warning(f"Не найдено файлов для деплоя в {repo_name}")
                failed_repos.append(repo_name)
                continue
            
            self.formatter.print_key_value("Файлов для деплоя", str(len(files_to_deploy)))
            
            # Формируем имя ветки
            branch_prefix = self.config.get('git_settings', {}).get('branch_prefix', 'deploy/')
            branch_name = f"{branch_prefix}{self.version}"
            
            # Выполняем деплой
            success = self.git_handler.deploy_to_repository(
                repo_name=repo_name,
                repo_config=repo_config,
                files_to_deploy=files_to_deploy,
                branch_name=branch_name,
                version=self.version,
                date=self.date,
                force=force,
                deployment_config=deployment_config
            )
            
            if success:
                self.formatter.print_success(f"Деплой в {repo_name} успешен")
                success_count += 1
            else:
                self.formatter.print_error(f"Деплой в {repo_name} неудачен")
                failed_repos.append(repo_name)
            
            # Пауза между деплоями (кроме последнего)
            if i < len(selected_repos) and delay > 0:
                import time
                self.formatter.print_info(f"Пауза {delay} сек. перед следующим деплоем...")
                time.sleep(delay)
        
        # Итоги
        self.formatter.print_section("📊 ИТОГИ ДЕПЛОЯ")
        self.formatter.print_key_value("Успешно", f"{success_count}/{len(selected_repos)}")
        if failed_repos:
            self.formatter.print_error(f"Неудачно: {', '.join(failed_repos)}")
        self.formatter.print_separator()
    
    def run(self):
        """Запускает интерактивный процесс деплоя"""
        try:
            self.formatter.print_header("🚀 ДЕПЛОЙ В РЕПОЗИТОРИИ")
            
            # 1. Получение версии и даты
            self._get_version_and_date()
            
            # 2. Проверка токенов
            self.formatter.print_section("🔐 ПРОВЕРКА ТОКЕНОВ")
            self._validate_tokens()
            
            # 3. Интерактивный выбор репозиториев
            selected_repos = self._interactive_repo_selection()
            if not selected_repos:
                self.formatter.print_error("Не выбрано ни одного репозитория")
                return
            
            # 4. Подтверждение деплоя
            self._confirm_deployment(selected_repos, force=False)
            
            # 5. Выполнение деплоя
            self._deploy_to_selected_repos(selected_repos, force=False)
                
        except KeyboardInterrupt:
            self.formatter.print_warning("\nДеплой прерван пользователем")
            self.logger.warning("Деплой прерван пользователем")
        except FileNotFoundError as e:
            self.formatter.print_error(f"\nФайл не найден: {e}")
            self.logger.error(f"Файл не найден: {e}")
            sys.exit(1)
        except ValueError as e:
            self.formatter.print_error(f"\nОшибка валидации данных: {e}")
            self.logger.error(f"Ошибка валидации данных: {e}")
            sys.exit(1)
        except Exception as e:
            self.formatter.print_error(f"\nНеожиданная ошибка: {e}")
            self.logger.error(f"Неожиданная ошибка: {e}")
            sys.exit(1)


def main():
    """Главная функция"""
    script = DeployToRepositoriesScript()
    script.run()


if __name__ == "__main__":
    main()
