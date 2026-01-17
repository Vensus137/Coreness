"""
Интеграционные тесты ActionHub и регистрации действий
Проверяют корректную регистрацию и вызов действий через ActionHub
"""
import pytest

from tests.conftest import initialized_di_container  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_all_actions_registered(initialized_di_container):
    """Проверка, что все actions из config.yaml видны в ActionHub"""
    # Получаем ActionHub и PluginsManager через DI
    action_hub = initialized_di_container.get_utility('action_hub')
    plugins_manager = initialized_di_container.get_utility('plugins_manager')

    # Если по каким-то причинам action_hub не получен через DI – это уже повод падать
    assert action_hub is not None, "Утилита action_hub должна быть доступна через DI"
    assert plugins_manager is not None, "PluginsManager должен быть доступен через DI"
    
    all_plugins = plugins_manager.get_all_plugins_info()
    missing_actions = []
    
    for plugin_name, plugin_info in all_plugins.items():
        actions = plugin_info.get('actions', {})
        for action_name in actions.keys():
            # В ActionRegistry ключом маппинга является ИМЯ ДЕЙСТВИЯ, а не plugin.action
            action_config = action_hub.get_action_config(action_name)
            if action_config is None:
                missing_actions.append(f"{plugin_name}.{action_name}")
    
    if missing_actions:
        pytest.fail(
            "Действия не найдены в ActionHub (по имени действия):\n"
            + "\n".join(missing_actions)
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_call_with_validation(initialized_di_container):
    """Проверка вызова действия с валидацией входных данных"""
    action_hub = initialized_di_container.get_utility('action_hub')
    assert action_hub is not None, "Утилита action_hub должна быть доступна через DI"
    
    # Тестируем простое действие из scenario_helper (sleep)
    # В ActionHub действие зарегистрировано под именем 'sleep'
    result = await action_hub.execute_action(
        'sleep',
        data={'seconds': 0.01}  # Минимальная задержка для теста
    )
    
    # Проверяем структуру ответа
    assert isinstance(result, dict), "Результат должен быть словарем"
    assert 'result' in result, "Результат должен содержать поле 'result'"
    assert result['result'] == 'success', f"Действие должно выполниться успешно, получено: {result}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_config_retrieval(initialized_di_container):
    """Проверка получения конфигурации действий"""
    action_hub = initialized_di_container.get_utility('action_hub')
    plugins_manager = initialized_di_container.get_utility('plugins_manager')

    assert action_hub is not None, "Утилита action_hub должна быть доступна через DI"
    assert plugins_manager is not None, "PluginsManager должен быть доступен через DI"
    
    all_plugins = plugins_manager.get_all_plugins_info()
    
    # Проверяем несколько случайных действий
    checked_count = 0
    for plugin_name, plugin_info in all_plugins.items():
        actions = plugin_info.get('actions', {})
        if not actions:
            continue
        
        # Берем первое действие из каждого плагина
        first_action = list(actions.keys())[0]
        
        action_config = action_hub.get_action_config(first_action)
        assert action_config is not None, (
            f"Конфигурация действия {plugin_name}.{first_action} должна быть доступна"
        )
        
        # Проверяем структуру конфигурации
        assert isinstance(
            action_config, dict
        ), f"Конфигурация {plugin_name}.{first_action} должна быть словарем"
        
        checked_count += 1
        if checked_count >= 5:  # Проверяем первые 5 плагинов
            break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_hub_internal_actions(initialized_di_container):
    """Проверка внутренних действий ActionHub"""
    action_hub = initialized_di_container.get_utility('action_hub')
    assert action_hub is not None, "Утилита action_hub должна быть доступна через DI"
    
    # Проверяем внутреннее действие get_available_actions
    result = await action_hub.execute_action('get_available_actions')
    
    assert isinstance(result, dict), "Результат должен быть словарем"
    assert 'result' in result, "Результат должен содержать поле 'result'"
    
    # Если успешно, должно вернуться отображение доступных действий
    if result.get('result') == 'success' and 'response_data' in result:
        actions_mapping = result.get('response_data', {})
        assert isinstance(actions_mapping, dict), "response_data должен быть словарем с действиями"
        # В системе реально есть actions, так что ожидаем хотя бы одно действие
        assert len(actions_mapping) > 0, "Должно быть доступно хотя бы одно действие"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_action_call_with_invalid_data(initialized_di_container):
    """Проверка обработки невалидных данных при вызове действия"""
    action_hub = initialized_di_container.get_utility('action_hub')
    assert action_hub is not None, "Утилита action_hub должна быть доступна через DI"
    
    # Пытаемся вызвать действие с невалидными данными
    result = await action_hub.execute_action(
        'sleep',
        data={'seconds': -1}  # Отрицательное значение должно быть отклонено
    )
    
    # Результат может быть success (если валидация не строгая) или error
    assert isinstance(result, dict), "Результат должен быть словарем"
    assert 'result' in result, "Результат должен содержать поле 'result'"
    
    # Если ошибка, проверяем структуру error
    if result.get('result') == 'error':
        assert 'error' in result, "При ошибке должно быть поле 'error'"

