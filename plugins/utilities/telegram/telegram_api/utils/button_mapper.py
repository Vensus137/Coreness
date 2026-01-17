"""
Подмодуль для обработки кнопок
"""


class ButtonMapper:
    """
    Подмодуль для обработки кнопок Telegram
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
        # Максимальная длина callback_data для Telegram
        self.callback_data_limit = 60
    
    def _normalize_button_text(self, text: str) -> str:
        """Нормализация текста кнопки в callback_data"""
        try:
            # Ленивые импорты библиотек
            import re

            import emoji
            from unidecode import unidecode
            
            # Удаляем emoji
            text = emoji.replace_emoji(text, replace='')
            
            # Приводим к нижнему регистру и убираем пробелы
            text = text.lower().strip()
            
            # Транслитерация
            text = unidecode(text)
            
            # Убираем все кроме букв, цифр, пробелов, дефисов и подчеркиваний
            text = re.sub(r'[^a-z0-9 _-]', '', text)
            
            # Заменяем пробелы на подчеркивания
            text = re.sub(r'\s+', '_', text)
            
            # Убираем множественные подчеркивания
            text = re.sub(r'_+', '_', text).strip('_')
            
            # Ограничиваем длину
            return text[:self.callback_data_limit]
            
        except Exception as e:
            self.logger.error(f"Ошибка нормализации текста кнопки: {e}")
            return "unknown_button"
    
    def build_reply_markup(self, inline=None, reply=None):
        """Строит разметку клавиатуры для сообщения"""
        try:
            # Приоритет: inline > reply
            if inline:
                markup = {
                    "inline_keyboard": [
                        [
                            self._build_inline_button(btn) for btn in row
                        ]
                        for row in inline
                    ]
                }
                return markup
            
            # Обработка reply клавиатуры
            if reply is not None:  # Проверяем на None, а не на truthiness
                if reply == []:  # Пустой список = убрать клавиатуру
                    return {"remove_keyboard": True}
                elif reply:  # Непустой список = показать клавиатуру
                    markup = {
                        "keyboard": [
                            [{"text": btn} for btn in row]
                            for row in reply
                        ],
                        "resize_keyboard": True
                    }
                    return markup
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка создания разметки клавиатуры: {e}")
            return None
    
    def _build_inline_button(self, btn):
        """Строит InlineKeyboardButton с универсальной логикой"""
        try:
            if isinstance(btn, str):
                # Простая строка -> callback_data с нормализованным текстом
                callback_data = self._normalize_button_text(btn)
                return {
                    "text": btn,
                    "callback_data": callback_data
                }
            elif isinstance(btn, dict):
                text = list(btn.keys())[0]
                value = btn[text]
                
                if isinstance(value, str):
                    # Проверяем, является ли значение ссылкой
                    if value.startswith(("http://", "https://", "tg://")):
                        return {
                            "text": text,
                            "url": value
                        }
                    else:
                        # Иначе используем как callback_data
                        return {
                            "text": text,
                            "callback_data": value
                        }
                else:
                    # Неизвестный тип значения -> резервный вариант
                    self.logger.warning(f"[ButtonMapper] Неизвестный тип значения кнопки: {type(value)}, значение: {repr(value)}")
                    callback_data = self._normalize_button_text(text)
                    return {
                        "text": text,
                        "callback_data": callback_data
                    }
            else:
                # Неизвестный тип -> резервный вариант
                self.logger.warning(f"[ButtonMapper] Неизвестный тип кнопки: {type(btn)}, значение: {repr(btn)}")
                callback_data = self._normalize_button_text(str(btn))
                return {
                    "text": str(btn),
                    "callback_data": callback_data
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка создания inline кнопки: {e}, кнопка: {repr(btn)}")
            # Резервный вариант
            return {
                "text": str(btn),
                "callback_data": "unknown_button"
            }
