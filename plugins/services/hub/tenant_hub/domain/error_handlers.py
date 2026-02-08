"""
Error handling decorators for tenant hub actions
Provides consistent error handling across all action methods
"""

from functools import wraps
from typing import Any, Callable, Dict


def handle_action_errors(error_code: str = "INTERNAL_ERROR"):
    """
    Decorator for handling errors in action methods.
    Catches exceptions and returns standardized error response.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs) -> Dict[str, Any]:
            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(f"Error in {func.__name__}: {e}")
                return {
                    "result": "error",
                    "error": {
                        "code": error_code,
                        "message": f"Internal error: {str(e)}"
                    }
                }
        return wrapper
    return decorator


def extract_error_message(error: Any) -> str:
    """
    Extract error message from error object.
    Handles both dict and string error formats.
    """
    if isinstance(error, dict):
        return error.get('message', 'Unknown error')
    return str(error) if error else 'Unknown error'
