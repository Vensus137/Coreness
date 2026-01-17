"""
Утилиты для тестов
"""
import os
from pathlib import Path


def find_project_root(start_path: Path = None) -> Path:
    """
    Надежно определяет корень проекта
    """
    # Сначала проверяем переменную окружения
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root and Path(env_root).exists():
        return Path(env_root)
    
    # Определяем стартовую точку
    if start_path is None:
        # Используем текущий файл как точку отсчета
        start_path = Path(__file__)
    
    # Ищем корень проекта по ключевым файлам/папкам
    current = start_path.resolve()
    
    # Если start_path - файл, начинаем с его директории
    if current.is_file():
        current = current.parent
    
    # Поднимаемся вверх, пока не найдем корень проекта
    while current != current.parent:
        # Проверяем наличие ключевых файлов проекта
        if (current / "main.py").exists() and \
           (current / "plugins").exists() and \
           (current / "app").exists():
            return current
        current = current.parent
    
    # Fallback - если не найден, возвращаем директорию на уровень выше от start_path
    # (для случая, когда start_path находится в tests/)
    if start_path.name == "tests" or "tests" in start_path.parts:
        # Если мы в tests/, поднимаемся на уровень выше
        return start_path.parent if start_path.is_dir() else start_path.parent.parent
    
    return start_path.parent if start_path.is_file() else start_path

