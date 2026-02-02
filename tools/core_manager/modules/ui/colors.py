"""Color utilities for terminal output."""

import sys

if sys.platform == "win32":
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass


class Colors:
    """ANSI color codes for terminal output."""
    
    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Wrap text with color code."""
        return f"{color}{text}{Colors.RESET}"
    
    @staticmethod
    def bold(text: str) -> str:
        """Make text bold."""
        return f"{Colors.BOLD}{text}{Colors.RESET}"
    
    @staticmethod
    def success(text: str) -> str:
        """Green text for success messages."""
        return Colors.colorize(text, Colors.GREEN)
    
    @staticmethod
    def error(text: str) -> str:
        """Red text for error messages."""
        return Colors.colorize(text, Colors.RED)
    
    @staticmethod
    def warning(text: str) -> str:
        """Yellow text for warning messages."""
        return Colors.colorize(text, Colors.YELLOW)
    
    @staticmethod
    def info(text: str) -> str:
        """Cyan text for info messages."""
        return Colors.colorize(text, Colors.CYAN)
    
    @staticmethod
    def highlight(text: str) -> str:
        """Bright cyan text for highlighting."""
        return Colors.colorize(text, Colors.BRIGHT_CYAN)

    @staticmethod
    def unknown(text: str) -> str:
        """Yellow for unknown/N/A values."""
        return Colors.colorize(text, Colors.YELLOW)

    @staticmethod
    def version(text: str) -> str:
        """Green for known version."""
        return Colors.colorize(text, Colors.GREEN)

    @staticmethod
    def environment(text: str) -> str:
        """Cyan for environment."""
        return Colors.colorize(text, Colors.CYAN)

    @staticmethod
    def deployment(text: str) -> str:
        """Magenta for deployment mode."""
        return Colors.colorize(text, Colors.MAGENTA)
