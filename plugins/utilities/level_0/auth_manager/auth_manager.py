import os
import time
import uuid
import ssl
import certifi
from typing import Dict, Optional, Any
import requests


class AuthManager:
    """
    Универсальная утилита для управления авторизацией и токенами OAuth2.
    Поддерживает кэширование токенов с автоматическим обновлением.
    """
    def __init__(self, **kwargs):

        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']

        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("auth_manager")

        self.default_token_lifetime = settings.get('default_token_lifetime', 1800)
        self.token_refresh_threshold = settings.get('token_refresh_threshold', 300)
        self.cache_cleanup_interval = settings.get('cache_cleanup_interval', 3600)
        
        self._token_cache: Dict[str, Dict[str, Any]] = {}
        self._last_cache_cleanup = time.time()

        # Настраиваем SSL контекст для работы с российскими сертификатами
        self._setup_ssl_context()
        self.logger.info("AuthManager инициализирован")

    def _setup_ssl_context(self):
        """Настраивает SSL контекст для работы с российскими сертификатами"""
        self.session = self.get_ssl_session()
    
    def get_ssl_session(self, verify: bool = True) -> requests.Session:
        """Возвращает сессию с настроенными SSL сертификатами"""
        try:
            session = requests.Session()
            
            if not verify:
                session.verify = False
                return session
            
            project_root = self.settings_manager.get_project_root()
            certs_path = os.path.join(project_root, 'ssl_certificates', 'russian_certs.pem')
            
            if os.path.exists(certs_path):
                ssl_context = ssl.create_default_context()
                ssl_context.load_verify_locations(cafile=certs_path)
                
                class SSLAdapter(requests.adapters.HTTPAdapter):
                    def init_poolmanager(self, *args, **kwargs):
                        kwargs['ssl_context'] = ssl_context
                        return super().init_poolmanager(*args, **kwargs)
                    
                    def proxy_manager_for(self, proxy, **proxy_kwargs):
                        proxy_kwargs['ssl_context'] = ssl_context
                        return super().proxy_manager_for(proxy, **proxy_kwargs)
                
                session.mount('https://', SSLAdapter())
                session.verify = True
                self.logger.debug(f"SSL сессия создана с российскими сертификатами: {certs_path}")
            else:
                session.verify = True
                self.logger.debug("Российские SSL сертификаты не найдены, используем стандартные")
            
            return session
            
        except Exception as e:
            self.logger.error(f"Ошибка создания SSL сессии: {e}")
            session = requests.Session()
            session.verify = True
            return session

    def get_token(self, service_name: str) -> str:
        """
        Получить валидный токен для сервиса (с кэшированием)
        """
        self._cleanup_cache_if_needed()
        if service_name in self._token_cache:
            cached_data = self._token_cache[service_name]
            token = cached_data['token']
            expires_at = cached_data['expires_at']
            service_config = cached_data.get('service_config', {})
            refresh_threshold = service_config.get('refresh_threshold', self.token_refresh_threshold)
            if time.time() < expires_at - refresh_threshold:
                self.logger.debug(f"Используем кэшированный токен для {service_name}")
                return token
            else:
                self.logger.info(f"Токен для {service_name} истекает, обновляем...")
        return self._request_new_token(service_name)

    def refresh_token(self, service_name: str) -> str:
        """Принудительно обновить токен для сервиса"""
        self.logger.info(f"Принудительное обновление токена для {service_name}")
        if service_name in self._token_cache:
            del self._token_cache[service_name]
        return self._request_new_token(service_name)

    def clear_cache(self, service_name: str = None) -> bool:
        """Очистить кэш токенов для сервиса или всех сервисов"""
        try:
            if service_name:
                if service_name in self._token_cache:
                    del self._token_cache[service_name]
                    self.logger.info(f"Кэш токенов очищен для {service_name}")
                else:
                    self.logger.warning(f"Кэш токенов для {service_name} не найден")
            else:
                cache_size = len(self._token_cache)
                self._token_cache.clear()
                self.logger.info(f"Кэш токенов полностью очищен ({cache_size} записей)")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")
            return False

    def get_token_info(self, service_name: str) -> Dict[str, Any]:
        """Получить информацию о токене (время жизни, сервис)"""
        if service_name not in self._token_cache:
            return {
                'cached': False,
                'service_name': service_name,
                'expires_at': None,
                'time_until_expiry': None
            }
        cached_data = self._token_cache[service_name]
        expires_at = cached_data['expires_at']
        time_until_expiry = expires_at - time.time()
        return {
            'cached': True,
            'service_name': service_name,
            'expires_at': expires_at,
            'time_until_expiry': time_until_expiry,
            'service_config': cached_data.get('service_config', {})
        }

    def _request_new_token(self, service_name: str) -> str:
        """Запрашивает новый токен для сервиса"""
        service_config = self._get_service_config(service_name)
        if not service_config:
            raise ValueError(f"Сервис {service_name} не настроен в конфигурации")
        auth_type = service_config.get('auth_type', 'oauth2')
        if auth_type == 'oauth2':
            return self._request_oauth2_token(service_name, service_config)
        else:
            raise ValueError(f"Неподдерживаемый тип авторизации: {auth_type}")

    def _get_service_config(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Получает конфигурацию сервиса из настроек"""
        try:
            services_config = self.settings_manager.get_plugin_settings("auth_manager").get('services', {})
            if service_name not in services_config:
                self.logger.error(f"Сервис {service_name} не найден в конфигурации auth_manager")
                return None
            return services_config[service_name]
        except Exception as e:
            self.logger.error(f"Ошибка получения конфигурации сервиса {service_name}: {e}")
            return None

    def _request_oauth2_token(self, service_name: str, service_config: Dict[str, Any]) -> str:
        """Запрашивает OAuth2 токен для сервиса"""
        try:
            token_url = service_config['token_url']
            scope = service_config.get('scope', '')
            headers = service_config.get('headers', {})
            auth_key = service_config.get('auth_key', '')
            if auth_key.startswith('${') and auth_key.endswith('}'):
                env_var = auth_key[2:-1]
                auth_key = os.getenv(env_var, '')
            if not auth_key:
                raise ValueError(f"Auth key не настроен для сервиса {service_name}")
            data = {}
            if scope:
                data['scope'] = scope
            request_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': str(uuid.uuid4()),
                'Authorization': f'Basic {auth_key}'
            }
            request_headers.update(headers)
            self.logger.info(f"Запрашиваем OAuth2 токен для {service_name}")
            response = self.session.post(token_url, data=data, headers=request_headers)
            if response.status_code != 200:
                raise Exception(f"Ошибка получения токена: {response.status_code} - {response.text}")
            token_data = response.json()
            access_token = token_data.get('access_token')
            if not access_token:
                raise Exception("Access token не найден в ответе API")
            # Индивидуальные параметры времени жизни токена
            expires_in = token_data.get('expires_in', service_config.get('token_lifetime', self.default_token_lifetime))
            refresh_threshold = service_config.get('refresh_threshold', self.token_refresh_threshold)
            expires_at = time.time() + expires_in
            self._token_cache[service_name] = {
                'token': access_token,
                'expires_at': expires_at,
                'service_config': service_config,
                'refresh_threshold': refresh_threshold
            }
            self.logger.info(f"Токен для {service_name} получен, истекает через {expires_in} секунд")
            return access_token
        except Exception as e:
            self.logger.error(f"Ошибка запроса OAuth2 токена для {service_name}: {e}")
            raise

    def _cleanup_cache_if_needed(self):
        """Очищает кэш если прошло достаточно времени"""
        current_time = time.time()
        if current_time - self._last_cache_cleanup > self.cache_cleanup_interval:
            expired_services = []
            for service_name, cached_data in self._token_cache.items():
                if current_time > cached_data['expires_at']:
                    expired_services.append(service_name)
            for service_name in expired_services:
                del self._token_cache[service_name]
                self.logger.debug(f"Удален истекший токен для {service_name}")
            if expired_services:
                self.logger.info(f"Очищено {len(expired_services)} истекших токенов")
            self._last_cache_cleanup = current_time
