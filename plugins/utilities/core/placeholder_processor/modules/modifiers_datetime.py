"""
Modifiers for working with dates and time
"""
from datetime import timedelta
from typing import Any, Union

from dateutil.relativedelta import relativedelta

from .datetime_parser import parse_datetime_value, parse_interval_string


class DatetimeModifiers:
    """Class with modifiers for working with dates"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_shift(self, value: Any, param: str) -> Union[str, Any]:
        """
        Date shift by specified interval (PostgreSQL style)
        
        Syntax: shift:+interval or shift:-interval
        
        Supported units (case-insensitive):
        - year, years, y
        - month, months, mon
        - week, weeks, w
        - day, days, d
        - hour, hours, h
        - minute, minutes, min, m
        - second, seconds, sec, s
        
        Examples:
        - {date|shift:+1 day}
        - {date|shift:-2 hours}
        - {date|shift:+1 year 2 months}
        - {date|shift:+1 week 3 days 6 hours}
        
        Supported input formats:
        - Unix timestamp: 1735128000
        - PostgreSQL: 2024-12-25, 2024-12-25 15:30:45
        - Standard: 25.12.2024, 25.12.2024 15:30, 25.12.2024 15:30:45
        - ISO: 2024-12-25T15:30:45
        - Python datetime objects
        
        Returns: String in ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        """
        if not value or not param:
            return value
        
        try:
            # 1. Check sign (+ or -)
            param_str = str(param).strip()
            if not param_str or param_str[0] not in ('+', '-'):
                self.logger.warning(f"shift modifier requires + or - sign at start: '{param}'")
                return value
            
            sign = 1 if param_str[0] == '+' else -1
            interval_str = param_str[1:].strip()
            
            if not interval_str:
                self.logger.warning(f"shift modifier: empty interval after sign")
                return value
            
            # 2. Parse interval
            interval = parse_interval_string(interval_str)
            
            # Check that at least something was parsed
            if all(v == 0 for v in interval.values()):
                self.logger.warning(f"shift modifier: failed to parse interval '{interval_str}'")
                return value
            
            # 3. Parse input date
            dt, has_time = parse_datetime_value(value)
            if dt is None:
                self.logger.warning(f"shift modifier: failed to parse date '{value}'")
                return value
            
            # 4. Apply shift
            # For months/years use relativedelta (correctly handles month boundaries)
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
                # For others use timedelta (faster)
                dt = dt + timedelta(
                    weeks=sign * interval['weeks'],
                    days=sign * interval['days'],
                    hours=sign * interval['hours'],
                    minutes=sign * interval['minutes'],
                    seconds=sign * interval['seconds']
                )
            
            # 5. Return in ISO format (without timezone and nanoseconds)
            if has_time:
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt.strftime('%Y-%m-%d')
        
        except Exception as e:
            self.logger.warning(f"Error in shift modifier: {e}")
            return value
    
    def modifier_seconds(self, value: Any, param: str) -> Union[int, None]:
        """
        Convert time strings to seconds: {field|seconds}
        
        Supported format: Xw Yd Zh Km Ms
        (w - weeks, d - days, h - hours, m - minutes, s - seconds)
        
        Examples:
        - "2h 30m" → 9000
        - "1d 2w" → 1296000
        - "30m" → 1800
        """
        if not value:
            return None
        
        # Convert value to string and parse
        time_string = str(value).strip()
        if not time_string:
            return None
        
        return self._parse_time_string(time_string)
    
    def _parse_time_string(self, time_string: str) -> Union[int, None]:
        """Universal parser for time strings to seconds (e.g., '1w 5d 4h 30m 15s')"""
        import re
        
        if not time_string:
            return None
        
        # Pattern for finding values with time units
        # Stricter pattern: only digits, spaces and time units
        pattern = r"(\d+)\s*(w|d|h|m|s)\b"
        
        # Check that string contains only valid characters
        if not re.match(r"^[\d\s\w]+$", time_string.strip()):
            return None
        
        total_seconds = 0
        found_any = False
        
        for value, unit in re.findall(pattern, time_string):
            found_any = True
            value = int(value)
            if unit == 'w':
                total_seconds += value * 604800  # weeks to seconds
            elif unit == 'd':
                total_seconds += value * 86400   # days to seconds
            elif unit == 'h':
                total_seconds += value * 3600     # hours to seconds
            elif unit == 'm':
                total_seconds += value * 60       # minutes to seconds
            elif unit == 's':
                total_seconds += value            # seconds
        
        # If nothing found or result is 0, return None
        return total_seconds if found_any and total_seconds > 0 else None
    
    def modifier_to_date(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of day (00:00:00): {field|to_date}
        
        Examples:
        - {datetime|to_date} - start of day
        - {datetime|to_date|format:datetime} - start of day with formatting
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS), where time is 00:00:00
        """
        return self._to_period_start(value, 'date')
    
    def modifier_to_hour(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of hour (minutes and seconds = 0): {field|to_hour}
        
        Examples:
        - {datetime|to_hour} - start of hour
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'hour')
    
    def modifier_to_minute(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of minute (seconds = 0): {field|to_minute}
        
        Examples:
        - {datetime|to_minute} - start of minute
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'minute')
    
    def modifier_to_second(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of second (microseconds = 0): {field|to_second}
        
        Examples:
        - {datetime|to_second} - start of second
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'second')
    
    def modifier_to_week(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of week (Monday 00:00:00): {field|to_week}
        
        Examples:
        - {datetime|to_week} - start of week (Monday)
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'week')
    
    def modifier_to_month(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of month (1st day, 00:00:00): {field|to_month}
        
        Examples:
        - {datetime|to_month} - start of month
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'month')
    
    def modifier_to_year(self, value: Any, param: str) -> Union[str, Any]:
        """
        Convert date to start of year (January 1, 00:00:00): {field|to_year}
        
        Examples:
        - {datetime|to_year} - start of year
        
        Returns: ISO format (YYYY-MM-DD HH:MM:SS)
        """
        return self._to_period_start(value, 'year')
    
    def _to_period_start(self, value: Any, period: str) -> Union[str, Any]:
        """
        Internal method for converting date to period start
        
        Periods:
        - 'date' - start of day (00:00:00)
        - 'hour' - start of hour (minutes and seconds = 0)
        - 'minute' - start of minute (seconds = 0)
        - 'second' - start of second (microseconds = 0)
        - 'week' - start of week (Monday 00:00:00)
        - 'month' - start of month (1st day, 00:00:00)
        - 'year' - start of year (January 1, 00:00:00)
        """
        if not value:
            return value
        
        try:
            # Parse input date
            dt, has_time = parse_datetime_value(value)
            if dt is None:
                self.logger.warning(f"to_{period} modifier: failed to parse date '{value}'")
                return value
            
            # Apply conversion depending on period
            if period == 'date':
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'hour':
                dt = dt.replace(minute=0, second=0, microsecond=0)
            elif period == 'minute':
                dt = dt.replace(second=0, microsecond=0)
            elif period == 'second':
                dt = dt.replace(microsecond=0)
            elif period == 'week':
                # Start of week (Monday)
                days_since_monday = dt.weekday()  # 0 = Monday, 6 = Sunday
                dt = dt - timedelta(days=days_since_monday)
                dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'month':
                dt = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif period == 'year':
                dt = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                self.logger.warning(f"to_{period} modifier: unknown period '{period}'")
                return value
            
            # Return in ISO format (without timezone and nanoseconds)
            # Always return with time, as this is conversion to period start
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        
        except Exception as e:
            self.logger.warning(f"Error in to_{period} modifier: {e}")
            return value
