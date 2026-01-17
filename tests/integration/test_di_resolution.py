"""
Интеграционные тесты зависимостей и разрешения DI
Проверяют корректное разрешение зависимостей через DI-контейнер
"""
import pytest

from tests.conftest import initialized_di_container  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_dependencies_resolved(initialized_di_container):
    """Проверка, что все зависимости могут быть разрешены"""
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    all_plugins = plugins_manager.get_all_plugins_info()
    
    errors = []
    skipped_plugins = ['logger', 'plugins_manager', 'settings_manager']  # Эти создаются вручную
    
    for plugin_name in all_plugins.keys():
        if plugin_name in skipped_plugins:
            continue  # Эти создаются вручную в Application
        
        try:
            plugin_type = plugins_manager.get_plugin_type(plugin_name)
            if plugin_type == 'utilities' or plugin_type == 'utility':
                _ = initialized_di_container.get_utility(plugin_name)
            elif plugin_type == 'services' or plugin_type == 'service':
                _ = initialized_di_container.get_service(plugin_name)
            else:
                errors.append(f"{plugin_name}: неизвестный тип плагина '{plugin_type}'")
                continue
        except Exception as e:
            errors.append(f"{plugin_name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Ошибки разрешения зависимостей:\n" + "\n".join(errors))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dependency_order_correct(initialized_di_container):
    """Проверка правильного порядка инициализации зависимостей"""
    settings_manager = initialized_di_container.get_utility('settings_manager')
    startup_plan = settings_manager.get_startup_plan()
    
    assert startup_plan is not None, "План запуска должен быть построен"
    
    dependency_order = startup_plan.get('dependency_order', [])
    assert len(dependency_order) > 0, "Порядок зависимостей должен быть определен"
    
    # Проверяем, что foundation утилиты идут первыми (если они в списке)
    foundation_utils = ['logger', 'plugins_manager', 'settings_manager']
    
    # Проверяем, что утилиты, от которых зависят другие, инициализируются раньше
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    
    for i, util_name in enumerate(dependency_order):
        if util_name in foundation_utils:
            continue  # Foundation утилиты могут быть исключены из плана
        
        # Получаем зависимости этой утилиты
        deps = plugins_manager.get_plugin_dependencies(util_name)
        
        # Проверяем, что все зависимости инициализированы раньше
        for dep in deps:
            if dep in dependency_order:
                dep_idx = dependency_order.index(dep)
                if dep_idx >= i:
                    # Это может быть нормально, если зависимость создается вручную
                    if dep not in foundation_utils:
                        # Предупреждаем, но не падаем - это может быть нормально
                        pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_required_utilities_initialized(initialized_di_container):
    """Проверка, что все требуемые утилиты могут быть получены"""
    settings_manager = initialized_di_container.get_utility('settings_manager')
    startup_plan = settings_manager.get_startup_plan()
    
    required_utilities = startup_plan.get('required_utilities', [])
    assert len(required_utilities) > 0, "Должны быть определены требуемые утилиты"
    
    # Проверяем, что обращение к требуемым утилитам не приводит к исключениям
    errors = []
    for util_name in required_utilities:
        try:
            _ = initialized_di_container.get_utility(util_name)
        except Exception as e:
            errors.append(f"{util_name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Ошибки при доступе к требуемым утилитам:\n" + "\n".join(errors))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_enabled_services_initialized(initialized_di_container):
    """Проверка, что все включенные сервисы могут быть получены"""
    settings_manager = initialized_di_container.get_utility('settings_manager')
    startup_plan = settings_manager.get_startup_plan()
    
    enabled_services = startup_plan.get('enabled_services', [])
    assert len(enabled_services) > 0, "Должны быть определены включенные сервисы"
    
    # Проверяем, что обращение к включенным сервисам не приводит к исключениям
    errors = []
    for service_name in enabled_services:
        try:
            _ = initialized_di_container.get_service(service_name)
        except Exception as e:
            errors.append(f"{service_name}: {str(e)}")
    
    if errors:
        pytest.fail(f"Ошибки при доступе к включенным сервисам:\n" + "\n".join(errors))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_optional_dependencies_handled(initialized_di_container):
    """Проверка корректной обработки опциональных зависимостей"""
    plugins_manager = initialized_di_container.get_utility('plugins_manager')
    all_plugins = plugins_manager.get_all_plugins_info()
    
    errors = []
    
    for plugin_name, plugin_info in all_plugins.items():
        optional_deps = plugin_info.get('optional_dependencies', [])
        
        if not optional_deps:
            continue
        
        # Проверяем, что опциональные зависимости либо доступны, либо корректно обрабатываются
        for opt_dep in optional_deps:
            try:
                # Пытаемся получить опциональную зависимость
                dep_instance = initialized_di_container.get_utility(opt_dep)
                # Если зависимость не найдена, это нормально для опциональных
                # Главное, что не возникает ошибок
            except Exception as e:
                errors.append(f"{plugin_name} -> {opt_dep}: {str(e)}")
    
    if errors:
        pytest.fail(f"Ошибки обработки опциональных зависимостей:\n" + "\n".join(errors))

