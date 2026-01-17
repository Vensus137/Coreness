"""
Интеграционный тест структуры ответов действий
Проверяет, что все действия в конфигах имеют правильный формат output (result, error, response_data)
"""
import pytest
import yaml
from pathlib import Path

# Корень проекта уже добавлен в sys.path через pythonpath = ["."] в pyproject.toml
from tests.conftest import project_root  # noqa: F401


class TestResponseStructure:
    """Тесты структуры ответов действий"""
    
    def test_all_actions_have_correct_output_structure(self, project_root):
        """Проверка: все действия имеют правильную структуру output"""
        plugins_dir = project_root / "plugins"
        errors = []
        
        # Сканируем все config.yaml файлы
        for config_path in plugins_dir.rglob("config.yaml"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                plugin_name = config.get('name', 'unknown')
                actions = config.get('actions', {})
                
                for action_name, action_config in actions.items():
                    output_config = action_config.get('output', {})
                    
                    if not output_config:
                        # Нет output - это нормально для некоторых действий
                        continue
                    
                    # Проверяем наличие result
                    result_config = output_config.get('result')
                    if not result_config:
                        errors.append(f"{plugin_name}.{action_name}: отсутствует 'result' в output")
                    
                    # Проверяем формат error (должен быть объект с code, message, details)
                    error_config = output_config.get('error')
                    if error_config:
                        if not isinstance(error_config, dict):
                            errors.append(f"{plugin_name}.{action_name}: 'error' должен быть объектом, получен {type(error_config).__name__}")
                        else:
                            # Проверяем структуру error
                            properties = error_config.get('properties', {})
                            
                            if 'code' not in properties:
                                errors.append(f"{plugin_name}.{action_name}: 'error' должен содержать 'code'")
                            
                            if 'message' not in properties:
                                errors.append(f"{plugin_name}.{action_name}: 'error' должен содержать 'message'")
                            
                            # details опциональны, но если есть - должны быть массивом
                            details_config = properties.get('details', {})
                            if details_config and details_config.get('type') != 'array':
                                errors.append(f"{plugin_name}.{action_name}: 'error.details' должен быть массивом")
                    
                    # Проверяем response_data (если есть)
                    response_data_config = output_config.get('response_data')
                    if response_data_config:
                        if not isinstance(response_data_config, dict):
                            errors.append(f"{plugin_name}.{action_name}: 'response_data' должен быть объектом, получен {type(response_data_config).__name__}")
                
            except Exception as e:
                errors.append(f"Ошибка загрузки {config_path}: {str(e)}")
        
        if errors:
            pytest.fail(f"Ошибки структуры output:\n" + "\n".join(errors))
    
    def test_all_actions_error_format_is_object(self, project_root):
        """Проверка: все действия используют новый формат error (объект, а не строка)"""
        plugins_dir = project_root / "plugins"
        errors = []
        
        # Сканируем все config.yaml файлы
        for config_path in plugins_dir.rglob("config.yaml"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                plugin_name = config.get('name', 'unknown')
                actions = config.get('actions', {})
                
                for action_name, action_config in actions.items():
                    output_config = action_config.get('output', {})
                    
                    if not output_config:
                        continue
                    
                    error_config = output_config.get('error')
                    if error_config:
                        # Проверяем, что error - это объект, а не строка
                        if isinstance(error_config, str):
                            errors.append(f"{plugin_name}.{action_name}: 'error' должен быть объектом, получена строка")
                        elif isinstance(error_config, dict):
                            error_type = error_config.get('type')
                            if error_type == 'string':
                                errors.append(f"{plugin_name}.{action_name}: 'error.type' должен быть 'object', получен 'string' (старый формат)")
            
            except Exception as e:
                errors.append(f"Ошибка загрузки {config_path}: {str(e)}")
        
        if errors:
            pytest.fail(f"Ошибки формата error (должен быть объект):\n" + "\n".join(errors))

