"""
Утилиты для работы с версиями
Унифицированные функции для парсинга, инкремента и обработки версий
"""

import re
from typing import Optional, Tuple


def parse_version(version: str) -> Tuple[str, Optional[str]]:
    """
    Парсит версию на основную часть и суффикс
    """
    if not version:
        return ("0.0.0", None)
    
    # Ищем первый дефис после цифр (начало суффикса)
    # Паттерн: основная часть заканчивается на цифру, затем идет дефис
    match = re.match(r'^(\d+(?:\.\d+)*)(.*)$', version)
    if match:
        base_version = match.group(1)
        suffix = match.group(2) if match.group(2) else None
        return (base_version, suffix)
    
    # Если не нашли паттерн, возвращаем как есть
    return (version, None)


def get_clean_version(version: str) -> str:
    """
    Получает чистую версию без суффикса для миграций
    """
    base_version, _ = parse_version(version)
    return base_version


def increment_version(version: str) -> str:
    """
    Инкрементирует версию с учетом суффикса
    
    Логика:
    - Если есть суффикс с числом (-beta-9) → инкрементируем число (-beta-10)
    - Если суффикс без числа (-beta) → добавляем -1 (-beta-1)
    - Если суффикса нет → добавляем -1 (0.14.0 → 0.14.0-1)
    """
    base_version, suffix = parse_version(version)
    
    if suffix:
        # Ищем число в конце суффикса
        # Паттерн: -beta-9, -alpha-1, -rc-5 и т.д.
        match = re.search(r'-(\d+)$', suffix)
        if match:
            # Есть число в конце - инкрементируем
            number = int(match.group(1))
            new_number = number + 1
            # Заменяем последнее число
            new_suffix = re.sub(r'-(\d+)$', f'-{new_number}', suffix)
            return f"{base_version}{new_suffix}"
        else:
            # Нет числа в конце - добавляем -1
            return f"{base_version}{suffix}-1"
    else:
        # Нет суффикса - добавляем -1
        return f"{base_version}-1"

