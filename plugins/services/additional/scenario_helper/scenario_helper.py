"""
Scenario Helper Service - вспомогательные утилиты для управления выполнением сценариев
(генерация случайных чисел, задержки, модификация массивов)
"""

from typing import Any, Dict

from .modules.array import ArrayManager
from .modules.cache import CacheManager
from .modules.format import DataFormatter
from .modules.random import RandomManager
from .modules.sleep import SleepManager


class ScenarioHelperService:
    """
    Вспомогательные утилиты для управления выполнением сценариев:
    - Генерация случайных чисел с поддержкой seed
    - Задержки выполнения (sleep)
    - Модификация массивов (добавление, удаление, очистка)
    - Проверка значений в массивах
    - Установка временных данных в кэш сценария
    - Форматирование структурированных данных в текстовый формат
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('scenario_helper')
        
        # Регистрируем себя в ActionHub
        self.action_hub.register('scenario_helper', self)
        
        # Получаем утилиту id_generator через DI
        self.id_generator = kwargs['id_generator']
        
        # Создаем менеджеры
        self.data_formatter = DataFormatter(self.logger)
        self.sleep_manager = SleepManager(self.logger)
        self.random_manager = RandomManager(self.logger)
        self.array_manager = ArrayManager(self.logger)
        self.cache_manager = CacheManager(self.logger)
    
    # === Actions для ActionHub ===
    
    async def sleep(self, data: dict) -> Dict[str, Any]:
        """Задержка выполнения на указанное количество секунд"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.sleep_manager.sleep(data)
        except Exception as e:
            self.logger.error(f"Ошибка задержки: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def generate_int(self, data: dict) -> Dict[str, Any]:
        """Генерация случайного целого числа в заданном диапазоне"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.random_manager.generate_int(data)
        except Exception as e:
            self.logger.error(f"Ошибка генерации числа: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def generate_array(self, data: dict) -> Dict[str, Any]:
        """Генерация массива случайных чисел в заданном диапазоне"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.random_manager.generate_array(data)
        except Exception as e:
            self.logger.error(f"Ошибка генерации массива: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def choose_from_array(self, data: dict) -> Dict[str, Any]:
        """Выбор случайных элементов из массива без повторений"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.random_manager.choose_from_array(data)
        except Exception as e:
            self.logger.error(f"Ошибка выбора из массива: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def modify_array(self, data: dict) -> Dict[str, Any]:
        """Модификация массива: добавление, удаление элементов или очистка"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.array_manager.modify_array(data)
        except Exception as e:
            self.logger.error(f"Ошибка модификации массива: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def check_value_in_array(self, data: dict) -> Dict[str, Any]:
        """Проверка наличия значения в массиве"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.array_manager.check_value_in_array(data)
        except Exception as e:
            self.logger.error(f"Ошибка проверки значения в массиве: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def generate_unique_id(self, data: dict) -> Dict[str, Any]:
        """Генерация уникального ID через автоинкремент в БД (детерминированная генерация)"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            seed = data.get('seed')
            
            # Получаем или создаем уникальный ID
            unique_id = await self.id_generator.get_or_create_unique_id(seed=seed)
            
            if unique_id is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось сгенерировать уникальный ID"
                    }
                }
            
            return {
                "result": "success",
                "response_data": {
                    "unique_id": unique_id
                }
            }
        except Exception as e:
            self.logger.error(f"Ошибка генерации уникального ID: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def set_cache(self, data: dict) -> Dict[str, Any]:
        """Установка временных данных в кэш сценария"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.cache_manager.set_cache(data)
        except Exception as e:
            self.logger.error(f"Ошибка установки кэша: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def format_data_to_text(self, data: dict) -> Dict[str, Any]:
        """Форматирование структурированных данных в текстовый формат"""
        try:
            # Валидация выполняется централизованно в ActionRegistry
            return await self.data_formatter.format_data_to_text(data)
        except Exception as e:
            self.logger.error(f"Ошибка форматирования данных: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }

