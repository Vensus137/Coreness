"""
Tenant Parser - подмодуль для парсинга конфигураций тенантов
Парсит конфигурации тенантов из файлов (отдельно bot и scenarios)
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class TenantParser:
    """
    Подмодуль для парсинга конфигураций тенантов
    Парсит отдельные части: bot/config или scenarios
    """
    
    def __init__(self, logger, settings_manager, condition_parser):
        self.logger = logger
        self.settings_manager = settings_manager
        self.condition_parser = condition_parser
        
        # Получаем настройки из global (общие для всех сервисов)
        global_settings = self.settings_manager.get_global_settings()
        tenants_config_path = global_settings.get("tenants_config_path", "config/tenant")
        
        # Получаем настройку максимальной глубины вложенности для storage
        tenant_hub_settings = self.settings_manager.get_plugin_settings("tenant_hub")
        self.storage_max_depth = tenant_hub_settings.get("storage_max_depth", 10)
        
        # Путь к тенантам (единая папка без разделения на system/public)
        # Папка уже создана в tenant_hub, проверка не нужна
        from pathlib import Path
        project_root = self.settings_manager.get_project_root()
        self.tenants_path = Path(project_root) / tenants_config_path
    
    # === Публичные методы ===
    
    async def parse_bot(self, tenant_id: int) -> Dict[str, Any]:
        """
        Парсит только конфигурацию бота и команды (без сценариев)
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id не указан"
                    }
                }
            
            # Получаем путь к тенанту
            tenant_path = await self._get_tenant_path(tenant_id)
            if not tenant_path:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Тенант {tenant_id} не найден"
                    }
                }
            
            # Парсим tg_bot.yaml
            bot_data = await self._parse_bot_data(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": bot_data
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга конфигурации бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_scenarios(self, tenant_id: int) -> Dict[str, Any]:
        """
        Парсит только сценарии тенанта (без бота)
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id не указан"
                    }
                }
            
            # Получаем путь к тенанту
            tenant_path = await self._get_tenant_path(tenant_id)
            if not tenant_path:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Тенант {tenant_id} не найден"
                    }
                }
            
            # Парсим сценарии
            scenario_data = await self._parse_scenarios(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": scenario_data
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга сценариев: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_storage(self, tenant_id: int) -> Dict[str, Any]:
        """
        Парсит только storage тенанта (без бота и сценариев)
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id не указан"
                    }
                }
            
            # Получаем путь к тенанту
            tenant_path = await self._get_tenant_path(tenant_id)
            if not tenant_path:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Тенант {tenant_id} не найден"
                    }
                }
            
            # Парсим storage
            storage_data = await self._parse_storage(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": storage_data
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_tenant_config(self, tenant_id: int) -> Dict[str, Any]:
        """
        Парсит конфиг тенанта из файла config.yaml
        Возвращает словарь с конфигом (например, {"ai_token": "..."})
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id не указан"
                    }
                }
            
            # Получаем путь к тенанту
            tenant_path = await self._get_tenant_path(tenant_id)
            if not tenant_path:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Тенант {tenant_id} не найден"
                    }
                }
            
            # Парсим config.yaml
            config = await self._parse_tenant_config_file(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": config
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга атрибутов тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    async def parse_tenant(self, tenant_id: int) -> Dict[str, Any]:
        """
        Парсит всю конфигурацию тенанта (bot + scenarios)
        """
        try:
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id не указан"
                    }
                }
            
            # Получаем путь к тенанту
            tenant_path = await self._get_tenant_path(tenant_id)
            if not tenant_path:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Тенант {tenant_id} не найден"
                    }
                }
            
            # Парсим bot
            bot_data = await self._parse_bot_data(tenant_id, tenant_path)
            
            # Парсим scenarios
            scenario_data = await self._parse_scenarios(tenant_id, tenant_path)
            
            # Парсим storage
            storage_data = await self._parse_storage(tenant_id, tenant_path)
            
            return {
                "result": "success",
                "response_data": {
                    "bot": bot_data.get("bot", {}),
                    "bot_commands": bot_data.get("bot_commands", []),
                    "scenarios": scenario_data.get("scenarios", []),
                    "storage": storage_data.get("storage", {})
                }
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга конфигурации тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "PARSE_ERROR",
                    "message": str(e)
                }
            }
    
    # === Внутренние методы ===
    
    async def _get_tenant_path(self, tenant_id: int) -> Optional[Path]:
        """Получает путь к папке тенанта"""
        try:
            tenant_name = f"tenant_{tenant_id}"
            tenant_path = self.tenants_path / tenant_name
            
            # Проверяем существование папки тенанта
            if not tenant_path.exists():
                self.logger.warning(f"Папка тенанта не найдена: {tenant_path}")
                return None
            
            return tenant_path
            
        except Exception as e:
            self.logger.error(f"Ошибка получения пути к тенанту {tenant_id}: {e}")
            return None
    
    async def _parse_bot_data(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Парсит данные бота (bot + bot_commands)"""
        bot_data = {
            "bot": {},
            "bot_commands": []
        }
        
        # Парсим tg_bot.yaml
        bot_file = tenant_path / "tg_bot.yaml"
        if bot_file.exists():
            yaml_data = await self._parse_yaml_file(bot_file)
            
            # Извлекаем данные бота
            # bot_token может быть None если не указан в конфиге (тогда используется из БД)
            bot_token = yaml_data.get("bot_token")
            # Если токен пустая строка, считаем что его нет
            if bot_token is not None and not bot_token.strip():
                bot_token = None
            
            bot_data["bot"] = {
                "bot_token": bot_token,
                "is_active": yaml_data.get("is_active", True)
            }
            
            # Извлекаем команды бота
            commands = yaml_data.get("commands", [])
            for cmd in commands:
                bot_data["bot_commands"].append({
                    "action_type": "register",
                    "command": cmd.get("command"),
                    "description": cmd.get("description"),
                    "scope": cmd.get("scope", "default")
                })
            
            # Извлекаем команды для очистки
            command_clear = yaml_data.get("command_clear", [])
            for cmd in command_clear:
                bot_data["bot_commands"].append({
                    "action_type": "clear",
                    "command": None,
                    "description": None,
                    "scope": cmd.get("scope", "default"),
                    "chat_id": cmd.get("chat_id"),
                    "user_id": cmd.get("user_id")
                })
        else:
            self.logger.warning(f"[Tenant-{tenant_id}] Файл tg_bot.yaml не найден")
        
        return bot_data
    
    async def _parse_scenarios(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Парсит все сценарии тенанта"""
        scenarios = []
        scenarios_path = tenant_path / "scenarios"
        
        if scenarios_path.exists():
            # Парсим все YAML файлы рекурсивно из scenarios (включая подпапки)
            for yaml_file in scenarios_path.rglob("*.yaml"):
                file_scenarios = await self._parse_scenario_file(yaml_file)
                scenarios.extend(file_scenarios)
        
        return {
            "scenarios": scenarios
        }
    
    async def _parse_scenario_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Парсит файл сценариев"""
        scenarios = []
        
        try:
            loop = asyncio.get_event_loop()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = await loop.run_in_executor(None, f.read)
            
            yaml_content = yaml.safe_load(content) or {}
            
            # Обрабатываем каждый сценарий в файле
            for scenario_name, scenario_data in yaml_content.items():
                if isinstance(scenario_data, dict):
                    # Парсим триггеры
                    parsed_trigger = await self._parse_scenario_trigger(scenario_data.get("trigger", []))
                    
                    # Парсим шаги
                    parsed_step = await self._parse_scenario_step(scenario_data.get("step", []))
                    
                    scenario = {
                        "scenario_name": scenario_name,
                        "description": scenario_data.get("description"),
                        "schedule": scenario_data.get("schedule"),  # Cron выражение для scheduled сценариев
                        "trigger": parsed_trigger,
                        "step": parsed_step
                    }
                    scenarios.append(scenario)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга файла сценариев {file_path}: {e}")
        
        return scenarios
    
    async def _parse_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Парсит YAML файл"""
        try:
            loop = asyncio.get_event_loop()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = await loop.run_in_executor(None, f.read)
            return yaml.safe_load(content) or {}
        except Exception as e:
            self.logger.error(f"Ошибка чтения файла {file_path}: {e}")
            return {}
    
    async def _parse_scenario_trigger(self, trigger: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Парсит триггеры сценария в формат БД используя condition_parser"""
        parsed_trigger = []
        
        for trigger_data in trigger:
            # Используем condition_parser.build_condition для создания условия
            condition_expression = await self.condition_parser.build_condition([trigger_data])
            
            parsed_trigger.append({
                "condition_expression": condition_expression
            })
        
        return parsed_trigger
    
    async def _parse_scenario_step(self, step: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Парсит шаги сценария в формат БД"""
        parsed_step = []
        
        for step_order, step_data in enumerate(step):
            # Берем params как есть (dict)
            params = step_data.get("params", {})
            
            parsed_step.append({
                "step_order": step_order,
                "action_name": step_data.get("action") or step_data.get("action_name"),
                "params": params,
                "is_async": step_data.get("async", False),
                "action_id": step_data.get("action_id"),
                "transition": step_data.get("transition", [])
            })
        
        return parsed_step
    
    async def _parse_storage(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """Парсит секцию storage из конфига тенанта"""
        storage = {}
        storage_path = tenant_path / "storage"
        
        if storage_path.exists() and storage_path.is_dir():
            # Парсим все YAML файлы в папке storage
            for yaml_file in storage_path.glob("*.yaml"):
                try:
                    # Парсим содержимое файла
                    yaml_content = await self._parse_yaml_file(yaml_file)
                    
                    # Ожидаем структуру: {group_key: {key: value}}
                    if not isinstance(yaml_content, dict):
                        self.logger.warning(f"[Tenant-{tenant_id}] Файл {yaml_file.name} содержит невалидную структуру, ожидается словарь")
                        continue
                    
                    # Обрабатываем каждую группу в файле
                    for group_key, group_data in yaml_content.items():
                        if not isinstance(group_data, dict):
                            self.logger.warning(f"[Tenant-{tenant_id}] Группа '{group_key}' в файле {yaml_file.name} содержит невалидную структуру, ожидается словарь")
                            continue
                        
                        # Валидируем и нормализуем атрибуты группы
                        validated_group = await self._validate_and_normalize_storage_group(
                            tenant_id, group_key, group_data, yaml_file.name
                        )
                        
                        if validated_group:
                            # Объединяем с существующими данными группы (если группа уже была в другом файле)
                            if group_key in storage:
                                # Объединяем атрибуты, новые перезаписывают старые
                                storage[group_key].update(validated_group)
                            else:
                                storage[group_key] = validated_group
                        
                except Exception as e:
                    self.logger.error(f"[Tenant-{tenant_id}] Ошибка парсинга файла storage {yaml_file.name}: {e}")
        
        return {
            "storage": storage
        }
    
    async def _validate_and_normalize_storage_group(
        self, tenant_id: int, group_key: str, group_data: Dict[str, Any], file_name: str
    ) -> Dict[str, Any]:
        """
        Валидирует и нормализует группу атрибутов storage
        
        Поддерживает:
        - Простые типы (str, int, float, bool, None)
        - Массивы с простыми типами или сложными структурами (dict, list)
        - Словари (dict) с любыми поддерживаемыми типами значений
        - Рекурсивная валидация вложенных структур (максимальная глубина настраивается через config.yaml: tenant_hub.storage_max_depth)
        """
        validated_group = {}
        
        for key, value in group_data.items():
            validated_value = await self._validate_storage_value(
                tenant_id, group_key, key, value, file_name, depth=0, max_depth=self.storage_max_depth
            )
            
            if validated_value is not None:
                validated_group[key] = validated_value
        
        return validated_group
    
    async def _validate_storage_value(
        self, tenant_id: int, group_key: str, key: str, value: Any, file_name: str, depth: int = 0, max_depth: int = 10
    ) -> Any:
        """
        Рекурсивно валидирует значение storage с поддержкой сложных структур
        
        Поддерживает:
        - Простые типы: str, int, float, bool, None
        - Массивы: могут содержать простые типы, словари или другие массивы
        - Словари: могут содержать любые поддерживаемые типы значений
        
        Параметры:
        - depth: текущая глубина вложенности
        - max_depth: максимальная глубина вложенности для предотвращения рекурсии
        """
        # Проверка глубины вложенности
        if depth > max_depth:
            self.logger.warning(
                f"[Tenant-{tenant_id}] Атрибут '{group_key}.{key}' в файле {file_name} "
                f"превышает максимальную глубину вложенности ({max_depth}), пропускаем."
            )
            return None
        
        # Обработка словарей (JSON объекты)
        if isinstance(value, dict):
            validated_dict = {}
            for dict_key, dict_value in value.items():
                nested_key = f"{key}.{dict_key}" if depth > 0 else f"{group_key}.{key}.{dict_key}"
                validated_nested = await self._validate_storage_value(
                    tenant_id, group_key, nested_key, dict_value, file_name, 
                    depth=depth + 1, max_depth=max_depth
                )
                if validated_nested is not None:
                    validated_dict[dict_key] = validated_nested
            
            return validated_dict if validated_dict else None
        
        # Обработка массивов
        elif isinstance(value, list):
            validated_list = []
            invalid_items = []
            
            for i, item in enumerate(value):
                array_key = f"{key}[{i}]" if depth > 0 else f"{group_key}.{key}[{i}]"
                validated_item = await self._validate_storage_value(
                    tenant_id, group_key, array_key, item, file_name,
                    depth=depth + 1, max_depth=max_depth
                )
                
                if validated_item is not None:
                    validated_list.append(validated_item)
                else:
                    invalid_items.append(i)
            
            # Логируем некорректные элементы только если есть валидные
            if invalid_items and validated_list:
                for i in invalid_items:
                    self.logger.warning(
                        f"[Tenant-{tenant_id}] Элемент '{group_key}.{key}[{i}]' в файле {file_name} "
                        f"содержит неподдерживаемый тип, пропускаем."
                    )
            
            # Возвращаем валидированный массив только если он не пустой или пустой массив был исходно валидным
            if validated_list or (not invalid_items and len(value) == 0):
                return validated_list
            elif invalid_items:
                # Если массив полностью некорректный, логируем один раз
                self.logger.warning(
                    f"[Tenant-{tenant_id}] Атрибут '{group_key}.{key}' в файле {file_name} "
                    f"содержит массив с некорректными элементами, пропускаем."
                )
            return None
        
        # Обработка простых типов
        elif isinstance(value, (str, int, float, bool, type(None))):
            return value
        
        # Обработка других типов - пытаемся преобразовать в строку
        else:
            original_type = type(value).__name__
            try:
                str_value = str(value)
                self.logger.warning(
                    f"[Tenant-{tenant_id}] Атрибут '{group_key}.{key}' в файле {file_name} "
                    f"был преобразован в строку из {original_type}"
                )
                return str_value
            except Exception as e:
                self.logger.error(
                    f"[Tenant-{tenant_id}] Не удалось преобразовать атрибут '{group_key}.{key}' "
                    f"в файле {file_name}: {e}. Пропускаем."
                )
                return None
    
    async def _parse_tenant_config_file(self, tenant_id: int, tenant_path: Path) -> Dict[str, Any]:
        """
        Парсит файл config.yaml с конфигом тенанта
        Возвращает словарь с конфигом (например, {"ai_token": "..."})
        Если файла нет или поле пустое → не добавляет в словарь
        """
        config = {}
        tenant_file = tenant_path / "config.yaml"
        
        if tenant_file.exists():
            yaml_data = await self._parse_yaml_file(tenant_file)
            
            # Извлекаем ai_token (приоритет) или openrouter_token (обратная совместимость)
            ai_token = yaml_data.get("ai_token")
            if not ai_token:
                # Обратная совместимость: проверяем старое поле
                ai_token = yaml_data.get("openrouter_token")
            # Если токен пустая строка, считаем что его нет
            if ai_token is not None and ai_token.strip():
                config["ai_token"] = ai_token.strip()
                # Также сохраняем в старое поле для обратной совместимости
                config["openrouter_token"] = ai_token.strip()
        else:
            # Файл не существует - это нормально, возвращаем пустой словарь
            pass
        
        return config

