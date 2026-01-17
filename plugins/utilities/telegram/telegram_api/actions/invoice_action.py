"""
InvoiceAction - действия с инвойсами через Telegram API
"""

from typing import Any, Dict


class InvoiceAction:
    """Действия с инвойсами через Telegram API"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    async def send_invoice(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Отправка инвойса через Telegram API метод sendInvoice
        """
        try:
            chat_id = data.get('chat_id')
            if not chat_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан chat_id для отправки инвойса"
                    }
                }
            
            title = data.get('title')
            if not title:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан title для инвойса"
                    }
                }
            
            description = data.get('description', '')
            payload = data.get('payload')
            if not payload:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан payload (ID инвойса)"
                    }
                }
            
            amount = data.get('amount')
            if not amount or not isinstance(amount, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан amount (количество звезд) или он не является целым числом"
                    }
                }
            
            currency = data.get('currency', 'XTR')  # По умолчанию XTR для звезд
            
            # Формируем prices для Telegram API
            # Для звезд нужен массив с одним элементом
            prices = [
                {
                    "label": title,
                    "amount": amount
                }
            ]
            
            payload_data = {
                'chat_id': chat_id,
                'title': title,
                'description': description,
                'payload': str(payload),  # Telegram API требует строку
                'currency': currency,
                'prices': prices
            }
            
            # Выполняем запрос
            result = await self.api_client.make_request_with_limit(
                bot_token,
                "sendInvoice",
                payload_data,
                bot_id=bot_id,
                chat_id=chat_id
            )
            
            # Обрабатываем результат и возвращаем только нужные поля
            if result.get('result') == 'success':
                response_data = result.get('response_data', {})
                message_id = response_data.get('message_id')
                
                return {
                    "result": "success",
                    "response_data": {
                        "invoice_message_id": message_id
                    }
                }
            else:
                # Возвращаем только result и error, без response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Неизвестная ошибка"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка отправки инвойса: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def create_invoice_link(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Создание ссылки на инвойс через Telegram API метод createInvoiceLink
        """
        try:
            title = data.get('title')
            if not title:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан title для инвойса"
                    }
                }
            
            description = data.get('description', '')
            payload = data.get('payload')
            if not payload:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан payload (ID инвойса)"
                    }
                }
            
            amount = data.get('amount')
            if not amount or not isinstance(amount, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан amount (количество звезд) или он не является целым числом"
                    }
                }
            
            currency = data.get('currency', 'XTR')  # По умолчанию XTR для звезд
            
            # Формируем prices для Telegram API
            prices = [
                {
                    "label": title,
                    "amount": amount
                }
            ]
            
            payload_data = {
                'title': title,
                'description': description,
                'payload': str(payload),  # Telegram API требует строку
                'currency': currency,
                'prices': prices
            }
            
            # Выполняем запрос
            result = await self.api_client.make_request(
                bot_token,
                "createInvoiceLink",
                payload_data
            )
            
            # Обрабатываем результат и возвращаем только нужные поля
            if result.get('result') == 'success':
                response_data = result.get('response_data', {})
                invoice_link = response_data.get('invoice_link') if isinstance(response_data, dict) else response_data
                
                return {
                    "result": "success",
                    "response_data": {
                        "invoice_link": invoice_link
                    }
                }
            else:
                # Возвращаем только result и error, без response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Неизвестная ошибка"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка создания ссылки на инвойс: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def answer_pre_checkout_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Ответ на запрос подтверждения оплаты через Telegram API метод answerPreCheckoutQuery
        """
        try:
            pre_checkout_query_id = data.get('pre_checkout_query_id')
            if not pre_checkout_query_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан pre_checkout_query_id"
                    }
                }
            
            ok = data.get('ok')
            if ok is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Не указан ok (true/false)"
                    }
                }
            
            payload_data = {
                'pre_checkout_query_id': pre_checkout_query_id,
                'ok': ok
            }
            
            # Если отклоняем, можно указать сообщение об ошибке
            if not ok and data.get('error_message'):
                payload_data['error_message'] = data.get('error_message')
            
            # Выполняем запрос
            result = await self.api_client.make_request(
                bot_token,
                "answerPreCheckoutQuery",
                payload_data
            )
            
            # Обрабатываем результат и возвращаем только нужные поля
            if result.get('result') == 'success':
                # Согласно config.yaml, при успехе возвращаем только result без response_data
                return {"result": "success"}
            else:
                # Возвращаем только result и error, без response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Неизвестная ошибка"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка ответа на pre_checkout_query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

