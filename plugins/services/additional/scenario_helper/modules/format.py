"""
Format Module - форматирование структурированных данных в текстовый формат
"""

import re
from typing import Any, Dict, List, Optional


class DataFormatter:
    """
    Класс для форматирования структурированных данных в текстовый формат
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def format_data_to_text(self, data: dict) -> Dict[str, Any]:
        """
        Форматирование структурированных данных в текстовый формат
        """
        try:
            format_type = data.get('format_type')
            input_data = data.get('input_data')
            title = data.get('title')
            item_template = data.get('item_template')
            
            if not format_type:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Тип форматирования (format_type) не указан. Доступны: list, structured"
                    }
                }
            
            if input_data is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Массив элементов для форматирования (input_data) не указан"
                    }
                }
            
            # Проверяем, что input_data - массив
            if not isinstance(input_data, list):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "input_data должен быть массивом"
                    }
                }
            
            # Выбираем форматтер
            if format_type == "list":
                if not item_template:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Для формата 'list' требуется шаблон элемента (item_template)"
                        }
                    }
                formatted_text = self._format_list(input_data, title, item_template)
            elif format_type == "structured":
                formatted_text = self._format_structured(input_data, title)
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Неизвестный тип форматирования: {format_type}. Доступны: list, structured"
                    }
                }
            
            # Формируем response_data
            response_data = {
                "formatted_text": formatted_text
            }
            
            return {
                "result": "success",
                "response_data": response_data
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка форматирования данных: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _format_list(self, items: List[Dict[str, Any]], title: Optional[str], item_template: str) -> str:
        """
        Форматирование простого списка элементов
        """
        lines = []
        
        # Добавляем заголовок, если указан
        if title:
            lines.append(title)
        
        # Форматируем каждый элемент
        for item in items:
            if not isinstance(item, dict):
                self.logger.warning(f"Пропущен элемент, не являющийся объектом: {item}")
                continue
            
            # Заменяем плейсхолдеры через $ на значения из item
            formatted_item = self._apply_template(item_template, item)
            lines.append(formatted_item)
        
        return "\n".join(lines)
    
    def _format_structured(self, items: List[Dict[str, Any]], title: Optional[str]) -> str:
        """
        Форматирование структурированного списка с заголовками, подзаголовками и вложенными блоками
        """
        lines = []
        
        # Добавляем общий заголовок, если указан
        if title:
            lines.append(title)
        
        # Форматируем каждый элемент
        for item in items:
            if not isinstance(item, dict):
                self.logger.warning(f"Пропущен элемент, не являющийся объектом: {item}")
                continue
            
            # Заголовок элемента: name - description (на одной строке)
            item_name = item.get('name') or item.get('id')
            description = item.get('description')
            
            if item_name and description:
                lines.append(f"{item_name} — {description}")
            elif item_name:
                lines.append(item_name)
            elif description:
                lines.append(description)
            
            # Блок параметров (если есть)
            parameters = item.get('parameters')
            if parameters and isinstance(parameters, dict):
                lines.append("  Параметры:")
                
                for param_name, param_info in parameters.items():
                    if isinstance(param_info, dict):
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('description', '')
                        param_default = param_info.get('default')
                        param_optional = param_info.get('optional', False)
                        
                        # Форматируем параметр: - param_name (type) (опционально) - описание. По умолчанию: default
                        param_line = f"  - {param_name} ({param_type})"
                        if param_optional:
                            param_line += " (опционально)"
                        if param_desc:
                            param_line += f" — {param_desc}"
                        if param_default is not None:
                            param_line += f". По умолчанию: {param_default}"
                        lines.append(param_line)
                    else:
                        # Простой параметр без деталей
                        lines.append(f"  - {param_name}")
            
            # Пустая строка между элементами
            lines.append("")
        
        # Убираем последнюю пустую строку
        if lines and lines[-1] == "":
            lines.pop()
        
        return "\n".join(lines)
    
    def _apply_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        Применяет шаблон с плейсхолдерами через $ к данным
        """
        result = template
        
        # Находим все плейсхолдеры через $ (например, $id, $description)
        # Поддерживаем простые ключи: $key
        pattern = r'\$(\w+)'
        
        def replace_placeholder(match):
            key = match.group(1)
            value = data.get(key, '')
            # Если значение - строка, возвращаем как есть, иначе преобразуем в строку
            return str(value) if value is not None else ''
        
        result = re.sub(pattern, replace_placeholder, result)
        
        return result
