"""
Access Validator - модуль для валидации доступа к действиям
"""

from typing import Any, Dict, List


class AccessValidator:
    """
    Валидатор доступа к действиям
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        self.groups = {}
        self.access_rules = {}
        
        # Загружаем конфигурацию доступа
        self._load_access_config()
    
    def _load_access_config(self):
        """Загрузка групп и правил доступа из настроек ActionHub"""
        try:
            # Получаем настройки плагина ActionHub через settings_manager
            plugin_settings = self.settings_manager.get_plugin_settings('action_hub')
            
            # Загружаем группы
            self.groups = plugin_settings.get('groups', {})
            
            # Загружаем правила доступа
            self.access_rules = plugin_settings.get('access_rules', {})
            
            self.logger.info(f"AccessValidator: загружены группы: {list(self.groups.keys())}")
            self.logger.info(f"AccessValidator: загружены правила доступа: {list(self.access_rules.keys())}")
            
        except Exception as e:
            self.logger.error(f"AccessValidator: ошибка загрузки конфигурации доступа: {e}")
            self.groups = {}
            self.access_rules = {}
    
    def validate_action_access(self, action_name: str, action_config: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация доступа к действию на основе его конфигурации"""
        try:
            access_rules = action_config.get('access_rules', [])
            
            # Если нет правил доступа - пропускаем проверку
            if not access_rules:
                return {"result": "success"}
            
            # Выполняем все правила действия
            for rule_name in access_rules:
                rule_result = self._execute_access_rule(rule_name, data)
                if rule_result.get("result") != "success":
                    return rule_result
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка валидации доступа для действия '{action_name}': {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Ошибка валидации доступа: {str(e)}"
                }
            }
    
    def _execute_access_rule(self, rule_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение конкретного правила доступа по имени"""
        try:
            rule_config = self.access_rules.get(rule_name)
            if not rule_config:
                self.logger.warning(f"Правило {rule_name} не найдено в конфигурации")
                return {"result": "success"}
            
            # Унифицированная структура: allowed_groups + check_fields
            allowed_groups = rule_config.get('allowed_groups', [])
            check_fields = rule_config.get('check_fields', [])
            
            # Универсальное правило доступа для всех правил
            return self._check_universal_access(allowed_groups, check_fields, data)
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения правила {rule_name}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _check_universal_access(self, allowed_groups: List[str], check_fields: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Универсальная проверка доступа"""
        try:
            # Если есть check_fields - проверяем на подмену данных
            if check_fields:
                return self._check_data_integrity(allowed_groups, check_fields, data)
            
            # Если нет check_fields - проверяем только группы доступа
            system_data = data.get('system', {})
            return self._check_group_access(allowed_groups, system_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка универсальной проверки доступа: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _check_group_access(self, allowed_groups: List[str], system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Проверка доступа по группам - проверяем входят ли системные атрибуты в требования группы"""
        try:
            if not allowed_groups:
                return {"result": "success"}
            
            # Проверяем каждую разрешенную группу
            for group_name in allowed_groups:
                if group_name not in self.groups:
                    continue
                
                group_requirements = self.groups[group_name]
                group_matches = True
                
                # Проверяем все требования группы
                for field_name, allowed_values in group_requirements.items():
                    field_value = system_data.get(field_name)
                    if field_value not in allowed_values:
                        group_matches = False
                        break
                
                # Если группа подошла - доступ разрешен
                if group_matches:
                    return {"result": "success"}
            
            # Ни одна группа не подошла
            return {
                "result": "error",
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": f"Системные данные не соответствуют требованиям ни одной из групп: {allowed_groups}"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки доступа по группам: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _check_data_integrity(self, allowed_groups: List[str], check_fields: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Проверка целостности данных (защита от подмены)"""
        try:
            if not check_fields:
                return {"result": "success"}
            
            # Проверяем каждое поле на подмену
            for field in check_fields:
                system_value = data.get('system', {}).get(field)
                public_value = data.get(field)
                
                if system_value is None:
                    continue  # Пропускаем если системное значение отсутствует
                
                # Если значения не совпадают - проверяем права на подмену через group_access
                if public_value != system_value:
                    # Используем существующую логику проверки групп
                    access_result = self._check_group_access(allowed_groups, data.get('system', {}))
                    if access_result.get("result") != "success":
                        error_msg = access_result.get('error', {})
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get('message', '')
                        else:
                            error_msg = str(error_msg)
                        return {
                            "result": "error",
                            "error": {
                                "code": "PERMISSION_DENIED",
                                "message": f"Обнаружена попытка подмены поля {field} для {field}={system_value}. {error_msg}"
                            }
                        }
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки целостности данных: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }