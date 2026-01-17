"""
GitHub API клиент для работы с Merge Requests и ветками
"""

from typing import Dict, Optional

import requests


class GitHubAPIClient:
    """Клиент для работы с GitHub API"""
    
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
    
    def get_token(self, repo_config: Dict) -> str:
        """Получает токен для репозитория (уже разрешенный из переменных окружения)"""
        token = repo_config.get('token')
        if not token:
            raise ValueError(f"Не указан token для репозитория (должен быть в формате ${{VARIABLE_NAME}})")
        
        return token
    
    def parse_repo_url(self, repo_url: str) -> Optional[tuple]:
        """Парсит URL репозитория и возвращает (owner, repo_name)"""
        if "github.com" in repo_url:
            parts = repo_url.split('/')
            owner = parts[-2]
            repo_name = parts[-1]
            return (owner, repo_name)
        return None
    
    def build_api_url(self, endpoint: str, owner: str, repo_name: str) -> str:
        """Строит полный URL для GitHub API"""
        github_config = self.config.get('git_settings', {}).get('providers', {}).get('github', {})
        api_base_url = github_config.get('api_url', 'https://api.github.com')
        return f"{api_base_url}/repos/{owner}/{repo_name}/{endpoint}"
    
    def get_headers(self, token: str) -> Dict[str, str]:
        """Возвращает заголовки для запросов к GitHub API"""
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }


class MergeRequestManager:
    """Управление Merge Requests через GitHub API"""
    
    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        self.api_client = GitHubAPIClient(config, logger)
    
    def check_existing(self, repo_config: Dict, branch_name: str) -> Dict:
        """Проверяет существующий Merge Request для ветки"""
        try:
            # Получаем токен
            token = self.api_client.get_token(repo_config)
            
            # Извлекаем owner и repo из URL
            repo_url = repo_config['url']
            parsed = self.api_client.parse_repo_url(repo_url)
            if not parsed:
                return {"exists": False, "status": None, "url": None}
            
            owner, repo_name = parsed
            
            # Проверяем существующие PR
            api_url = self.api_client.build_api_url("pulls", owner, repo_name)
            headers = self.api_client.get_headers(token)
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                pulls = response.json()
                for pull in pulls:
                    if pull['head']['ref'] == branch_name:
                        return {
                            "exists": True,
                            "status": pull['state'],
                            "url": pull['html_url'],
                            "title": pull['title'],
                            "merged": pull.get('merged', False),
                            "approved": pull.get('approved', False)
                        }
            
            return {"exists": False, "status": None, "url": None}
            
        except requests.RequestException as e:
            self.logger.error(f"Сетевая ошибка при проверке MR: {e}")
            return {"exists": False, "status": None, "url": None}
        except KeyError as e:
            self.logger.error(f"Ошибка формата ответа API при проверке MR: {e}")
            return {"exists": False, "status": None, "url": None}
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при проверке MR: {e}")
            return {"exists": False, "status": None, "url": None}
    
    def create(self, repo_config: Dict, branch_name: str, version: str, date: str, repo_name: str) -> bool:
        """Создает Merge Request через GitHub API"""
        try:
            # Получаем токен
            token = self.api_client.get_token(repo_config)
            
            # Извлекаем owner и repo из URL
            repo_url = repo_config['url']
            parsed = self.api_client.parse_repo_url(repo_url)
            if not parsed:
                self.logger.warning("Создание MR поддерживается только для GitHub")
                return False
            
            owner, repo_name_api = parsed
            
            # Получаем базовую ветку из конфига
            from modules.base import get_base
            base = get_base().get_default_branch(repo_config)
            
            # Формируем данные для MR
            mr_template = self.config['git_settings']['mr_description_template']
            mr_description = mr_template.format(
                version=version,
                changes=f"Обновление файлов для версии {version}",
                repo_name=repo_name,
                date=date
            )
            
            mr_title_template = self.config['git_settings']['mr_title_template']
            mr_title = mr_title_template.format(
                version=version,
                date=date
            )
            
            # Данные для API
            data = {
                "title": mr_title,
                "body": mr_description,
                "head": branch_name,
                "base": base
            }
            
            # Отправляем запрос к GitHub API
            api_url = self.api_client.build_api_url("pulls", owner, repo_name_api)
            headers = self.api_client.get_headers(token)
            
            self.logger.info(f"Создание MR: {api_url}")
            self.logger.debug(f"Данные MR: {data}")
            
            response = requests.post(api_url, json=data, headers=headers)
            
            self.logger.info(f"Ответ GitHub API: {response.status_code}")
            
            if response.status_code == 201:
                mr_data = response.json()
                mr_url = mr_data['html_url']
                self.logger.info(f"Merge Request создан: {mr_url}")
                print(f"\n{'='*60}")
                print(f"🔗 MERGE REQUEST СОЗДАН")
                print(f"{'='*60}")
                print(f"📋 URL: {mr_url}")
                print(f"📝 Заголовок: {mr_title}")
                print(f"📊 Статус: ОТКРЫТ")
                print(f"📅 Дата: {date}")
                print(f"{'='*60}")
                return True
            elif response.status_code == 422:
                # MR уже существует
                error_data = response.json()
                if "already exists" in str(error_data):
                    self.logger.warning(f"MR для ветки {branch_name} уже существует")
                    print(f"\n{'='*60}")
                    print(f"⚠️ MR УЖЕ СУЩЕСТВУЕТ")
                    print(f"{'='*60}")
                    print(f"🔗 Ветка: {branch_name}")
                    print(f"📊 Статус: ОБНОВЛЕН")
                    print(f"💡 MR был обновлен новыми изменениями")
                    print(f"{'='*60}")
                    return True
                else:
                    self.logger.error(f"Ошибка создания MR (422): {error_data}")
                    print(f"\n{'='*60}")
                    print(f"❌ ОШИБКА СОЗДАНИЯ MR")
                    print(f"{'='*60}")
                    print(f"🔗 Ветка: {branch_name}")
                    print(f"📊 Код ошибки: 422")
                    print(f"📝 Детали: {error_data}")
                    print(f"{'='*60}")
                    return False
            else:
                self.logger.error(f"Ошибка создания MR: {response.status_code} - {response.text}")
                print(f"\n{'='*60}")
                print(f"❌ ОШИБКА СОЗДАНИЯ MR")
                print(f"{'='*60}")
                print(f"🔗 Ветка: {branch_name}")
                print(f"📊 Код ошибки: {response.status_code}")
                print(f"📝 Ответ: {response.text}")
                print(f"{'='*60}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Сетевая ошибка при создании MR: {e}")
            print(f"\n{'='*60}")
            print(f"❌ СЕТЕВАЯ ОШИБКА MR")
            print(f"{'='*60}")
            print(f"🔗 Ветка: {branch_name}")
            print(f"📝 Ошибка: {e}")
            print(f"💡 Проверьте подключение к интернету и доступность GitHub API")
            print(f"{'='*60}")
            return False
        except KeyError as e:
            self.logger.error(f"Ошибка формата конфигурации при создании MR: {e}")
            print(f"\n{'='*60}")
            print(f"❌ ОШИБКА КОНФИГУРАЦИИ MR")
            print(f"{'='*60}")
            print(f"🔗 Ветка: {branch_name}")
            print(f"📝 Отсутствует обязательное поле: {e}")
            print(f"{'='*60}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при создании MR: {e}")
            print(f"\n{'='*60}")
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА MR")
            print(f"{'='*60}")
            print(f"🔗 Ветка: {branch_name}")
            print(f"📝 Ошибка: {e}")
            print(f"{'='*60}")
            return False
    
    def show_info(self, repo_config: Dict, branch_name: str):
        """Показывает информацию о существующем MR"""
        try:
            existing_mr = self.check_existing(repo_config, branch_name)
            if existing_mr['exists']:
                print(f"📋 Найден существующий MR: {existing_mr['url']}")
                print(f"   Статус: {existing_mr['status']}")
                print(f"   Заголовок: {existing_mr['title']}")
                
                if existing_mr['merged']:
                    print("   ⚠️ MR уже был мержен!")
                    print("   💡 Рекомендуется создать новую версию")
                elif existing_mr['status'] == 'closed':
                    print("   ⚠️ MR был закрыт!")
                    print("   💡 Рекомендуется создать новую версию")
                elif existing_mr['status'] == 'open':
                    print("   ✅ MR открыт и ожидает ревью")
            else:
                print(f"📋 MR для ветки {branch_name} не найден")
                
        except Exception as e:
            self.logger.warning(f"Ошибка получения информации о MR: {e}")
    
    def check_branch_exists_via_api(self, repo_config: Dict, branch_name: str) -> bool:
        """Проверяет существование ветки через GitHub API без клонирования"""
        try:
            # Получаем токен
            token = self.api_client.get_token(repo_config)
            
            # Извлекаем owner и repo из URL
            repo_url = repo_config['url']
            parsed = self.api_client.parse_repo_url(repo_url)
            if not parsed:
                return False
            
            owner, repo_name = parsed
            
            # Проверяем существование ветки через API
            api_url = self.api_client.build_api_url(f"branches/{branch_name}", owner, repo_name)
            headers = self.api_client.get_headers(token)
            
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            else:
                self.logger.warning(f"Неожиданный ответ API при проверке ветки: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            self.logger.warning(f"Сетевая ошибка при проверке ветки через API: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Неожиданная ошибка при проверке ветки через API: {e}")
            return False
    
    def create_tag(self, repo_config: Dict, version: str, branch_name: str) -> bool:
        """Создает тег версии через GitHub API"""
        try:
            # Получаем токен
            token = self.api_client.get_token(repo_config)
            
            # Извлекаем owner и repo из URL
            repo_url = repo_config['url']
            parsed = self.api_client.parse_repo_url(repo_url)
            if not parsed:
                self.logger.warning("Создание тега поддерживается только для GitHub")
                return False
            
            owner, repo_name = parsed
            
            # Проверяем, существует ли тег уже
            tag_name = f"v{version}" if not version.startswith('v') else version
            api_url = self.api_client.build_api_url(f"git/ref/tags/{tag_name}", owner, repo_name)
            headers = self.api_client.get_headers(token)
            
            check_response = requests.get(api_url, headers=headers)
            if check_response.status_code == 200:
                self.logger.warning(f"Тег {tag_name} уже существует, пропускаем создание")
                print(f"⚠️ Тег {tag_name} уже существует в репозитории")
                return True
            
            # Получаем SHA коммита из ветки
            branch_api_url = self.api_client.build_api_url(f"branches/{branch_name}", owner, repo_name)
            branch_response = requests.get(branch_api_url, headers=headers)
            
            if branch_response.status_code != 200:
                self.logger.error(f"Не удалось получить информацию о ветке {branch_name}: {branch_response.status_code}")
                print(f"❌ Ошибка получения информации о ветке {branch_name}")
                return False
            
            branch_data = branch_response.json()
            commit_sha = branch_data['commit']['sha']
            
            # Создаем тег через GitHub API
            # Используем Git References API для создания lightweight тега
            tag_ref_url = self.api_client.build_api_url("git/refs", owner, repo_name)
            tag_data = {
                "ref": f"refs/tags/{tag_name}",
                "sha": commit_sha
            }
            
            self.logger.info(f"Создание тега {tag_name} на коммите {commit_sha[:7]}...")
            response = requests.post(tag_ref_url, json=tag_data, headers=headers)
            
            if response.status_code == 201:
                tag_url = f"https://github.com/{owner}/{repo_name}/releases/tag/{tag_name}"
                self.logger.info(f"Тег {tag_name} успешно создан")
                print(f"\n{'='*60}")
                print(f"🏷️ ТЕГ ВЕРСИИ СОЗДАН")
                print(f"{'='*60}")
                print(f"📋 Тег: {tag_name}")
                print(f"🔗 URL: {tag_url}")
                print(f"📊 Коммит: {commit_sha[:7]}")
                print(f"{'='*60}")
                return True
            elif response.status_code == 422:
                # Тег уже существует или другая ошибка валидации
                error_data = response.json()
                if "already exists" in str(error_data):
                    self.logger.warning(f"Тег {tag_name} уже существует")
                    print(f"⚠️ Тег {tag_name} уже существует в репозитории")
                    return True
                else:
                    self.logger.error(f"Ошибка создания тега (422): {error_data}")
                    print(f"❌ Ошибка создания тега: {error_data}")
                    return False
            else:
                self.logger.error(f"Ошибка создания тега: {response.status_code} - {response.text}")
                print(f"\n{'='*60}")
                print(f"❌ ОШИБКА СОЗДАНИЯ ТЕГА")
                print(f"{'='*60}")
                print(f"📋 Тег: {tag_name}")
                print(f"📊 Код ошибки: {response.status_code}")
                print(f"📝 Ответ: {response.text}")
                print(f"{'='*60}")
                return False
                
        except requests.RequestException as e:
            self.logger.error(f"Сетевая ошибка при создании тега: {e}")
            print(f"\n{'='*60}")
            print(f"❌ СЕТЕВАЯ ОШИБКА СОЗДАНИЯ ТЕГА")
            print(f"{'='*60}")
            print(f"📋 Тег: {version}")
            print(f"📝 Ошибка: {e}")
            print(f"💡 Проверьте подключение к интернету и доступность GitHub API")
            print(f"{'='*60}")
            return False
        except KeyError as e:
            self.logger.error(f"Ошибка формата ответа API при создании тега: {e}")
            print(f"\n{'='*60}")
            print(f"❌ ОШИБКА ФОРМАТА ОТВЕТА API")
            print(f"{'='*60}")
            print(f"📋 Тег: {version}")
            print(f"📝 Отсутствует поле: {e}")
            print(f"{'='*60}")
            return False
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при создании тега: {e}")
            print(f"\n{'='*60}")
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА СОЗДАНИЯ ТЕГА")
            print(f"{'='*60}")
            print(f"📋 Тег: {version}")
            print(f"📝 Ошибка: {e}")
            print(f"{'='*60}")
            return False

