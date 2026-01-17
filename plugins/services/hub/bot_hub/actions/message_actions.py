"""
Действия для работы с сообщениями через Bot Hub
"""

from typing import Any, Dict


class MessageActions:
    """Действия для работы с сообщениями"""
    
    def __init__(self, bot_info_manager, telegram_api, logger, settings=None):
        self.bot_info_manager = bot_info_manager
        self.telegram_api = telegram_api
        self.logger = logger
        self.settings = settings or {}
        # Сохраняем значение по умолчанию из настроек при инициализации
        self.default_buttons_per_row = self.settings.get('default_buttons_per_row', 2)
    
    async def send_message(self, data: dict) -> Dict[str, Any]:
        """Отправка сообщения боту"""
        try:
            bot_id = data.get('bot_id')
            
            # Получаем информацию о боте
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Неизвестная ошибка')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Неизвестная ошибка')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Не удалось получить информацию о боте {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Токен бота {bot_id} не найден"
                    }
                }
            
            # Отправляем сообщение через telegram_api (передаем исходные data)
            result = await self.telegram_api.send_message(
                bot_info['bot_token'], 
                bot_id, 
                data
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def delete_message(self, data: dict) -> Dict[str, Any]:
        """Удаление сообщения бота"""
        try:
            bot_id = data.get('bot_id')
            
            # Получаем информацию о боте
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Неизвестная ошибка')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Неизвестная ошибка')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Не удалось получить информацию о боте {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Токен бота {bot_id} не найден"
                    }
                }
            
            # Удаляем сообщение через telegram_api (передаем исходные data)
            result = await self.telegram_api.delete_message(
                bot_info['bot_token'], 
                bot_id, 
                data
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def build_keyboard(self, data: dict) -> Dict[str, Any]:
        """
        Построение клавиатуры из массива ID с использованием шаблонов
        
        Параметры:
        - items: массив ID (обязательно)
        - keyboard_type: тип клавиатуры - "inline" или "reply" (обязательно)
        - text_template: шаблон текста кнопки с плейсхолдером $value$ (обязательно)
        - callback_template: шаблон callback_data для inline клавиатуры с плейсхолдером $value$ (обязательно для inline)
        - buttons_per_row: количество кнопок в строке (опционально, по умолчанию 1)
        
        Примечание: Используется синтаксис $value$ вместо {value} чтобы избежать конфликта
        с системой плейсхолдеров, которая обрабатывает {value} как плейсхолдер.
        """
        try:
            items = data.get('items')
            keyboard_type = data.get('keyboard_type')
            text_template = data.get('text_template')
            callback_template = data.get('callback_template')
            buttons_per_row = data.get('buttons_per_row', self.default_buttons_per_row)
            
            # Дополнительная бизнес-валидация: callback_template обязателен для inline
            if keyboard_type == 'inline' and not callback_template:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "callback_template обязателен для inline клавиатуры"
                    }
                }
            
            # Строим клавиатуру
            keyboard = []
            current_row = []
            
            for item_id in items:
                # Заменяем $value$ в шаблонах на текущий ID (используем $value$ чтобы избежать конфликта с плейсхолдерами)
                text = str(text_template).replace('$value$', str(item_id))
                
                if keyboard_type == 'inline':
                    callback = str(callback_template).replace('$value$', str(item_id))
                    button = {text: callback}
                else:  # reply
                    button = text
                
                current_row.append(button)
                
                # Если строка заполнена, добавляем её в клавиатуру
                if len(current_row) >= buttons_per_row:
                    keyboard.append(current_row)
                    current_row = []
            
            # Добавляем оставшиеся кнопки
            if current_row:
                keyboard.append(current_row)
            
            return {
                "result": "success",
                "response_data": {
                    "keyboard": keyboard,
                    "keyboard_type": keyboard_type,
                    "rows_count": len(keyboard),
                    "buttons_count": len(items)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка построения клавиатуры: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def answer_callback_query(self, data: dict) -> Dict[str, Any]:
        """Ответ на callback query (всплывающее уведомление или простое уведомление)"""
        try:
            bot_id = data.get('bot_id')
            
            # Получаем информацию о боте
            bot_result = await self.bot_info_manager.get_bot_info(bot_id)
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Неизвестная ошибка')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Неизвестная ошибка')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Не удалось получить информацию о боте {bot_id}: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            if not bot_info.get('bot_token'):
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Токен бота {bot_id} не найден"
                    }
                }
            
            # Отвечаем на callback query через telegram_api (передаем исходные data)
            result = await self.telegram_api.answer_callback_query(
                bot_info['bot_token'], 
                bot_id, 
                data
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка ответа на callback query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }