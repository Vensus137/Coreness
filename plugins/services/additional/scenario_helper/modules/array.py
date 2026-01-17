"""
Модуль для работы с массивами (модификация, проверка значений)
"""

from typing import Any, Dict


class ArrayManager:
    """
    Класс для работы с массивами
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def modify_array(self, data: dict) -> Dict[str, Any]:
        """
        Модификация массива: добавление, удаление элементов или очистка
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет данных для модификации"
                    }
                }
            
            array = data.get('array')
            operation = data.get('operation')
            value = data.get('value')
            skip_duplicates = data.get('skip_duplicates', True)  # По умолчанию пропускаем дубликаты
            
            # Валидация параметров
            if array is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр array обязателен"
                    }
                }
            
            if not isinstance(array, list):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр array должен быть массивом"
                    }
                }
            
            if operation is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр operation обязателен"
                    }
                }
            
            if operation not in ['add', 'remove', 'clear']:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр operation должен быть одним из: 'add', 'remove', 'clear'"
                    }
                }
            
            # Создаем копию массива для модификации
            modified_array = list(array)
            
            # Выполняем операцию
            if operation == 'add':
                if value is None:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Параметр value обязателен для операции 'add'"
                        }
                    }
                
                # Проверяем дубликаты, если нужно
                if skip_duplicates and value in modified_array:
                    # Элемент уже есть, возвращаем массив без изменений
                    pass
                else:
                    modified_array.append(value)
            
            elif operation == 'remove':
                if value is None:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Параметр value обязателен для операции 'remove'"
                        }
                    }
                
                # Проверяем, есть ли элемент в массиве
                if value not in modified_array:
                    # Элемент не найден
                    return {
                        "result": "not_found",
                        "response_data": {
                            "modified_array": modified_array  # Возвращаем исходный массив без изменений
                        }
                    }
                
                # Удаляем все вхождения значения
                modified_array = [item for item in modified_array if item != value]
            
            elif operation == 'clear':
                modified_array = []
            
            # Формируем результат
            result = {
                "result": "success",
                "response_data": {
                    "modified_array": modified_array
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка модификации массива: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def check_value_in_array(self, data: dict) -> Dict[str, Any]:
        """
        Проверка наличия значения в массиве
        Возвращает индекс первого вхождения значения в массиве
        result: "success" если найдено, "not_found" если не найдено
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет данных для проверки"
                    }
                }
            
            array = data.get('array')
            value = data.get('value')
            
            # Валидация параметров
            if array is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр array обязателен"
                    }
                }
            
            if not isinstance(array, list):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр array должен быть массивом"
                    }
                }
            
            if value is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр value обязателен"
                    }
                }
            
            # Проверяем наличие значения в массиве
            if value in array:
                # Находим индекс первого вхождения
                index = array.index(value)
                
                # Формируем результат - найдено
                return {
                    "result": "success",
                    "response_data": {
                        "response_index": index
                    }
                }
            else:
                # Значение не найдено
                return {
                    "result": "not_found"
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки значения в массиве: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
