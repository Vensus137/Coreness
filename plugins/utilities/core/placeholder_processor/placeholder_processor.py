import re
from typing import Any, Dict, List

from .modules.object_utils import deep_merge

# Импортируем утилиты из модулей
from .modules.path_parser import extract_literal_or_get_value, get_nested_value
from .modules.type_utils import determine_result_type


class PlaceholderProcessor:
    """
    Высокопроизводительный процессор плейсхолдеров с оптимизациями:
    - Предкомпиляция регулярных выражений
    - Быстрые строковые проверки
    - Кэширование результатов
    - Многоуровневая оптимизация
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("placeholder_processor")
        
        # Настройки
        self.enable_fast_check = settings.get('enable_fast_check', True)
        self.max_nesting_depth = settings.get('max_nesting_depth', 10)
        
        # Предкомпилированные регулярные выражения
        # Поддержка вложенности на один уровень: {...{...}...}
        # На базе этого делаем рекурсивную подстановку, что позволяет обрабатывать произвольную глубину
        self.placeholder_pattern = re.compile(r'\{((?:[^{}]|\{[^{}]*\})+)\}')
        self.modifier_pattern = re.compile(r'([^|:]+)(?::([^|]+))?')
        
        # Инициализация модификаторов
        self._init_modifiers()
    
    def _init_modifiers(self):
        """Инициализация всех доступных модификаторов"""
        # Импортируем все модули с модификаторами
        from .modules.modifiers_arithmetic import ArithmeticModifiers
        from .modules.modifiers_array import ArrayModifiers
        from .modules.modifiers_async import AsyncModifiers
        from .modules.modifiers_basic import BasicModifiers
        from .modules.modifiers_conditional import ConditionalModifiers
        from .modules.modifiers_datetime import DatetimeModifiers
        from .modules.modifiers_formatting import FormattingModifiers
        
        # Создаем экземпляры классов с модификаторами
        basic = BasicModifiers(self.logger)
        arithmetic = ArithmeticModifiers(self.logger)
        formatting = FormattingModifiers(self.logger)
        conditional = ConditionalModifiers(self.logger)
        datetime_mods = DatetimeModifiers(self.logger)
        array_mods = ArrayModifiers(self.logger)
        async_mods = AsyncModifiers(self.logger)
        
        self.modifiers = {
            # Fallback (остается в основном классе, так как использует _determine_result_type)
            'fallback': self._modifier_fallback,
            
            # Арифметические
            '/': arithmetic.modifier_divide,
            '+': arithmetic.modifier_add,
            '-': arithmetic.modifier_subtract,
            '*': arithmetic.modifier_multiply,
            '%': arithmetic.modifier_modulo,
            
            # Базовые строковые
            'upper': basic.modifier_upper,
            'lower': basic.modifier_lower,
            'title': basic.modifier_title,
            'capitalize': basic.modifier_capitalize,
            'truncate': basic.modifier_truncate,
            'length': basic.modifier_length,
            'case': basic.modifier_case,
            'regex': basic.modifier_regex,
            'code': basic.modifier_code,
            
            # Форматирование
            'format': formatting.modifier_format,
            'tags': formatting.modifier_tags,
            'list': formatting.modifier_list,
            'comma': formatting.modifier_comma,
            
            # Условные
            'equals': conditional.modifier_equals,
            'in_list': conditional.modifier_in_list,
            'true': conditional.modifier_true,
            'value': conditional.modifier_value,
            'exists': conditional.modifier_exists,
            'is_null': conditional.modifier_is_null,
            
            # Временные (даты и время)
            'shift': datetime_mods.modifier_shift,
            'seconds': datetime_mods.modifier_seconds,
            'to_date': datetime_mods.modifier_to_date,
            'to_hour': datetime_mods.modifier_to_hour,
            'to_minute': datetime_mods.modifier_to_minute,
            'to_second': datetime_mods.modifier_to_second,
            'to_week': datetime_mods.modifier_to_week,
            'to_month': datetime_mods.modifier_to_month,
            'to_year': datetime_mods.modifier_to_year,
            
            # Массивы
            'expand': array_mods.modifier_expand,
            'keys': array_mods.modifier_keys,
            
            # Async действия
            'not_ready': async_mods.modifier_not_ready,
            'ready': async_mods.modifier_ready,
        }
    
    def process_placeholders(self, data_with_placeholders: Dict, values_dict: Dict, max_depth: int = None) -> Dict:
        """
        Универсальный метод - обрабатывает плейсхолдеры в любом словаре,
        используя значения из values_dict с поддержкой вложенных плейсхолдеров
        """
        try:
            # Используем настройку из конфига, если max_depth не указан
            if max_depth is None:
                max_depth = self.max_nesting_depth
            
            # Один проход - вложенные плейсхолдеры обрабатываются рекурсивно
            result = self._process_object_optimized(data_with_placeholders, values_dict)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки плейсхолдеров: {e}")
            return data_with_placeholders
    
    def process_placeholders_full(self, data_with_placeholders: Dict, values_dict: Dict, max_depth: int = None) -> Dict:
        """
        Обрабатывает плейсхолдеры в словаре и возвращает ПОЛНЫЙ объект с обработанными плейсхолдерами.
        В отличие от process_placeholders, который возвращает только обработанные поля,
        этот метод возвращает весь исходный объект с замененными плейсхолдерами.
        """
        try:
            # Используем настройку из конфига, если max_depth не указан
            if max_depth is None:
                max_depth = self.max_nesting_depth
            
            # Обрабатываем плейсхолдеры рекурсивно
            # _process_object_optimized уже возвращает полный объект с объединенными вложенными структурами
            processed_data = self._process_object_optimized(data_with_placeholders, values_dict)
            
            # Рекурсивно объединяем исходные данные с обработанными
            return deep_merge(data_with_placeholders, processed_data)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки плейсхолдеров (полный режим): {e}")
            return data_with_placeholders
    

    def process_text_placeholders(self, text: str, values_dict: Dict, max_depth: int = None) -> str:
        """
        Универсальный метод для обработки плейсхолдеров в строке.
        Принимает строку и словарь значений, возвращает обработанную строку.
        """
        try:
            # Используем настройку из конфига, если max_depth не указан
            if max_depth is None:
                max_depth = self.max_nesting_depth
            
            # Проверяем, есть ли плейсхолдеры в тексте
            if not self._has_placeholders_fast(text):
                return text
            
            # Обрабатываем строку через оптимизированный метод
            result = self._process_string_optimized(text, values_dict, 0)
            
            # Убеждаемся, что результат - строка
            return str(result) if result is not None else text
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки плейсхолдеров в тексте: {e}")
            return text
    
    def _process_placeholder_chain(self, placeholder: str, values_dict: Dict, depth: int = 0):
        """Обрабатывает цепочку модификаторов с поддержкой вложенных плейсхолдеров"""
        # Контроль глубины рекурсии
        if depth >= self.max_nesting_depth:
            self.logger.warning(f"⚠️ Достигнута максимальная глубина рекурсии ({self.max_nesting_depth}) для плейсхолдера: {placeholder}")
            return f"{{{placeholder}}}"
        
        # Сначала вычисляем ВСЕ внутренние плейсхолдеры внутри текущего content (без внешних скобок)
        if self._has_placeholders_fast(placeholder):
            try:
                def _inner_repl(m):
                    inner_content = m.group(1).strip()
                    return str(self._process_placeholder_chain(inner_content, values_dict, depth + 1))
                placeholder = self.placeholder_pattern.sub(_inner_repl, placeholder)
            except Exception as e:
                # ОЖИДАЕМО: Если не удалось обработать вложенные плейсхолдеры (не найдено значение, ошибка преобразования и т.д.),
                # продолжаем выполнение с исходным плейсхолдером. Это нормальное поведение для случаев, когда значение отсутствует.
                self.logger.warning(f"Ошибка обработки вложенных плейсхолдеров: {e}")

        parts = placeholder.split('|')
        field_name = parts[0].strip()
        
        # Проверяем, является ли field_name литеральным значением в кавычках
        value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
        
        # Если значение - строка с плейсхолдерами, рекурсивно обрабатываем
        if isinstance(value, str) and self._has_placeholders_fast(value):
            value = self._process_string_optimized(value, values_dict, depth + 1)
        
        # Применяем модификаторы по порядку
        for modifier in parts[1:]:
            value = self._apply_modifier(value, modifier.strip())
        
        # Определяем тип результата универсально
        if value is not None:
            return determine_result_type(value)
        else:
            # ОЖИДАЕМО: Если значение не найдено, возвращаем плейсхолдер как строку для упрощения отладки
            # Это позволяет видеть, какие плейсхолдеры не были разрешены
            return f"{{{placeholder}}}"
    
    def _process_object_optimized(self, obj: Any, values_dict: Dict) -> Dict:
        """Оптимизированная обработка объекта (dict, list, str)"""
        if isinstance(obj, dict):
            return self._process_dict_optimized(obj, values_dict)
        elif isinstance(obj, list):
            return self._process_list_optimized(obj, values_dict)
        elif isinstance(obj, str):
            return self._process_string_optimized(obj, values_dict, 0)
        else:
            return {}
    
    def _process_dict_optimized(self, obj: Dict, values_dict: Dict) -> Dict:
        """Оптимизированная обработка словаря"""
        result = {}
        
        for key, value in obj.items():
            if isinstance(value, str):
                # Уровень 1: Быстрая проверка
                if self.enable_fast_check and not self._has_placeholders_fast(value):
                    continue
                
                # Уровень 2: Обработка строки
                processed_value = self._process_string_optimized(value, values_dict, 0)
                # Сравниваем с учетом возможного изменения типа
                # ОЖИДАЕМО: Если плейсхолдер не разрешился и остался строкой, он не добавляется в result.
                # Затем _deep_merge берет исходное значение из base, и плейсхолдер остается строкой.
                # Это ожидаемое поведение для упрощения отладки.
                if processed_value != value or type(processed_value) is not type(value):
                    result[key] = processed_value
            
            elif isinstance(value, dict):
                # Обрабатываем вложенный словарь рекурсивно
                processed_dict = self._process_dict_optimized(value, values_dict)
                # Объединяем оригинальный словарь с обработанными полями
                # Это гарантирует, что все поля будут в результате, даже если они не изменились
                merged_dict = {**value, **processed_dict}
                result[key] = merged_dict
            
            elif isinstance(value, list):
                processed_list = self._process_list_optimized(value, values_dict)
                if processed_list is not value:  # Добавляем только если есть изменения
                    result[key] = processed_list
        
            else:
                # Числовые значения (int, float), bool, None и другие типы
                # Добавляем как есть, так как они не содержат плейсхолдеров
                result[key] = value
        
        return result
    
    def _process_list_optimized(self, obj: List, values_dict: Dict) -> List:
        """Оптимизированная обработка списка"""
        result = []
        has_changes = False
        
        for item in obj:
            if isinstance(item, str):
                # Быстрая проверка
                if self.enable_fast_check and not self._has_placeholders_fast(item):
                    result.append(item)  # Добавляем элементы без плейсхолдеров как есть
                    continue
                
                # Проверяем, содержит ли плейсхолдер модификатор expand
                has_expand_modifier = '|expand' in item or item.endswith('|expand}')
                
                # Обработка строки
                processed_item = self._process_string_optimized(item, values_dict, 0)
                
                # Сравниваем с учетом возможного изменения типа
                if processed_item != item or type(processed_item) is not type(item):
                    has_changes = True
                    # Если использован модификатор expand и результат - массив массивов, разворачиваем его
                    if has_expand_modifier and isinstance(processed_item, list):
                        # Проверяем, является ли это массивом массивов
                        if processed_item and all(isinstance(subitem, list) for subitem in processed_item):
                            # Разворачиваем массив массивов на один уровень
                            result.extend(processed_item)
                        else:
                            # Обычный массив добавляем как есть
                            result.append(processed_item)
                    # Если результат - массив, и весь исходный элемент был одним плейсхолдером, разворачиваем его
                    elif isinstance(processed_item, list) and self._is_entire_placeholder(item):
                        # Разворачиваем массив на один уровень
                        result.extend(processed_item)
                    else:
                        result.append(processed_item)
                else:
                    result.append(item)
            
            elif isinstance(item, dict):
                processed_dict = self._process_dict_optimized(item, values_dict)
                # Объединяем оригинальный словарь с обработанными полями
                # Это гарантирует, что все поля будут в результате, даже если они не изменились
                merged_dict = {**item, **processed_dict}
                if merged_dict != item:  # Проверяем, были ли изменения
                    has_changes = True
                result.append(merged_dict)
            
            elif isinstance(item, list):
                processed_list = self._process_list_optimized(item, values_dict)
                if processed_list is not item:  # Добавляем только если есть изменения
                    has_changes = True
                    result.append(processed_list)
                else:
                    # Добавляем список даже если он не изменился (важно для статичных элементов)
                    result.append(item)
        
        # ОЖИДАЕМО: Если изменений нет, возвращаем исходный объект для оптимизации.
        # Логика has_changes корректно отслеживает все изменения (строки, словари, списки).
        return result if has_changes else obj
    
    def _process_string_optimized(self, text: str, values_dict: Dict, depth: int = 0):
        """Оптимизированная обработка строки с сохранением типов"""
        # Уровень 1: Быстрая проверка
        if self.enable_fast_check and not self._has_placeholders_fast(text):
            return text
        
        # Уровень 2: Простая замена (если нет модификаторов)
        if self._is_simple_replacement(text):
            return self._simple_replace(text, values_dict, depth)
        
        # Уровень 3: Сложная замена с модификаторами
        return self._complex_replace(text, values_dict, depth)
    
    def _has_placeholders_fast(self, text: str) -> bool:
        """Быстрая проверка наличия плейсхолдеров без regex"""
        return '{' in text and '}' in text
    
    def _is_simple_replacement(self, text: str) -> bool:
        """Проверяет, является ли замена простой (без модификаторов)"""
        # ОПТИМИЗАЦИЯ: Быстрая проверка наличия | перед полным парсингом
        if '|' not in text:
            return True
        
        # Если есть |, проверяем каждый плейсхолдер на наличие модификаторов
        matches = self.placeholder_pattern.findall(text)
        for match in matches:
            if '|' in match:
                return False
        return True
    
    def _simple_replace(self, text: str, values_dict: Dict, depth: int = 0):
        """Простая замена без модификаторов с сохранением типов"""
        def replace_simple(match):
            field_name = match.group(1).strip()
            # Внутри простого плейсхолдера тоже могут быть вложенные, их нужно сначала вычислить
            # Но нужно обрабатывать вложенные плейсхолдеры рекурсивно, заменяя их значениями,
            # чтобы получить финальный путь для поиска
            if self._has_placeholders_fast(field_name):
                # Обрабатываем вложенные плейсхолдеры, заменяя их значениями в строке
                def _inner_repl(m):
                    inner_content = m.group(1).strip()
                    inner_value = self._process_placeholder_chain(inner_content, values_dict, depth + 1)
                    # Если вернулся плейсхолдер (не обработался), возвращаем как есть
                    if isinstance(inner_value, str) and inner_value.startswith('{') and inner_value.endswith('}'):
                        return inner_value
                    return str(inner_value)
                field_name = self.placeholder_pattern.sub(_inner_repl, field_name)
            # Используем функцию для извлечения литералов или значений
            value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
            # В смешанном тексте всегда возвращаем строку
            result = str(determine_result_type(value)) if value is not None else match.group(0)
            return result
        
        # Проверяем, есть ли плейсхолдеры в тексте
        if not self.placeholder_pattern.search(text):
            return text
        
        # Если весь текст - это один плейсхолдер, возвращаем значение как есть
        if self._is_entire_placeholder(text):
            field_name = text[1:-1].strip()
            
            if self._has_placeholders_fast(field_name):
                # Если есть вложенные плейсхолдеры, обрабатываем через _process_placeholder_chain
                # который уже вернет финальное значение
                value = self._process_placeholder_chain(field_name, values_dict, depth)
                
                # Если _process_placeholder_chain вернул значение (не None и не исходный плейсхолдер)
                if value is not None:
                    # Проверяем, не вернул ли он исходный плейсхолдер в виде строки
                    value_str = str(value)
                    if not (value_str.startswith('{') and value_str.endswith('}') and field_name in value_str):
                        return determine_result_type(value)
                # ОЖИДАЕМО: Если вернул None или исходный плейсхолдер, возвращаем исходный текст (плейсхолдер как строку).
                # Это упрощает отладку, позволяя видеть, какие плейсхолдеры не были разрешены.
                return text
            # Если нет вложенных плейсхолдеров, используем функцию для извлечения литералов или значений
            value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
            
            # ОЖИДАЕМО: Если значение None, возвращаем исходный текст (плейсхолдер как строку) для отладки
            return determine_result_type(value) if value is not None else text
        
        # Если плейсхолдеры встроены в текст, возвращаем строку
        return self.placeholder_pattern.sub(replace_simple, text)
    
    def _complex_replace(self, text: str, values_dict: Dict, depth: int = 0):
        """Сложная замена с модификаторами. Для чистого плейсхолдера сохраняет тип результата."""
        def replace_complex(match):
            placeholder_content = match.group(1).strip()
            result = self._process_placeholder_chain(placeholder_content, values_dict, depth)
            # В смешанном тексте всегда возвращаем строку
            return str(result)
        
        # Итеративно разворачиваем плейсхолдеры, чтобы после подстановки внутренних
        # на следующем проходе корректно обработать внешние
        
        # Если весь текст - это один плейсхолдер с модификаторами, сохраняем тип результата
        if self._is_entire_placeholder(text):
            placeholder_content = text[1:-1].strip()
            result = self._process_placeholder_chain(placeholder_content, values_dict, depth)
            
            # Для чистого плейсхолдера сохраняем тип результата (не преобразуем в строку)
            if result is not None:
                # Проверяем, не вернул ли он исходный плейсхолдер в виде строки
                value_str = str(result)
                if not (value_str.startswith('{') and value_str.endswith('}') and placeholder_content in value_str):
                    return result
            # Если вернул None или исходный плейсхолдер, возвращаем исходный текст
            return text
        
        while True:
            if not self.placeholder_pattern.search(text):
                return text
            new_text = self.placeholder_pattern.sub(replace_complex, text)
            if new_text == text:
                return new_text
            text = new_text

    def _is_entire_placeholder(self, text: str) -> bool:
        """Проверяет, что вся строка — один плейсхолдер с балансом скобок."""
        if not text or text[0] != '{' or text[-1] != '}':
            return False
        depth = 0
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
                # первая открывающая должна быть на позиции 0
                if depth == 1 and i != 0:
                    return False
            elif ch == '}':
                depth -= 1
                if depth < 0:
                    return False
                # если наружная закрылась раньше конца строки — это не единственный плейсхолдер
                if depth == 0 and i != len(text) - 1:
                    return False
        return depth == 0
    
    def _apply_modifier(self, value: Any, modifier: str) -> Any:
        """Применяет один модификатор"""
        # Проверяем, является ли модификатор арифметическим (начинается с символа)
        if modifier and modifier[0] in ['/', '+', '-', '*', '%']:
            mod_name = modifier[0]
            mod_param = modifier[1:] if len(modifier) > 1 else None
        elif ':' in modifier:
            mod_name, mod_param = modifier.split(':', 1)
        else:
            mod_name, mod_param = modifier, None
        
        # Получаем функцию модификатора
        modifier_func = self.modifiers.get(mod_name)
        if modifier_func:
            try:
                return modifier_func(value, mod_param)
            except Exception as e:
                self.logger.warning(f"Ошибка применения модификатора {mod_name}: {e}")
                return value
        
        return value
    
    # === Модификаторы ===
    
    def _modifier_fallback(self, value: Any, param: str) -> Any:
        """Замена с дефолтом: {field|fallback:default}"""
        # ОЖИДАЕМО: Fallback срабатывает только для None и пустой строки.
        # False, 0, [], {} считаются валидными значениями и не триггерят fallback.
        if value is not None and value != "":
            return value
        
        # Используем универсальный метод определения типа
        if param is None:
            return None
        
        # ОЖИДАЕМО: Если param пустая строка после strip(), возвращается пустая строка "", а не None.
        # Это ожидаемое поведение для fallback: без значения.
        return determine_result_type(param.strip())
    