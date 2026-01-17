"""
Модуль для генерации случайных чисел и выбора элементов
"""

import random
from typing import Any, Dict


class RandomManager:
    """
    Класс для генерации случайных чисел и выбора элементов
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def generate_int(self, data: dict) -> Dict[str, Any]:
        """
        Генерация случайного целого числа в заданном диапазоне
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет данных для генерации"
                    }
                }
            
            min_val = data.get('min')
            max_val = data.get('max')
            seed = data.get('seed')
            
            # Валидация параметров
            if min_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр min обязателен"
                    }
                }
            
            if max_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр max обязателен"
                    }
                }
            
            if not isinstance(min_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр min должен быть целым числом"
                    }
                }
            
            if not isinstance(max_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр max должен быть целым числом"
                    }
                }
            
            if min_val > max_val:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min не может быть больше max"
                    }
                }
            
            # Создаем генератор с seed или без
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            
            # Генерируем случайное число
            value = rng.randint(min_val, max_val)
            
            # Формируем результат
            result = {
                "result": "success",
                "response_data": {
                    "random_value": value
                }
            }
            
            # Добавляем seed в ответ, если он был передан (конвертируем в строку для консистентности)
            if seed is not None:
                result["response_data"]["random_seed"] = str(seed)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации случайного числа: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def generate_array(self, data: dict) -> Dict[str, Any]:
        """
        Генерация массива случайных чисел в заданном диапазоне
        По умолчанию без повторений, можно разрешить повторения через allow_duplicates=True
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет данных для генерации"
                    }
                }
            
            min_val = data.get('min')
            max_val = data.get('max')
            count = data.get('count')
            seed = data.get('seed')
            allow_duplicates = data.get('allow_duplicates', False)  # По умолчанию без повторений
            
            # Валидация параметров
            if min_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр min обязателен"
                    }
                }
            
            if max_val is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр max обязателен"
                    }
                }
            
            if count is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр count обязателен"
                    }
                }
            
            if not isinstance(min_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр min должен быть целым числом"
                    }
                }
            
            if not isinstance(max_val, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр max должен быть целым числом"
                    }
                }
            
            if not isinstance(count, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр count должен быть целым числом"
                    }
                }
            
            if min_val > max_val:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "min не может быть больше max"
                    }
                }
            
            if count < 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр count не может быть отрицательным"
                    }
                }
            
            if count == 0:
                return {
                    "result": "success",
                    "response_data": {
                        "random_list": []
                    }
                }
            
            # Проверяем возможность генерации без повторений
            range_size = max_val - min_val + 1
            if not allow_duplicates and count > range_size:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Невозможно сгенерировать {count} уникальных чисел в диапазоне [{min_val}, {max_val}] (доступно только {range_size} уникальных значений). Используйте allow_duplicates=True для разрешения повторений"
                    }
                }
            
            # Создаем генератор с seed или без
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            
            # Генерируем массив случайных чисел
            if allow_duplicates:
                # С повторениями - обычная генерация
                values = [rng.randint(min_val, max_val) for _ in range(count)]
            else:
                # Без повторений - используем sample для гарантии уникальности
                all_possible_values = list(range(min_val, max_val + 1))
                values = rng.sample(all_possible_values, count)
            
            # Формируем результат
            result = {
                "result": "success",
                "response_data": {
                    "random_list": values
                }
            }
            
            # Добавляем seed в ответ, если он был передан (конвертируем в строку для консистентности)
            if seed is not None:
                result["response_data"]["random_seed"] = str(seed)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации массива случайных чисел: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def choose_from_array(self, data: dict) -> Dict[str, Any]:
        """
        Выбор случайных элементов из массива без повторений
        Возвращает выбранные элементы и их порядковые номера (индексы) в исходном массиве
        """
        try:
            if not data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет данных для выбора"
                    }
                }
            
            array = data.get('array')
            count = data.get('count')
            seed = data.get('seed')
            
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
            
            if count is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр count обязателен"
                    }
                }
            
            if not isinstance(count, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр count должен быть целым числом"
                    }
                }
            
            if count < 0:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Параметр count не может быть отрицательным"
                    }
                }
            
            # Проверяем, достаточно ли элементов в массиве
            if count > len(array):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Недостаточно элементов в массиве: запрошено {count}, доступно {len(array)}"
                    }
                }
            
            # Если запрошено 0 элементов, возвращаем пустой массив
            if count == 0:
                return {
                    "result": "success",
                    "response_data": {
                        "random_list": []
                    }
                }
            
            # Создаем генератор с seed или без
            if seed is not None:
                rng = random.Random(seed)
            else:
                rng = random.Random()
            
            # Выбираем случайные элементы без повторений
            # Используем sample для гарантии отсутствия повторений
            selected_values = rng.sample(array, count)
            
            # Формируем результат
            result = {
                "result": "success",
                "response_data": {
                    "random_list": selected_values
                }
            }
            
            # Добавляем seed в ответ, если он был передан (конвертируем в строку для консистентности)
            if seed is not None:
                result["response_data"]["random_seed"] = str(seed)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка выбора элементов из массива: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
