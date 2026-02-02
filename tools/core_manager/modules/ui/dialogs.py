"""Interactive dialogs for user input."""

from typing import Callable
from .colors import Colors
from ..i18n.translator import Translator


def confirm(message: str, translator: Translator, default: bool = True, input_func: Callable[[str], str] | None = None) -> bool:
    """Ask user for yes/no confirmation. Accepts only y/yes and n/no."""
    if input_func is None:
        input_func = input

    msg_yn = translator.get("dialogs.please_answer_yn")
    msg_invalid = translator.get("dialogs.invalid_input_try_again")

    print()
    if default:
        prompt = f"{message} {Colors.highlight('(Y/n)')}: "
    else:
        prompt = f"{message} {Colors.highlight('(y/N)')}: "

    while True:
        try:
            response = input_func(prompt).strip().lower()

            # Empty response uses default
            if not response:
                return default

            # Check response
            if response in ["y", "yes"]:
                return True
            if response in ["n", "no"]:
                return False
            print(Colors.error(f"✗ {msg_yn}"))

        except (KeyboardInterrupt, EOFError):
            print()
            return False
        except UnicodeDecodeError:
            print(Colors.error(f"✗ {msg_invalid}"))
