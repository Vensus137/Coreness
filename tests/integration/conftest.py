"""
Fixtures for integration tests
"""
import socket
import pytest
from unittest.mock import patch


def find_free_port():
    """Finds free port for tests"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="function")
def http_server_free_port():
    """Fixture that returns free port for HTTP server"""
    return find_free_port()


# Fixed secret for webhook tests
TEST_WEBHOOK_SECRET = 'test_secret_12345'


@pytest.fixture(autouse=True)
def override_http_server_port_for_tests(settings_manager, http_server_free_port):
    """
    Automatically overrides settings for tests:
    - Database Manager: uses SQLite in memory instead of PostgreSQL (for CI without PostgreSQL)
    - HTTP Server: sets free port
    - Tenant Hub: enables webhooks for tests
    - Bot Hub: enables webhooks for tests
    - Global shutdown settings: minimal timeouts for fast tests
    
    Applied BEFORE container initialization via autouse=True
    """
    # Get original methods
    original_get_plugin_settings = settings_manager.get_plugin_settings
    original_get_global_settings = settings_manager.get_global_settings
    
    def patched_get_plugin_settings(plugin_name: str):
        settings = original_get_plugin_settings(plugin_name)
        if plugin_name == 'database_manager':
            # Override DB settings for tests - use SQLite instead of PostgreSQL
            settings = settings.copy()
            settings['database_preset'] = 'sqlite'
            # Ensure SQLite settings are present
            if 'database' not in settings:
                settings['database'] = {}
            if 'sqlite' not in settings['database']:
                settings['database']['sqlite'] = {}
            settings['database']['sqlite']['database_url'] = 'sqlite:///:memory:'
        elif plugin_name == 'http_server':
            # Override settings for tests
            settings = settings.copy()
            settings['port'] = http_server_free_port  # Set free port
            settings['external_url'] = f'https://127.0.0.1:{http_server_free_port}'  # For SSL generation in tests
            # Server does NOT start automatically - will start via http_api_service or explicitly in tests
        elif plugin_name == 'tenant_hub':
            # Override webhook settings for tests
            settings = settings.copy()
            settings['use_webhooks'] = True  # Enable webhooks for tests
            settings['github_webhook_secret'] = TEST_WEBHOOK_SECRET  # Fixed secret
        elif plugin_name == 'bot_hub':
            # Override webhook settings for Telegram tests
            settings = settings.copy()
            settings['use_webhooks'] = True  # Enable webhooks for tests
        return settings
    
    def patched_get_global_settings():
        """Overrides global settings for fast tests"""
        global_settings = original_get_global_settings()
        # Override shutdown settings for fast tests
        global_settings = global_settings.copy()
        if 'shutdown' not in global_settings:
            global_settings['shutdown'] = {}
        global_settings['shutdown'] = global_settings['shutdown'].copy()
        # Set minimal timeouts for fast tests
        # In tests we don't need to wait long - plugins should terminate quickly
        global_settings['shutdown']['di_container_timeout'] = 0.01
        global_settings['shutdown']['plugin_timeout'] = 0.01
        global_settings['shutdown']['background_tasks_timeout'] = 0.01
        return global_settings
    
    # Patch methods
    with patch.object(settings_manager, 'get_plugin_settings', side_effect=patched_get_plugin_settings), \
         patch.object(settings_manager, 'get_global_settings', side_effect=patched_get_global_settings):
        yield

