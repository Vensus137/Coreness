"""
UserStorageManager - подмодуль для работы с хранилищем данных пользователя
"""

import json
from typing import Any, Dict, List, Optional


class UserStorageManager:
    """
    Подмодуль для работы с хранилищем данных пользователя
    Управляет key-value данными пользователя (без групп, плоская структура)
    """
    
    def __init__(self, database_manager, logger, settings_manager):
        self.database_manager = database_manager
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Получаем лимит записей из настроек один раз при инициализации
        service_settings = self.settings_manager.get_plugin_settings('user_hub')
        self.storage_max_records = service_settings.get('storage_max_records', 100)
    
    async def get_storage(
        self, tenant_id: int, user_id: int, key: Optional[str] = None,
        key_pattern: Optional[str] = None, format_yaml: bool = False, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получение значений storage для пользователя
        Поддерживает получение всех значений, конкретного значения, а также поиск по паттернам
        """
        try:
            # Используем лимит из настроек, если не указан явно
            if limit is None:
                limit = self.storage_max_records
            
            # Используем универсальный метод получения
            master_repo = self.database_manager.get_master_repository()
            records = await master_repo.get_user_storage_records(
                tenant_id, user_id, key, key_pattern, limit
            )
            
            if not records:
                return {"result": "not_found"}
            
            # Определяем, что именно было запрошено для упрощения структуры ответа
            if key and not key_pattern:
                # Запрошен конкретный ключ (точное значение) - возвращаем только value
                first_record = records[0]
                user_storage_values = first_record.get('value')
            else:
                # Запрошен весь storage (ничего не указано) или паттерн для ключей
                # Возвращаем структуру {key: value, key2: value2}
                user_storage_values = {}
                for record in records:
                    k = record.get('key')
                    v = record.get('value')
                    # Проверяем наличие ключа (защита от некорректных данных)
                    if k is not None:
                        user_storage_values[k] = v
            
            # Базовый ответ со структурированными данными
            response_data = {
                "user_storage_values": user_storage_values
            }
            
            # Если запрошен форматированный вывод
            if format_yaml:
                import yaml
                # Для примитивов (строки, числа, bool) не используем YAML форматирование,
                # чтобы избежать добавления маркера конца документа (...)
                if isinstance(user_storage_values, (str, int, float, bool)) or user_storage_values is None:
                    formatted_text = str(user_storage_values) if user_storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        user_storage_values,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )
                    # Убираем лишние переносы строк в конце
                    formatted_text = formatted_text.rstrip()
                response_data["formatted_text"] = formatted_text
            
            return {
                "result": "success",
                "response_data": response_data
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения storage данных: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def set_storage(
        self, tenant_id: int, user_id: int, key: Optional[str] = None, value: Optional[Any] = None,
        values: Optional[Dict[str, Any]] = None, format_yaml: bool = False
    ) -> Dict[str, Any]:
        """
        Установка значений storage для пользователя
        Поддерживает смешанный подход с приоритетом: key -> value -> values
        - Если указан key: должен быть указан value (устанавливается одно значение)
        - Если указан values (без key): устанавливается полная структура {key: value}
        """
        try:
            # Определяем режим и формируем структуру для записи в БД
            # Приоритет: key -> value -> values
            if key:
                # Режим с key - должен быть указан value
                if value is not None:
                    # Режим: key + value - устанавливается одно значение
                    final_values = {key: value}
                    return_mode = "single_value"  # Вернуть только value
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "При указании key необходимо указать value"
                        }
                    }
            elif values:
                # Режим: полная структура values (без key)
                if not isinstance(values, dict):
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Параметр values должен быть объектом {key: value}"
                        }
                    }
                final_values = values
                return_mode = "structure"  # Вернуть {key: value}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Необходимо указать либо values (полная структура), либо key с value"
                    }
                }
            
            # Используем универсальный метод установки (batch для всех ключей)
            master_repo = self.database_manager.get_master_repository()
            success = await master_repo.set_user_storage_records(tenant_id, user_id, final_values)
            
            if not success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось установить значения"
                    }
                }
            
            # Определяем формат ответа аналогично get_storage на основе входных параметров
            if return_mode == "single_value":
                # Установлено одно значение (key + value) - возвращаем только value (как в get_storage для одного ключа)
                user_storage_values = final_values[key]
            else:
                # Установлена структура - возвращаем {key: value} (как в get_storage для нескольких ключей)
                user_storage_values = final_values
            
            # Базовый ответ со структурированными данными
            response_data = {
                "user_storage_values": user_storage_values
            }
            
            # Если запрошен форматированный вывод
            if format_yaml:
                import yaml
                # Для примитивов (строки, числа, bool) не используем YAML форматирование,
                # чтобы избежать добавления маркера конца документа (...)
                if isinstance(user_storage_values, (str, int, float, bool)) or user_storage_values is None:
                    formatted_text = str(user_storage_values) if user_storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        user_storage_values,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False
                    )
                    # Убираем лишние переносы строк в конце
                    formatted_text = formatted_text.rstrip()
                response_data["formatted_text"] = formatted_text
            
            return {
                "result": "success",
                "response_data": response_data
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка установки storage данных: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def delete_storage(
        self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Удаление значений из storage
        Если указан key или key_pattern - удаляется значение/значения, иначе удаляются все записи пользователя
        """
        try:
            # Используем универсальный метод удаления
            master_repo = self.database_manager.get_master_repository()
            deleted_count = await master_repo.delete_user_storage_records(
                tenant_id, user_id, key, key_pattern
            )
            
            if deleted_count > 0:
                return {"result": "success"}
            else:
                return {"result": "not_found"}
                
        except Exception as e:
            self.logger.error(f"Ошибка удаления storage данных: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _normalize_value(self, value: Any) -> str:
        """
        Нормализация значения для сравнения
        Для JSON значений: парсит и сериализует обратно с нормализацией
        Для простых значений: преобразует в строку
        """
        if value is None:
            return ""
        
        # Если значение уже строка, проверяем является ли оно JSON
        if isinstance(value, str):
            try:
                # Пытаемся распарсить как JSON
                parsed = json.loads(value)
                # Сериализуем обратно с нормализацией (sort_keys=True для dict)
                return json.dumps(parsed, sort_keys=True, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                # Не JSON, возвращаем как есть
                return str(value)
        
        # Если значение - dict или list, сериализуем в JSON с нормализацией
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, ensure_ascii=False)
        
        # Для простых типов (int, float, bool) преобразуем в строку
        return str(value)
    
    async def find_users_by_storage_value(self, tenant_id: int, key: str, value: Any) -> List[int]:
        """
        Поиск пользователей по ключу и значению в storage
        Использует индекс для быстрого поиска по tenant_id и key, затем фильтрует по value в памяти
        """
        try:
            # Получаем все записи по tenant_id и key (быстро через индекс)
            master_repo = self.database_manager.get_master_repository()
            records = await master_repo.get_user_storage_by_tenant_and_key(tenant_id, key)
            
            if not records:
                return []
            
            # Нормализуем искомое значение один раз
            normalized_target_value = self._normalize_value(value)
            
            # Фильтруем записи по значению в памяти
            matching_user_ids = []
            for record in records:
                record_value = record.get('value')
                # Нормализуем значение из БД для сравнения (JSON объекты могут иметь разный порядок ключей)
                normalized_record_value = self._normalize_value(record_value)
                
                if normalized_record_value == normalized_target_value:
                    user_id = record.get('user_id')
                    if user_id is not None:
                        matching_user_ids.append(user_id)
            
            # Убираем дубликаты (на случай если у пользователя несколько записей с одинаковым значением)
            return list(set(matching_user_ids))
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка поиска пользователей по storage key={key}, value={value}: {e}")
            return []
