import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ScenariosManager:
    """Менеджер сценариев и триггеров"""

    @staticmethod
    def _find_project_root(start_path: Path) -> Path:
        """Надежно определяет корень проекта"""
        # Сначала проверяем переменную окружения
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and Path(env_root).exists():
            return Path(env_root)
        
        # Ищем по ключевым файлам/папкам
        current = start_path
        while current != current.parent:
            # Проверяем наличие ключевых файлов проекта
            if (current / "main.py").exists() and \
               (current / "plugins").exists() and \
               (current / "app").exists():
                return current
            current = current.parent
        
        # Если не найден - используем fallback
        return start_path.parent.parent.parent.parent

    def __init__(self, config_dir: str = "config", max_actions_limit: int = 50, max_nesting_depth: int = 10, **kwargs):
        self.logger = kwargs['logger']
        self.config_dir = config_dir
        self._max_actions_limit = max_actions_limit
        self._max_nesting_depth = max_nesting_depth
        
        # Кеш для сценариев и триггеров
        self._cache: Dict[str, Any] = {}
        self._scenario_name_map: Dict[str, str] = {}  # name -> full_key для поиска по короткому имени

        # Устанавливаем корень проекта надежным способом
        self.project_root = self._find_project_root(Path(__file__))

        # Загружаем сценарии и триггеры
        self._load_scenarios_and_triggers()

    def _load_scenarios_and_triggers(self):
        """Загрузка всех сценариев и триггеров"""
        self.logger.info("Загрузка сценариев и триггеров...")
        self._cache.clear()
        self._scenario_name_map.clear()

        # Загружаем системные триггеры
        system_triggers = self._load_yaml_file('system/triggers.yaml')

        # Загружаем пользовательские триггеры
        user_triggers = self._load_yaml_file('triggers.yaml')

        # Объединяем: системные имеют приоритет
        merged_triggers = self._merge_triggers(user_triggers, system_triggers)
        self._cache['triggers'] = merged_triggers

        # Загружаем системные групповые триггеры
        system_group_triggers = self._load_yaml_file('system/group_triggers.yaml')
        # Загружаем пользовательские групповые триггеры
        user_group_triggers = self._load_yaml_file('group_triggers.yaml')
        # Объединяем: системные имеют приоритет
        merged_group_triggers = self._merge_triggers(user_group_triggers, system_group_triggers)
        self._cache['group_triggers'] = merged_group_triggers

        # Загружаем системные сценарии
        system_scenarios = self._load_scenarios_from_dir('system/scenarios')

        # Загружаем пользовательские сценарии
        user_scenarios = self._load_scenarios_from_dir('scenarios')

        # Объединяем: системные имеют приоритет
        merged_scenarios = self._merge_scenarios(user_scenarios, system_scenarios)
        self._cache['scenarios'] = merged_scenarios
        self.logger.info(f"Загружено сценариев: {len(merged_scenarios)}")

    def _load_yaml_file(self, relative_path: str) -> dict:
        """Загружает YAML файл по относительному пути от config_dir"""
        file_path = os.path.join(self.config_dir, relative_path)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_scenarios_from_dir(self, relative_dir: str) -> dict:
        """Рекурсивно загружает сценарии из указанной директории и всех подпапок"""
        scenarios = {}
        scenarios_dir = os.path.join(self.config_dir, relative_dir)

        if os.path.isdir(scenarios_dir):
            for root, _, files in os.walk(scenarios_dir):
                for filename in files:
                    if filename.endswith(('.yaml', '.yml')):
                        file_path = os.path.join(root, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_scenarios = yaml.safe_load(f) or {}
                            # Получаем относительный путь от scenarios_dir до файла
                            rel_path = os.path.relpath(file_path, scenarios_dir)
                            # Удаляем расширение и заменяем разделители на точки
                            file_prefix = rel_path.replace('\\', '/').replace('/', '.')
                            if file_prefix.endswith('.yaml'):
                                file_prefix = file_prefix[:-5]
                            elif file_prefix.endswith('.yml'):
                                file_prefix = file_prefix[:-4]
                            for scenario_name, scenario_data in file_scenarios.items():
                                full_key = f"{file_prefix}.{scenario_name}"
                                scenarios[full_key] = scenario_data
                                if scenario_name in self._scenario_name_map:
                                    self.logger.warning(f"Дублирование названия сценария '{scenario_name}'. Используется первый найденный.")
                                else:
                                    self._scenario_name_map[scenario_name] = full_key
        return scenarios

    def _merge_scenarios(self, base: dict, override: dict) -> dict:
        """Объединяет два словаря сценариев, override (системные) имеет приоритет"""
        result = dict(base)
        for k, v in override.items():
            result[k] = v  # Системные сценарии перезаписывают пользовательские
        return result

    def _merge_triggers(self, base: dict, override: dict) -> dict:
        """Рекурсивно объединяет два словаря триггеров, override (системные) имеет приоритет."""
        if not isinstance(base, dict):
            return override
        result = dict(base)
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_triggers(result[k], v)
            else:
                result[k] = v
        return result

    # === Публичные методы ===

    def get_scenario(self, key: str) -> Optional[dict]:
        """Получить оригинальный сценарий по полному или короткому ключу."""
        # Сначала ищем по полному ключу
        scenario = self._cache.get('scenarios', {}).get(key)
        if scenario is not None:
            return scenario
        # Если не найдено — ищем по короткому имени
        full_key = self._scenario_name_map.get(key)
        if full_key:
            return self._cache.get('scenarios', {}).get(full_key)
        return None

    def get_all_scenarios(self) -> dict:
        """Получить все оригинальные сценарии"""
        return self._cache.get('scenarios', {}).copy()

    def get_triggers(self) -> dict:
        """Получить триггеры"""
        return self._cache.get('triggers', {})

    def get_group_triggers(self) -> dict:
        """Получить групповые триггеры (для публичных чатов)"""
        return self._cache.get('group_triggers', {})

    def get_scenario_key(self, name_or_key: str) -> Optional[str]:
        """Вернуть полное имя сценария (file.scenario) по короткому или полному имени. Если не найдено — None."""
        if name_or_key in self._cache.get('scenarios', {}):
            return name_or_key
        full_key = self._scenario_name_map.get(name_or_key)
        if full_key:
            return full_key
        return None

    def get_scenario_name(self, name_or_key: str) -> Optional[str]:
        """Вернуть короткое имя сценария по короткому или полному имени. Если не найдено — None."""
        if name_or_key in self._scenario_name_map:
            return name_or_key
        if name_or_key in self._cache.get('scenarios', {}):
            return name_or_key.split('.')[-1]
        return None

    def reload(self):
        """Перезагрузить все сценарии и триггеры"""
        self.logger.info("Перезагрузка сценариев и триггеров...")
        self._load_scenarios_and_triggers() 