"""Simple formatter and logger for database migration (no external dependencies)."""

from ...ui.colors import Colors


class MigrationFormatter:
    """Simple formatter for migration output."""

    def print_info(self, msg: str) -> None:
        print(Colors.info(msg))

    def print_success(self, msg: str) -> None:
        print(Colors.success(msg))

    def print_error(self, msg: str) -> None:
        print(Colors.error(msg))

    def print_warning(self, msg: str) -> None:
        print(Colors.warning(msg))

    def print_section(self, msg: str) -> None:
        print(f"\n{Colors.bold('=' * 60)}")
        print(Colors.bold(msg))
        print(Colors.bold('=' * 60) + "\n")


class MigrationLogger:
    """Simple logger for migration (outputs to stdout)."""

    def info(self, msg: str) -> None:
        print(Colors.info(msg))

    def warning(self, msg: str) -> None:
        print(Colors.warning(msg))

    def error(self, msg: str) -> None:
        print(Colors.error(msg))
