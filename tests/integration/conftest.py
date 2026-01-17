"""
Фикстуры для integration-тестов
"""
import socket
import pytest
from unittest.mock import patch


def find_free_port():
    """Находит свободный порт для тестов"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="function")
def http_server_free_port():
    """Фикстура, которая возвращает свободный порт для HTTP сервера"""
    return find_free_port()


# Фиксированный секрет для тестов вебхуков
TEST_WEBHOOK_SECRET = 'test_secret_12345'


@pytest.fixture(autouse=True)
def override_http_server_port_for_tests(settings_manager, http_server_free_port):
    """
    Автоматически переопределяет настройки для тестов:
    - Database Manager: использует SQLite в памяти вместо PostgreSQL (для работы в CI без PostgreSQL)
    - HTTP Server: устанавливает свободный порт
    - Tenant Hub: включает вебхуки для тестов
    - Bot Hub: включает вебхуки для тестов
    - Глобальные настройки shutdown: минимальные таймауты для быстрых тестов
    
    Применяется ДО инициализации контейнера через autouse=True
    """
    # Получаем оригинальные методы
    original_get_plugin_settings = settings_manager.get_plugin_settings
    original_get_global_settings = settings_manager.get_global_settings
    
    def patched_get_plugin_settings(plugin_name: str):
        settings = original_get_plugin_settings(plugin_name)
        if plugin_name == 'database_manager':
            # Переопределяем настройки БД для тестов - используем SQLite вместо PostgreSQL
            settings = settings.copy()
            settings['database_preset'] = 'sqlite'
            # Убеждаемся, что настройки SQLite присутствуют
            if 'database' not in settings:
                settings['database'] = {}
            if 'sqlite' not in settings['database']:
                settings['database']['sqlite'] = {}
            settings['database']['sqlite']['database_url'] = 'sqlite:///:memory:'
        elif plugin_name == 'http_server':
            # Переопределяем настройки для тестов
            settings = settings.copy()
            settings['port'] = http_server_free_port  # Устанавливаем свободный порт
            settings['external_url'] = f'https://127.0.0.1:{http_server_free_port}'  # Для генерации SSL в тестах
            # Сервер НЕ запускается автоматически - запустится через http_api_service или явно в тестах
        elif plugin_name == 'tenant_hub':
            # Переопределяем настройки вебхуков для тестов
            settings = settings.copy()
            settings['use_webhooks'] = True  # Включаем вебхуки для тестов
            settings['github_webhook_secret'] = TEST_WEBHOOK_SECRET  # Фиксированный секрет
        elif plugin_name == 'bot_hub':
            # Переопределяем настройки вебхуков для тестов Telegram
            settings = settings.copy()
            settings['use_webhooks'] = True  # Включаем вебхуки для тестов
        return settings
    
    def patched_get_global_settings():
        """Переопределяет глобальные настройки для быстрых тестов"""
        global_settings = original_get_global_settings()
        # Переопределяем настройки shutdown для быстрых тестов
        global_settings = global_settings.copy()
        if 'shutdown' not in global_settings:
            global_settings['shutdown'] = {}
        global_settings['shutdown'] = global_settings['shutdown'].copy()
        # Устанавливаем минимальные таймауты для быстрых тестов
        # В тестах нам не нужно ждать долго - плагины должны быстро завершаться
        global_settings['shutdown']['di_container_timeout'] = 0.01
        global_settings['shutdown']['plugin_timeout'] = 0.01
        global_settings['shutdown']['background_tasks_timeout'] = 0.01
        return global_settings
    
    # Патчим методы
    with patch.object(settings_manager, 'get_plugin_settings', side_effect=patched_get_plugin_settings), \
         patch.object(settings_manager, 'get_global_settings', side_effect=patched_get_global_settings):
        yield

