"""
StorageManager - подмодуль для работы с хранилищем атрибутов тенанта
"""

from typing import Any, Dict, Optional


class StorageManager:
    """
    Подмодуль для работы с хранилищем атрибутов тенанта
    Управляет key-value данными тенанта (settings, limits, features, etc.)
    """
    
    def __init__(self, database_manager, logger, tenant_parser, settings_manager):
        self.database_manager = database_manager
        self.logger = logger
        self.tenant_parser = tenant_parser
        self.settings_manager = settings_manager
        
        # Получаем лимиты из настроек один раз при инициализации
        service_settings = self.settings_manager.get_plugin_settings('tenant_hub')
        self.storage_max_records = service_settings.get('storage_max_records', 100)
        self.storage_groups_max_limit = service_settings.get('storage_groups_max_limit', 200)
    
    async def get_storage(
        self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None,
        key: Optional[str] = None, key_pattern: Optional[str] = None, format_yaml: bool = False, 
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Получение значений storage для тенанта
        Поддерживает получение всех значений, группы, конкретного значения, а также поиск по паттернам
        """
        try:
            # Проверка: key может быть указан только вместе с group_key или group_key_pattern
            if (key or key_pattern) and not (group_key or group_key_pattern):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "key может быть указан только вместе с group_key или group_key_pattern"
                    }
                }
            
            # Используем лимит из настроек, если не указан явно
            if limit is None:
                limit = self.storage_max_records
            
            # Используем универсальный метод получения
            master_repo = self.database_manager.get_master_repository()
            records = await master_repo.get_storage_records(
                tenant_id, group_key, group_key_pattern, key, key_pattern, limit
            )
            
            if not records:
                return {"result": "not_found"}
            
            # Определяем, что именно было запрошено для упрощения структуры ответа
            has_group = group_key or group_key_pattern
            has_key = key or key_pattern
            is_exact_key = key and not key_pattern
            is_exact_group = group_key and not group_key_pattern
            
            if has_group and has_key and is_exact_key and is_exact_group:
                # Запрошено конкретное значение (точный group_key + точный key)
                # Возвращаем только value
                first_record = records[0]
                storage_values = first_record.get('value')
            elif has_group and is_exact_group:
                # Запрошена точная группа (group_key без паттерна, с key_pattern или без key)
                # Возвращаем структуру группы {key: value, key2: value2}
                storage_values = {}
                for record in records:
                    k = record.get('key')
                    v = record.get('value')
                    # Проверяем наличие ключа (защита от некорректных данных)
                    if k is not None:
                        storage_values[k] = v
            elif has_group:
                # Запрошена группа по паттерну (group_key_pattern)
                # Может быть несколько групп, возвращаем структуру {group_key: {key: value}}
                storage_values = {}
                for record in records:
                    gk = record.get('group_key')
                    k = record.get('key')
                    v = record.get('value')
                    # Проверяем наличие обязательных полей (защита от некорректных данных)
                    if gk is not None and k is not None:
                        if gk not in storage_values:
                            storage_values[gk] = {}
                        storage_values[gk][k] = v
            else:
                # Запрошен весь storage (ничего не указано)
                # Возвращаем полную структуру {group_key: {key: value}}
                storage_values = {}
                for record in records:
                    gk = record.get('group_key')
                    k = record.get('key')
                    v = record.get('value')
                    # Проверяем наличие обязательных полей (защита от некорректных данных)
                    if gk is not None and k is not None:
                        if gk not in storage_values:
                            storage_values[gk] = {}
                        storage_values[gk][k] = v
            
            # Базовый ответ со структурированными данными
            response_data = {
                "storage_values": storage_values
            }
            
            # Если запрошен форматированный вывод
            if format_yaml:
                import yaml
                # Для примитивов (строки, числа, bool) не используем YAML форматирование,
                # чтобы избежать добавления маркера конца документа (...)
                if isinstance(storage_values, (str, int, float, bool)) or storage_values is None:
                    formatted_text = str(storage_values) if storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        storage_values,
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
        self, tenant_id: int, group_key: Optional[str] = None, key: Optional[str] = None,
        value: Optional[Any] = None, values: Optional[Dict[str, Any]] = None, format_yaml: bool = False
    ) -> Dict[str, Any]:
        """
        Установка значений storage для тенанта
        Поддерживает смешанный подход с приоритетом: group_key -> key -> value -> values
        - Если указан group_key:
          - Если указан key:
            - Если указан value: устанавливается одно значение
            - Если указан values: устанавливается структура для группы
            - Иначе: ошибка
          - Если указан values (без key): устанавливается структура для группы
          - Иначе: ошибка
        - Если указан values (без group_key): устанавливается полная структура
        """
        try:
            # Определяем режим и формируем структуру для записи в БД
            # Приоритет: group_key -> key -> value -> values
            if group_key:
                # Режим с group_key
                if key:
                    # Режим: group_key + key
                    if value is not None:
                        # Режим: group_key + key + value - устанавливается одно значение
                        final_values = {group_key: {key: value}}
                        return_mode = "single_value"  # Вернуть только value
                    elif values:
                        # Режим: group_key + key + values - устанавливается структура для группы
                        if not isinstance(values, dict):
                            return {
                                "result": "error",
                                "error": {
                                    "code": "VALIDATION_ERROR",
                                    "message": "Параметр values должен быть объектом {key: value}"
                                }
                            }
                        final_values = {group_key: values}
                        return_mode = "group"  # Вернуть {key: value}
                    else:
                        return {
                            "result": "error",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "При указании group_key и key необходимо указать value или values"
                            }
                        }
                elif values:
                    # Режим: group_key + values (без key) - устанавливается структура для группы
                    if not isinstance(values, dict):
                        return {
                            "result": "error",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Параметр values должен быть объектом {key: value}"
                            }
                        }
                    final_values = {group_key: values}
                    return_mode = "group"  # Вернуть {key: value}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "При указании group_key необходимо указать key+value или values"
                        }
                    }
            elif values:
                # Режим: полная структура values (без group_key)
                if not isinstance(values, dict):
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Параметр values должен быть объектом {group_key: {key: value}}"
                        }
                    }
                # Проверяем структуру: все значения должны быть словарями
                for gk, group_data in values.items():
                    if not isinstance(group_data, dict):
                        return {
                            "result": "error",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": f"Некорректная структура: группа '{gk}' должна быть объектом с ключами, но получен тип {type(group_data).__name__}"
                            }
                        }
                final_values = values
                return_mode = "full"  # Вернуть {group_key: {key: value}}
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Необходимо указать либо values (полная структура), либо group_key с key+value или values"
                    }
                }
            
            # Используем универсальный метод установки (batch для всех групп)
            master_repo = self.database_manager.get_master_repository()
            success = await master_repo.set_storage_records(tenant_id, final_values)
            
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
                # Установлено одно значение (group_key + key + value) - возвращаем только value (как в get_storage для точного group_key + точного key)
                storage_values = final_values[group_key][key]
            elif return_mode == "group":
                # Установлена группа (group_key + values) - возвращаем {key: value} (как в get_storage для точного group_key)
                storage_values = final_values[group_key]
            else:
                # Установлена полная структура (values) - возвращаем {group_key: {key: value}} (как в get_storage для всего storage)
                storage_values = final_values
            
            # Базовый ответ со структурированными данными
            response_data = {
                "storage_values": storage_values
            }
            
            # Если запрошен форматированный вывод
            if format_yaml:
                import yaml
                # Для примитивов (строки, числа, bool) не используем YAML форматирование,
                # чтобы избежать добавления маркера конца документа (...)
                if isinstance(storage_values, (str, int, float, bool)) or storage_values is None:
                    formatted_text = str(storage_values) if storage_values is not None else "null"
                else:
                    formatted_text = yaml.dump(
                        storage_values,
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
        self, tenant_id: int, group_key: Optional[str] = None, group_key_pattern: Optional[str] = None, 
        key: Optional[str] = None, key_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Удаление значений или групп из storage
        Если указан key или key_pattern - удаляется значение, иначе удаляется группа
        """
        try:
            # Проверка: должен быть указан хотя бы один параметр для группы
            if not (group_key or group_key_pattern):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Необходимо указать group_key или group_key_pattern"
                    }
                }
            
            # Используем универсальный метод удаления
            master_repo = self.database_manager.get_master_repository()
            deleted_count = await master_repo.delete_storage_records(
                tenant_id, group_key, group_key_pattern, key, key_pattern
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
    
    async def get_storage_groups(self, tenant_id: int) -> Dict[str, Any]:
        """
        Получение списка уникальных ключей групп для тенанта
        Возвращает только список group_key без значений (с ограничением на количество групп)
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            # Запрашиваем limit + 1, чтобы определить, есть ли еще группы
            group_keys = await master_repo.get_storage_group_keys(tenant_id, limit=self.storage_groups_max_limit + 1)
            
            if group_keys is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Ошибка получения списка групп"
                    }
                }
            
            # Проверяем, был ли список обрезан
            is_truncated = len(group_keys) > self.storage_groups_max_limit
            
            # Если обрезан, берем только первые limit групп
            if is_truncated:
                group_keys = group_keys[:self.storage_groups_max_limit]
            
            response_data = {
                "group_keys": group_keys
            }
            
            # Добавляем информацию о том, что список обрезан
            if is_truncated:
                response_data["is_truncated"] = True
            
            return {
                "result": "success",
                "response_data": response_data
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка получения списка групп storage: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def sync_storage(self, tenant_id: int, storage_data: Dict[str, Dict[str, str]]) -> bool:
        """
        Синхронизация атрибутов из конфига
        Оптимизированная синхронизация: удаляем только группы из конфига одним batch запросом,
        затем загружаем все данные из конфига. Не требует получения всех групп из БД.
        
        storage_data: словарь {group_key: {key: value}}
        """
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Получаем список групп из конфига (только те, что нужно синхронизировать)
            groups_to_sync = list(storage_data.keys())
            
            # Удаляем группы из конфига одним batch запросом (оптимизация)
            # Удаляем только те группы, которые есть в конфиге - не трогаем остальные
            if groups_to_sync:
                deleted_count = await master_repo.delete_groups_batch(tenant_id, groups_to_sync)
                if deleted_count is None:
                    self.logger.warning(f"[Tenant-{tenant_id}] Ошибка удаления групп для синхронизации")
                elif deleted_count > 0:
                    self.logger.info(f"[Tenant-{tenant_id}] Удалено {deleted_count} записей из {len(groups_to_sync)} групп")
            
            # Загружаем новые данные из конфига (batch для всех групп сразу)
            if storage_data:
                success = await master_repo.set_storage_records(tenant_id, storage_data)
                if not success:
                    self.logger.warning(f"[Tenant-{tenant_id}] Не удалось синхронизировать storage")
                    return False
            
            self.logger.info(f"[Tenant-{tenant_id}] Синхронизация storage завершена (обработано {len(storage_data)} групп)")
            return True
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка синхронизации storage: {e}")
            return False
