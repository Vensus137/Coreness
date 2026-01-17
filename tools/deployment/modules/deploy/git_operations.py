"""
Git операции: клонирование, ветки, коммиты, push
"""

import time
from typing import Dict, Optional

from git import Repo


class GitRepository:
    """Работа с Git репозиториями"""
    
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
    
    def get_auth_url(self, repo_config: Dict, token: Optional[str] = None) -> str:
        """Формирует URL с токеном для аутентификации"""
        repo_url = repo_config['url']
        if "github.com" in repo_url and token:
            return repo_url.replace("https://", f"https://{token}@")
        return repo_url
    
    def clone(self, repo_config: Dict, repo_path: str, token: Optional[str] = None) -> Optional[Repo]:
        """Клонирует репозиторий"""
        try:
            # Формируем URL с токеном
            auth_url = self.get_auth_url(repo_config, token)
            
            self.logger.info(f"Клонирование репозитория: {repo_config['url']}")
            
            # Клонируем репозиторий
            repo = Repo.clone_from(auth_url, repo_path)
            
            # Настраиваем Git (получаем из конфига)
            self.configure_user(repo)
            
            # Настраиваем remote URL с токеном для push
            if "github.com" in repo_config['url'] and token:
                auth_remote_url = self.get_auth_url(repo_config, token)
                origin = repo.remotes.origin
                origin.set_url(auth_remote_url)
                self.logger.info(f"Remote URL настроен с токеном для push")
            
            self.logger.info(f"Репозиторий успешно клонирован в {repo_path}")
            return repo
            
        except Exception as e:
            self.logger.error(f"Ошибка клонирования репозитория: {e}")
            return None
    
    def configure_user(self, repo: Repo):
        """Настраивает пользователя Git для коммитов"""
        git_user = self.config.get('git_settings', {}).get('user', {})
        user_name = git_user.get('name', 'Deploy Manager')
        user_email = git_user.get('email', 'deploy@example.com')
        
        with repo.config_writer() as git_config:
            git_config.set_value("user", "name", user_name)
            git_config.set_value("user", "email", user_email)


class BranchManager:
    """Управление ветками Git"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def exists_locally(self, repo: Repo, branch_name: str) -> bool:
        """Проверяет существование ветки локально"""
        return branch_name in [head.name for head in repo.heads]
    
    def exists_remotely(self, repo: Repo, branch_name: str) -> bool:
        """Проверяет существование ветки в remote"""
        try:
            remote_refs = repo.remote('origin').refs
            for ref in remote_refs:
                if ref.name == branch_name:
                    return True
            return False
        except Exception as e:
            self.logger.warning(f"Ошибка проверки remote веток: {e}")
            return False
    
    def create(self, repo: Repo, branch_name: str, force: bool = False) -> bool:
        """Создает новую ветку"""
        try:
            # Проверяем локальную ветку
            local_exists = self.exists_locally(repo, branch_name)
            
            # Проверяем remote ветку
            remote_exists = self.exists_remotely(repo, branch_name)
            
            if local_exists or remote_exists:
                if not force:
                    print(f"⚠️ Ветка {branch_name} уже существует")
                    if local_exists and remote_exists:
                        print("   (локально и в remote)")
                    elif local_exists:
                        print("   (локально)")
                    elif remote_exists:
                        print("   (в remote)")
                    print("💡 Используйте --force для перезаписи")
                    return False
                else:
                    print(f"🗑️ Перезаписываем существующую ветку {branch_name}")
                    
                    # Удаляем локальную ветку если есть
                    if local_exists:
                        repo.delete_head(branch_name, force=True)
                    
                    # Удаляем remote ветку если есть
                    if remote_exists:
                        try:
                            origin = repo.remote('origin')
                            origin.push(f":{branch_name}")  # Удаляем remote ветку
                            print(f"🗑️ Удалена remote ветка {branch_name}")
                        except Exception as e:
                            self.logger.warning(f"Не удалось удалить remote ветку: {e}")
            
            # Создаем новую ветку
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            self.logger.info(f"Создана и переключена на ветку: {branch_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка создания ветки {branch_name}: {e}")
            return False


class CommitManager:
    """Управление коммитами и push"""
    
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
    
    def commit(self, repo: Repo, version: str, date: str, repo_name: str) -> bool:
        """Создает коммит с изменениями"""
        try:
            # Проверяем, есть ли изменения ДО добавления в индекс
            has_untracked = len(repo.untracked_files) > 0
            has_modified = repo.is_dirty()
            
            if not has_untracked and not has_modified:
                self.logger.warning("Нет изменений для коммита")
                print(f"ℹ️ Нет изменений для коммита - файлы уже актуальны")
                # Это не ошибка - возможно, файлы уже актуальны после мержа
                return True
            
            # Добавляем все файлы
            repo.git.add(A=True)
            
            # Формируем сообщение коммита
            commit_template = self.config['git_settings']['commit_message_template']
            commit_message = commit_template.format(
                version=version,
                date=date,
                repo_name=repo_name
            )
            
            # Создаем коммит
            repo.index.commit(commit_message)
            
            self.logger.info(f"Создан коммит: {commit_message}")
            print(f"✅ Создан коммит: {commit_message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка создания коммита: {e}")
            return False
    
    def push(self, repo: Repo, branch_name: str, force: bool = False) -> bool:
        """Отправляет ветку в репозиторий"""
        try:
            # Получаем remote
            origin = repo.remotes.origin
            
            # Push ветки
            if force:
                result = origin.push(branch_name, force=True)
                self.logger.info(f"Ветка {branch_name} принудительно отправлена в репозиторий")
            else:
                result = origin.push(branch_name)
                self.logger.info(f"Ветка {branch_name} отправлена в репозиторий")
            
            # Проверяем результат push более тщательно
            push_successful = False
            if result and len(result) > 0:
                for info in result:
                    # Сначала проверяем summary для новых веток (приоритет)
                    if info.summary and "[new branch]" in info.summary:
                        self.logger.info(f"Успешный push (новая ветка): {info.summary}")
                        push_successful = True
                        continue
                    
                    # Проверяем флаги ошибок
                    if hasattr(info, 'flags'):
                        if info.flags & 128:  # GIT_PUSH_ERROR
                            # Проверяем, не является ли это forced update (что не ошибка)
                            if info.summary and "(forced update)" in info.summary:
                                self.logger.info(f"Успешный push (forced update): {info.summary}")
                                push_successful = True
                            else:
                                self.logger.error(f"Ошибка push: {info.summary}")
                                return False
                        elif info.flags & 1:  # GIT_PUSH_UPDATE_FASTFORWARD
                            self.logger.info(f"Успешный push (fast-forward): {info.summary}")
                            push_successful = True
                        elif info.flags & 2:  # GIT_PUSH_UPDATE_REJECTED
                            # Дополнительная проверка для новых веток
                            if info.summary and "[new branch]" in info.summary:
                                self.logger.info(f"Успешный push (новая ветка): {info.summary}")
                                push_successful = True
                            else:
                                self.logger.error(f"Push отклонен: {info.summary}")
                                return False
                        elif info.flags & 4:  # GIT_PUSH_UPDATE_NONFASTFORWARD
                            self.logger.error(f"Push требует force: {info.summary}")
                            return False
                        else:
                            # Проверяем summary для других успешных push
                            if info.summary and "->" in info.summary:
                                self.logger.info(f"Успешный push: {info.summary}")
                                push_successful = True
                            else:
                                self.logger.info(f"Push результат: {info.summary}")
                                push_successful = True
            
            # Если push прошел успешно, дополнительно проверяем через API
            if push_successful:
                time.sleep(2)  # Ждем немного
                
                # Проверяем, что ветка действительно существует в remote
                try:
                    remote_refs = origin.refs
                    branch_exists = any(ref.name == f"origin/{branch_name}" for ref in remote_refs)
                    if not branch_exists:
                        self.logger.error(f"Ветка {branch_name} не найдена в remote после push")
                        return False
                except Exception as e:
                    self.logger.warning(f"Не удалось проверить remote refs: {e}")
                
                return True
            else:
                self.logger.error("Push не был успешным")
                return False
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки ветки: {e}")
            return False

