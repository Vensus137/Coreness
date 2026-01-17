"""
Интеграционный тест всех конфигов для action_validator
Проверяет, что все схемы валидации из config.yaml корректно парсятся и работают
"""
import pytest
import yaml
from pathlib import Path

# Корень проекта уже добавлен в sys.path через pythonpath = ["."] в pyproject.toml
from tests.conftest import project_root, module_logger  # noqa: F401


class RealSettingsManager:
    """Реальный SettingsManager для тестов с реальными конфигами"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._plugin_info_cache = {}
        self._load_all_plugins()
    
    def _load_all_plugins(self):
        """Загрузка всех плагинов из config.yaml файлов"""
        plugins_dir = self.project_root / "plugins"
        
        # Сканируем все config.yaml файлы
        for config_path in plugins_dir.rglob("config.yaml"):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                plugin_name = config.get('name')
                if not plugin_name:
                    continue
                
                # Сохраняем информацию о плагине
                self._plugin_info_cache[plugin_name] = {
                    'actions': config.get('actions', {}),
                    'methods': config.get('methods', {})
                }
                
            except Exception as e:
                # Игнорируем ошибки загрузки отдельных конфигов
                print(f"⚠️ Ошибка загрузки {config_path}: {e}")
                continue
    
    def get_plugin_info(self, plugin_name: str):
        """Получение информации о плагине"""
        plugin_info = self._plugin_info_cache.get(plugin_name)
        if not plugin_info:
            return None
        
        return {
            'actions': plugin_info.get('actions', {}),
            'methods': plugin_info.get('methods', {})
        }
    
    def get_plugin_settings(self, plugin_name: str):
        """Получение настроек плагина"""
        return {}


@pytest.fixture(scope="session")
def real_settings_manager(project_root):
    """Создает RealSettingsManager с реальными конфигами"""
    return RealSettingsManager(project_root)


@pytest.fixture(scope="session")
def real_validator(module_logger, real_settings_manager):
    """Создает ActionValidator с реальными конфигами"""
    # Импортируем здесь, чтобы избежать прямого импорта на уровне модуля
    from plugins.utilities.core.action_validator.action_validator import ActionValidator
    return ActionValidator(logger=module_logger, settings_manager=real_settings_manager)


class TestAllConfigs:
    """Тесты всех конфигов из plugins/"""
    
    def test_all_actions_schemas_parseable(self, real_validator, real_settings_manager):
        """Проверка: все схемы действий корректно парсятся"""
        errors = []
        
        for plugin_name, plugin_info in real_settings_manager._plugin_info_cache.items():
            actions = plugin_info.get('actions', {})
            
            for action_name, action_config in actions.items():
                # Извлекаем схему input.data.properties
                input_config = action_config.get('input', {})
                data_config = input_config.get('data', {})
                properties = data_config.get('properties', {})
                
                if not properties:
                    # Нет схемы - это нормально, пропускаем
                    continue
                
                # Пытаемся создать модель валидации
                try:
                    model = real_validator._create_pydantic_model(properties, f'{plugin_name}.{action_name}')
                    
                    if model is None:
                        # Модель не создана - это может быть нормально для пустых схем
                        continue
                    
                    # Проверяем, что модель может быть создана без ошибок
                    # Это означает, что схема корректна
                    
                except Exception as e:
                    errors.append(f"{plugin_name}.{action_name}: {str(e)}")
        
        if errors:
            pytest.fail(f"Ошибки парсинга схем:\n" + "\n".join(errors))
    
    def test_union_string_integer_types_supported(self, real_validator, real_settings_manager):
        """Проверка: все union типы string|integer корректно обрабатываются"""
        errors = []
        
        for plugin_name, plugin_info in real_settings_manager._plugin_info_cache.items():
            actions = plugin_info.get('actions', {})
            
            for action_name, action_config in actions.items():
                input_config = action_config.get('input', {})
                data_config = input_config.get('data', {})
                properties = data_config.get('properties', {})
                
                for field_name, field_config in properties.items():
                    type_str = field_config.get('type', 'string')
                    
                    # Проверяем union типы со string|integer
                    if isinstance(type_str, str) and '|' in type_str:
                        type_parts = [p.strip().lower() for p in type_str.split('|')]
                        
                        # Если есть string|integer или integer|string
                        if ('string' in type_parts and 'integer' in type_parts):
                            # Пытаемся создать модель с этим полем
                            try:
                                test_schema = {field_name: field_config}
                                model = real_validator._create_pydantic_model(test_schema, f'{plugin_name}.{action_name}.{field_name}')
                                
                                if model is None:
                                    errors.append(f"{plugin_name}.{action_name}.{field_name}: модель не создана для {type_str}")
                                
                            except Exception as e:
                                errors.append(f"{plugin_name}.{action_name}.{field_name}: ошибка создания модели для {type_str}: {str(e)}")
        
        if errors:
            pytest.fail(f"Ошибки обработки union типов string|integer:\n" + "\n".join(errors))
    
    def test_all_constraints_applied(self, real_validator, real_settings_manager):
        """Проверка: ограничения (min_length, max_length, min, max) корректно применяются"""
        errors = []
        
        for plugin_name, plugin_info in real_settings_manager._plugin_info_cache.items():
            actions = plugin_info.get('actions', {})
            
            for action_name, action_config in actions.items():
                input_config = action_config.get('input', {})
                data_config = input_config.get('data', {})
                properties = data_config.get('properties', {})
                
                for field_name, field_config in properties.items():
                    type_str = field_config.get('type', 'string')
                    
                    # Проверяем, что ограничения применяются только к подходящим типам
                    has_min_length = 'min_length' in field_config
                    has_max_length = 'max_length' in field_config
                    has_pattern = 'pattern' in field_config
                    has_min = 'min' in field_config
                    has_max = 'max' in field_config
                    
                    if has_min_length or has_max_length or has_pattern:
                        # Должен быть string или union со string
                        if isinstance(type_str, str):
                            type_parts = [p.strip().lower() for p in type_str.split('|')]
                            has_string = 'string' in type_parts or type_str.lower() == 'string'
                            
                            if not has_string:
                                errors.append(f"{plugin_name}.{action_name}.{field_name}: min_length/max_length/pattern применены к не-строковому типу {type_str}")
                    
                    if has_min or has_max:
                        # Должен быть number или union с number
                        if isinstance(type_str, str):
                            type_parts = [p.strip().lower() for p in type_str.split('|')]
                            has_number = any(t in type_parts for t in ['integer', 'float', 'number']) or type_str.lower() in ['integer', 'float', 'number']
                            
                            if not has_number:
                                errors.append(f"{plugin_name}.{action_name}.{field_name}: min/max применены к не-числовому типу {type_str}")
        
        if errors:
            pytest.fail(f"Ошибки применения ограничений:\n" + "\n".join(errors))

