"""
Модификаторы для работы с датами и временем
"""
from datetime import timedelta
from typing import Any, Union

from dateutil.relativedelta import relativedelta

from .datetime_parser import parse_datetime_value, parse_interval_string


class DatetimeModifiers:
    """Класс с модификаторами для работы с датами"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_shift(self, value: Any, param: str) -> Union[str, Any]:
        """
        Сдвиг даты на заданный интервал (PostgreSQL style)
        
        Синтаксис: shift:+интервал или shift:-интервал
        
        Поддерживаемые единицы (case-insensitive):
        - year, years, y
        - month, months, mon
        - week, weeks, w
        - day, days, d
        - hour, hours, h
        - minute, minutes, min, m
        - second, seconds, sec, s
        
        Примеры:
        - {date|shift:+1 day}
        - {date|shift:-2 hours}
        - {date|shift:+1 year 2 months}
        - {date|shift:+1 week 3 days 6 hours}
        
        Поддерживаемые входные форматы:
        - Unix timestamp: 1735128000
        - PostgreSQL: 2024-12-25, 2024-12-25 15:30:45
        - Стандартные: 25.12.2024, 25.12.2024 15:30, 25.12.2024 15:30:45
        - ISO: 2024-12-25T15:30:45
        - datetime объекты Python
        
        Возвращает: Строка в ISO формате (YYYY-MM-DD или YYYY-MM-DD HH:MM:SS)
        """
        if not value or not param:
            return value
        
        try:
            # 1. Проверяем знак (+ или -)
            param_str = str(param).strip()
            if not param_str or param_str[0] not in ('+', '-'):
                self.logger.warning(f"shift модификатор требует знак + или - в начале: '{param}'")
                return value
            
            sign = 1 if param_str[0] == '+' else -1
            interval_str = param_str[1:].strip()
            
            if not interval_str:
                self.logger.warning(f"shift модификатор: пустой интервал после знака")
                return value
            
            # 2. Парсим интервал
            interval = parse_interval_string(interval_str)
            
            # Проверяем, что хоть что-то было распарсено
            if all(v == 0 for v in interval.values()):
                self.logger.warning(f"shift модификатор: не удалось распарсить интервал '{interval_str}'")
                return value
            
            # 3. Парсим входную дату
            dt, has_time = parse_datetime_value(value)
            if dt is None:
                self.logger.warning(f"shift модификатор: не удалось распарсить дату '{value}'")
                return value
            
            # 4. Применяем сдвиг
            # Для месяцев/годов используем relativedelta (корректно обрабатывает края месяцев)
            if interval['years'] or interval['months']:
                dt = dt + relativedelta(
                    years=sign * interval['years'],
                    months=sign * interval['months'],
                    weeks=sign * interval['weeks'],
                    days=sign * interval['days'],
                    hours=sign * interval['hours'],
                    minutes=sign * interval['minutes'],
                    seconds=sign * interval['seconds']
                )
            else:
                # Для остальных используем timedelta (быстрее)
                dt = dt + timedelta(
                    weeks=sign * interval['weeks'],
                    days=sign * interval['days'],
                    hours=sign * interval['hours'],
                    minutes=sign * interval['minutes'],
                    seconds=sign * interval['seconds']
                )
            
            # 5. Возвращаем в ISO формате (без timezone и наносекунд)
            if has_time:
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt.strftime('%Y-%m-%d')
        
        except Exception as e:
            self.logger.warning(f"Ошибка в shift модификаторе: {e}")
            return value
    
    def modifier_seconds(self, value: Any, param: str) -> Union[int, None]:
        """
        Преобразование временных строк в секунды: {field|seconds}
        
        Поддерживаемый формат: Xw Yd Zh Km Ms
        (w - недели, d - дни, h - часы, m - минуты, s - секунды)
        
        Примеры:
        - "2h 30m" → 9000
        - "1d 2w" → 1296000
        - "30m" → 1800
        """
        if not value:
            return None
        
        # Преобразуем значение в строку и парсим
        time_string = str(value).strip()
        if not time_string:
            return None
        
        return self._parse_time_string(time_string)
    
    def _parse_time_string(self, time_string: str) -> Union[int, None]:
        """Универсальный парсер временных строк в секунды (например, '1w 5d 4h 30m 15s')"""
        import re
        
        if not time_string:
            return None
        
        # Паттерн для поиска значений с единицами времени
        # Более строгий паттерн: только цифры, пробелы и единицы времени
        pattern = r"(\d+)\s*(w|d|h|m|s)\b"
        
        # Проверяем, что строка содержит только валидные символы
        if not re.match(r"^[\d\s\w]+$", time_string.strip()):
            return None
        
        total_seconds = 0
        found_any = False
        
        for value, unit in re.findall(pattern, time_string):
            found_any = True
            value = int(value)
            if unit == 'w':
                total_seconds += value * 604800  # недели в секунды
            elif unit == 'd':
                total_seconds += value * 86400   # дни в секунды
            elif unit == 'h':
                total_seconds += value * 3600     # часы в секунды
            elif unit == 'm':
                total_seconds += value * 60       # минуты в секунды
            elif unit == 's':
                total_seconds += value            # секунды
        
        # Если ничего не найдено или результат 0, возвращаем None
        return total_seconds if found_any and total_seconds > 0 else None
    
    def modifier_to_date(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу дня (00:00:00): {field|to_date}
        
        Примеры:
        - {datetime|to_date} - начало дня
        - {datetime|to_date|format:datetime} - начало дня с форматированием
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS), где время 00:00:00
        """
        return self._to_period_start(value, 'date')
    
    def modifier_to_hour(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу часа (минуты и секунды = 0): {field|to_hour}
        
        Примеры:
        - {datetime|to_hour} - начало часа
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'hour')
    
    def modifier_to_minute(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу минуты (секунды = 0): {field|to_minute}
        
        Примеры:
        - {datetime|to_minute} - начало минуты
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'minute')
    
    def modifier_to_second(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу секунды (микросекунды = 0): {field|to_second}
        
        Примеры:
        - {datetime|to_second} - начало секунды
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'second')
    
    def modifier_to_week(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу недели (понедельник 00:00:00): {field|to_week}
        
        Примеры:
        - {datetime|to_week} - начало недели (понедельник)
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'week')
    
    def modifier_to_month(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу месяца (1 число, 00:00:00): {field|to_month}
        
        Примеры:
        - {datetime|to_month} - начало месяца
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'month')
    
    def modifier_to_year(self, value: Any, param: str) -> Union[str, Any]:
        """
        Приведение даты к началу года (1 января, 00:00:00): {field|to_year}
        
        Примеры:
        - {datetime|to_year} - начало года
        
        Возвращает: ISO формат (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'year')
    
    def _to_period_start(self, value: Any, period: str) -> Union[str, Any]:
        """
        Внутренний метод для приведения даты к началу периода
        
        Периоды:
        - 'date' - начало дня (00:00:00)
        - 'hour' - начало часа (минуты и секунды = 0)
        - 'minute' - начало минуты (секунды = 0)
        - 'second' - начало секунды (микросекунды = 0)
        - 'week' - начало недели (понедельник 00:00:00)
        - 'month' - начало месяца (1 число, 00:00:00)
        - 'year' - начало года (1 января, 00:00:00)
        """
        if not value:
            return value
        
        try:
            # Парсим входную дату
            dt, has_time = parse_datetime_value(value)
            if dt is None:
                self.logger.warning(f"to_{period} модификатор: не удалось распарсить дату '{value}'")
                return value
            
            # Применяем приведение в зависимости от периода
            if period == 'date':
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'hour':
                dt = dt.replace(minute=0, second=0, microsecond=0)
            elif period == 'minute':
                dt = dt.replace(second=0, microsecond=0)
            elif period == 'second':
                dt = dt.replace(microsecond=0)
            elif period == 'week':
                # Начало недели (понедельник)
                days_since_monday = dt.weekday()  # 0 = понедельник, 6 = воскресенье
                dt = dt - timedelta(days=days_since_monday)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'month':
                dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'year':
                dt = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                self.logger.warning(f"to_{period} модификатор: неизвестный период '{period}'")
                return value
            
            # Возвращаем в ISO формате (без timezone и наносекунд)
            # Всегда возвращаем с временем, так как это приведения к началу периода
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        except Exception as e:
            self.logger.warning(f"Ошибка в to_{period} модификаторе: {e}")
            return value
