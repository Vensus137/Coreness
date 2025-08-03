from aiogram.exceptions import TelegramBadRequest


class MessengerExtensions:
    """Дополнительный функционал messenger (опциональный)"""
    
    @staticmethod
    def process_private_answer(action: dict, chat_id: int, user_id: int = None, logger=None) -> int:
        """
        Обрабатывает private_answer параметр.
        Если private_answer=True и есть user_id, возвращает user_id для отправки в личку.
        """
        private_answer = action.get('private_answer', False)
        if private_answer:
            if user_id:
                return user_id
            else:
                if logger:
                    logger.error("private_answer=True, но user_id отсутствует в action. Сообщение не будет отправлено в личку.")
        return chat_id
    
    @staticmethod
    async def remove_message(bot, action: dict, logger) -> dict:
        """
        Удаляет сообщение из чата.
        """
        chat_id = action['chat_id']
        message_id = action['message_id']

        try:
            await bot.delete_message(chat_id, message_id)
            return {'success': True}
        except TelegramBadRequest as e:
            logger.warning(f"Не удалось удалить сообщение chat_id={chat_id}, message_id={message_id}: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения chat_id={chat_id}, message_id={message_id}: {e}")
            return {'success': False, 'error': str(e)} 