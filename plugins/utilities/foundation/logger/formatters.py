import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

# ANSI escape codes for colors
COLORS = {
    'DEBUG': '\033[36m',    # Cyan
    'INFO': '\033[32m',     # Green
    'WARNING': '\033[33m',  # Yellow
    'ERROR': '\033[31m',    # Red
    'CRITICAL': '\033[35m', # Magenta
    'RESET': '\033[0m'      # Reset
}

# Цвета для тегов
TAG_COLORS = {
    'square': '\033[36m',   # Cyan - контекст [Bot-1], [Tenant-2]
    'round': '\033[33m',    # Yellow - статус (error), (warning)  
    'curly': '\033[32m',   # Green - данные {config}, {data}
    'http': '\033[35m',    # Magenta - HTTP коды (200, 404, 500)
    'RESET': '\033[0m'
}

class TimezoneFormatter(logging.Formatter):
    """Базовый форматтер с правильной таймзоной"""
    
    def __init__(self, fmt, datefmt=None, style='%', timezone='Europe/Moscow'):
        super().__init__(fmt, datefmt, style)
        try:
            self._timezone = ZoneInfo(timezone)
        except Exception:
            # Fallback на UTC если указана неверная таймзона
            self._timezone = ZoneInfo('UTC')
    
    def formatTime(self, record, datefmt=None):
        """Переопределяем formatTime для использования правильной таймзоны"""
        ct = datetime.fromtimestamp(record.created, tz=self._timezone)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            s = ct.strftime(self.default_time_format)
            if self.default_msec_format:
                s = self.default_msec_format % (s, record.msecs)
        return s


class ColoredFormatter(TimezoneFormatter):
    """Форматтер с поддержкой цветов для консоли"""
    
    def __init__(self, fmt, datefmt=None, style='%', use_colors=True, smart_format=False, timezone='Europe/Moscow'):
        super().__init__(fmt, datefmt, style, timezone=timezone)
        self.use_colors = use_colors
        self.smart_format = smart_format
        
        # Предкомпилируем regex паттерны для умного форматирования
        if self.smart_format:
            self._compile_regex_patterns()
    
    def _compile_regex_patterns(self):
        """Предкомпиляция regex паттернов для повышения производительности"""
        # Компилируем паттерны один раз при инициализации
        self._http_pattern = re.compile(r'(HTTP \d{3})')
        self._square_pattern = re.compile(r'(\[[^\]]+\])')
        self._round_pattern = re.compile(r'(\([^)]+\))')
        self._curly_pattern = re.compile(r'(\{[^}]+\})')
        
        # Создаем функции замены с предкомпилированными паттернами
        self._http_replacer = lambda m: f'{TAG_COLORS["http"]}{m.group(1)}{TAG_COLORS["RESET"]}'
        self._square_replacer = lambda m: f'{TAG_COLORS["square"]}{m.group(1)}{TAG_COLORS["RESET"]}'
        self._round_replacer = lambda m: f'{TAG_COLORS["round"]}{m.group(1)}{TAG_COLORS["RESET"]}'
        self._curly_replacer = lambda m: f'{TAG_COLORS["curly"]}{m.group(1)}{TAG_COLORS["RESET"]}'
    
    def format(self, record):
        # Создаем сообщение полностью с нуля
        if self._fmt:
            message = self._fmt % {
                'asctime': self.formatTime(record, self.datefmt),
                'levelname': record.levelname,
                'name': record.name,
                'message': record.getMessage()
            }
        else:
            message = record.getMessage()
        
        if not self.use_colors:
            return message
        
        # СНАЧАЛА применяем умное форматирование тегов (до окрашивания уровня)
        if self.smart_format:
            # Используем предкомпилированные паттерны для максимальной скорости
            if 'HTTP' in message:
                message = self._http_pattern.sub(self._http_replacer, message)
            
            if '[' in message:
                message = self._square_pattern.sub(self._square_replacer, message)
            if '(' in message:
                message = self._round_pattern.sub(self._round_replacer, message)
            if '{' in message:
                message = self._curly_pattern.sub(self._curly_replacer, message)

        # ПОТОМ применяем цвета для уровней логирования
        levelname = record.levelname
        if levelname in COLORS:
            # Заменяем только первое вхождение (которое добавляет logging)
            message = message.replace(levelname, f"{COLORS[levelname]}{levelname}{COLORS['RESET']}", 1)

        return message
