"""
Интеграционные тесты жизненного цикла приложения
Проверяют корректную инициализацию и shutdown приложения
"""
import pytest

from tests.conftest import initialized_di_container, di_container  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_application_startup(initialized_di_container):
    """Проверка корректной инициализации приложения"""
    # Проверяем, что все утилиты инициализированы
    # Foundation утилиты доступны через get_utility(), но могут не быть в get_all_utilities()
    utilities = initialized_di_container.get_all_utilities()
    
    # Проверяем наличие критических foundation утилит через get_utility()
    logger = initialized_di_container.get_utility('logger')
    assert logger is not None, "Logger должен быть инициализирован"
    
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    assert plugins_manager is not None, "PluginsManager должен быть инициализирован"
    
    settings_manager = initialized_di_container.get_utility('settings_manager')
    assert settings_manager is not None, "SettingsManager должен быть инициализирован"
    
    # Проверяем, что есть другие утилиты (не только foundation)
    # Foundation утилиты могут не попадать в get_all_utilities(), но другие должны быть
    if len(utilities) == 0:
        # Если нет утилит в списке, проверяем, что хотя бы одна не-foundation утилита доступна
        test_utilities = ['action_hub', 'database_manager', 'cache_manager']
        found_utility = False
        for util_name in test_utilities:
            util = initialized_di_container.get_utility(util_name)
            if util is not None:
                found_utility = True
                break
        assert found_utility, "Должна быть хотя бы одна не-foundation утилита"
    
    # Проверяем, что все сервисы могут быть получены
    services = initialized_di_container.get_all_services()
    assert len(services) > 0, "Должны быть инициализированы сервисы"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_di_container_shutdown(di_container):
    """Проверка корректного shutdown DI-контейнера"""
    # Инициализируем контейнер для теста
    di_container.initialize_all_plugins()
    
    # Проверяем, что контейнер инициализирован перед shutdown
    # Foundation утилиты всегда доступны, проверяем их
    logger = di_container.get_utility('logger')
    assert logger is not None, "Logger должен быть доступен перед shutdown"
    
    # Проверяем, что shutdown не вызывает ошибок
    # Примечание: shutdown очищает контейнер, поэтому проверяем только отсутствие исключений
    try:
        di_container.shutdown()
    except Exception as e:
        pytest.fail(f"Shutdown вызвал исключение: {e}")
    
    # Проверяем, что shutdown не вызывает ошибок при повторном вызове
    try:
        di_container.shutdown()  # Должно быть безопасно
    except Exception as e:
        pytest.fail(f"Повторный shutdown вызвал исключение: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_foundation_utilities_available(initialized_di_container):
    """Проверка доступности foundation утилит"""
    # Foundation утилиты доступны через get_utility до shutdown
    foundation_utils = ['logger', 'plugins_manager', 'settings_manager']
    
    for util_name in foundation_utils:
        util_instance = initialized_di_container.get_utility(util_name)
        assert util_instance is not None, f"Foundation утилита {util_name} должна быть доступна"
        
        # Проверяем, что это действительно экземпляр утилиты
        assert hasattr(util_instance, '__class__'), f"{util_name} должен быть объектом"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_services_can_be_retrieved(initialized_di_container):
    """Проверка, что все сервисы могут быть получены из DI-контейнера"""
    # Получаем список включенных сервисов из плана запуска
    settings_manager = initialized_di_container.get_utility('settings_manager')
    assert settings_manager is not None, "SettingsManager должен быть доступен"
    
    startup_plan = settings_manager.get_startup_plan()
    assert startup_plan is not None, "План запуска должен быть построен"
    
    enabled_services = startup_plan.get('enabled_services', [])
    assert len(enabled_services) > 0, "Должен быть хотя бы один включенный сервис"
    
    # Проверяем, что каждый сервис может быть получен по имени
    for service_name in enabled_services:
        service_instance = initialized_di_container.get_service(service_name)
        assert service_instance is not None, f"Сервис {service_name} должен быть доступен"

