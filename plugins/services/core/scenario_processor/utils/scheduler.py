"""
Модуль для работы с расписанием сценариев (cron)
"""

from datetime import datetime
from typing import Optional

from croniter import croniter


class ScenarioScheduler:
    """
    Планировщик для scheduled сценариев
    - Парсинг cron выражений
    - Проверка времени запуска
    - Расчет следующего времени запуска
    """
    
    def __init__(self, logger, datetime_formatter):
        self.logger = logger
        self.datetime_formatter = datetime_formatter
    
    def is_valid_cron(self, cron_string: str) -> bool:
        """
        Проверка валидности cron выражения
        """
        if not cron_string or not isinstance(cron_string, str):
            return False
        
        try:
            croniter(cron_string)
            return True
        except Exception:
            return False
    
    async def get_next_run_time(self, cron_string: str, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Получение следующего времени запуска по cron выражению
        """
        if not self.is_valid_cron(cron_string):
            return None
        
        try:
            # Если время не указано - используем текущее локальное время
            if from_time is None:
                from_time = await self.datetime_formatter.now_local()
            
            # Создаем croniter от указанного времени
            cron = croniter(cron_string, from_time)
            next_run = cron.get_next(datetime)
            
            return next_run
            
        except Exception as e:
            self.logger.error(f"Ошибка расчета следующего времени запуска для cron '{cron_string}': {e}")
            return None

