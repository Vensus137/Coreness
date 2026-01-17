"""
Улучшенный консольный логгер для утилит деплоя
С поддержкой цветов и умного форматирования (аналогично основному логгеру)
"""

import re
import sys
from datetime import datetime

# ANSI escape codes for colors
COLORS = {
    'DEBUG': '\033[36m',    # Cyan
    'INFO': '\033[32m',     # Green
    'WARNING': '\033[33m',  # Yellow
    'ERROR': '\033[31m',    # Red
    'CRITICAL': '\033[35m', # Magenta
    'RESET': '\033[0m'      # Reset
}

# Цвета для тегов (аналогично основному логгеру)
TAG_COLORS = {
    'square': '\033[36m',   # Cyan - контекст [Bot-1], [Tenant-2]
    'round': '\033[33m',    # Yellow - статус (error), (warning)  
    'curly': '\033[32m',    # Green - данные {config}, {data}
    'http': '\033[35m',     # Magenta - HTTP коды (200, 404, 500)
    'RESET': '\033[0m'
}


class ConsoleLogger:
    """Улучшенный логгер для вывода в консоль с цветами и умным форматированием"""
    
    def __init__(self, name: str = "deployment", use_colors: bool = True, smart_format: bool = True):
        self.name = name
        self.use_colors = use_colors and sys.stdout.isatty()  # Проверяем, что это терминал
        self.smart_format = smart_format
        
        # Предкомпилируем regex паттерны для умного форматирования
        if self.smart_format:
            self._compile_regex_patterns()
    
    def _compile_regex_patterns(self):
        """Предкомпиляция regex паттернов для повышения производительности"""
        self._http_pattern = re.compile(r'(HTTP \d{3})')
        self._square_pattern = re.compile(r'(\[[^\]]+\])')
        self._round_pattern = re.compile(r'(\([^)]+\))')
        self._curly_pattern = re.compile(r'(\{[^}]+\})')
        
        # Создаем функции замены с предкомпилированными паттернами
        self._http_replacer = lambda m: f'{TAG_COLORS["http"]}{m.group(1)}{TAG_COLORS["RESET"]}'
        self._square_replacer = lambda m: f'{TAG_COLORS["square"]}{m.group(1)}{TAG_COLORS["RESET"]}'
        self._round_replacer = lambda m: f'{TAG_COLORS["round"]}{m.group(1)}{TAG_COLORS["RESET"]}'
        self._curly_replacer = lambda m: f'{TAG_COLORS["curly"]}{m.group(1)}{TAG_COLORS["RESET"]}'
    
    def _apply_smart_formatting(self, message: str) -> str:
        """Применяет умное форматирование тегов в сообщении"""
        if not self.smart_format or not self.use_colors:
            return message
        
        # Применяем форматирование тегов
        if 'HTTP' in message:
            message = self._http_pattern.sub(self._http_replacer, message)
        
        if '[' in message:
            message = self._square_pattern.sub(self._square_replacer, message)
        if '(' in message:
            message = self._round_pattern.sub(self._round_replacer, message)
        if '{' in message:
            message = self._curly_pattern.sub(self._curly_replacer, message)
        
        return message
    
    def _format_message(self, level: str, message: str) -> str:
        """Форматирует сообщение для вывода"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Применяем умное форматирование тегов
        message = self._apply_smart_formatting(str(message))
        
        # Формируем базовое сообщение
        formatted = f"[{timestamp}] [{level}] [{self.name}] {message}"
        
        # Применяем цвет для уровня логирования
        if self.use_colors and level in COLORS:
            # Заменяем только первое вхождение уровня (которое в квадратных скобках)
            formatted = formatted.replace(f"[{level}]", f"{COLORS[level]}[{level}]{COLORS['RESET']}", 1)
        
        return formatted
    
    def debug(self, message: str):
        """Выводит отладочное сообщение"""
        print(self._format_message("DEBUG", message), file=sys.stderr)
    
    def info(self, message: str):
        """Выводит информационное сообщение"""
        print(self._format_message("INFO", message))
    
    def warning(self, message: str):
        """Выводит предупреждение"""
        print(self._format_message("WARNING", message))
    
    def error(self, message: str):
        """Выводит ошибку"""
        print(self._format_message("ERROR", message), file=sys.stderr)

