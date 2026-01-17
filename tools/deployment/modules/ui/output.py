"""
Модуль для красивого вывода информации
Поддержка цветов и форматирования
"""

import sys
from typing import Optional


class Colors:
    """ANSI коды цветов для терминала"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Цвета текста
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Яркие цвета
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


class OutputFormatter:
    """Класс для форматированного вывода"""
    
    def __init__(self, use_colors: bool = True):
        """Инициализация форматтера"""
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """Добавляет цвет к тексту"""
        if self.use_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def print_header(self, text: str, width: int = 60):
        """Выводит заголовок"""
        print("\n" + "=" * width)
        print(self._colorize(text, Colors.BOLD + Colors.CYAN))
        print("=" * width)
    
    def print_section(self, text: str, width: int = 60):
        """Выводит секцию"""
        print("\n" + "-" * width)
        print(self._colorize(text, Colors.BOLD))
        print("-" * width)
    
    def print_success(self, text: str):
        """Выводит успешное сообщение"""
        print(self._colorize(f"✅ {text}", Colors.GREEN))
    
    def print_error(self, text: str):
        """Выводит сообщение об ошибке"""
        print(self._colorize(f"❌ {text}", Colors.RED), file=sys.stderr)
    
    def print_warning(self, text: str):
        """Выводит предупреждение"""
        print(self._colorize(f"⚠️ {text}", Colors.YELLOW))
    
    def print_info(self, text: str):
        """Выводит информационное сообщение"""
        print(self._colorize(f"ℹ️ {text}", Colors.CYAN))
    
    def print_step(self, step_num: int, total: int, text: str):
        """Выводит шаг процесса"""
        print(f"\n📋 Шаг {step_num}/{total}: {text}")
    
    def print_key_value(self, key: str, value: str, indent: int = 0):
        """Выводит пару ключ-значение"""
        prefix = " " * indent
        print(f"{prefix}{self._colorize(key, Colors.BOLD)}: {value}")
    
    def print_list(self, items: list, prefix: str = "  -", color: Optional[str] = None):
        """Выводит список элементов"""
        for item in items:
            if color:
                print(f"{prefix} {self._colorize(str(item), color)}")
            else:
                print(f"{prefix} {item}")
    
    def print_separator(self, width: int = 60):
        """Выводит разделитель"""
        print("=" * width)
    
    def print_table(self, headers: list, rows: list):
        """Выводит таблицу"""
        if not rows:
            return
        
        # Вычисляем ширину колонок
        col_widths = [len(str(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Выводим заголовки
        header_row = " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers))
        print(self._colorize(header_row, Colors.BOLD))
        print("-" * len(header_row))
        
        # Выводим строки
        for row in rows:
            row_str = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
            print(row_str)


# Глобальный экземпляр для удобного доступа
_formatter = None

def get_formatter() -> OutputFormatter:
    """Получает или создает форматтер"""
    global _formatter
    if _formatter is None:
        _formatter = OutputFormatter()
    return _formatter

