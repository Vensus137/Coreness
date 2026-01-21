"""
InvoiceAction - actions with invoices via Telegram API
"""

from typing import Any, Dict


class InvoiceAction:
    """Actions with invoices via Telegram API"""
    
    def __init__(self, api_client, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
    
    async def send_invoice(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Send invoice via Telegram API sendInvoice method
        """
        try:
            chat_id = data.get('chat_id')
            if not chat_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "chat_id not specified for sending invoice"
                    }
                }
            
            title = data.get('title')
            if not title:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "title not specified for invoice"
                    }
                }
            
            description = data.get('description', '')
            payload = data.get('payload')
            if not payload:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "payload (invoice ID) not specified"
                    }
                }
            
            amount = data.get('amount')
            if not amount or not isinstance(amount, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "amount (number of stars) not specified or is not an integer"
                    }
                }
            
            currency = data.get('currency', 'XTR')  # Default XTR for stars
            
            # Build prices for Telegram API
            # For stars, need an array with one element
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
                'payload': str(payload),  # Telegram API requires string
                'currency': currency,
                'prices': prices
            }
            
            # Execute request
            result = await self.api_client.make_request_with_limit(
                bot_token,
                "sendInvoice",
                payload_data,
                bot_id=bot_id,
                chat_id=chat_id
            )
            
            # Process result and return only needed fields
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
                # Return only result and error, without response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Unknown error"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error sending invoice: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def create_invoice_link(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Create invoice link via Telegram API createInvoiceLink method
        """
        try:
            title = data.get('title')
            if not title:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "title not specified for invoice"
                    }
                }
            
            description = data.get('description', '')
            payload = data.get('payload')
            if not payload:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "payload (invoice ID) not specified"
                    }
                }
            
            amount = data.get('amount')
            if not amount or not isinstance(amount, int):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "amount (number of stars) not specified or is not an integer"
                    }
                }
            
            currency = data.get('currency', 'XTR')  # Default XTR for stars
            
            # Build prices for Telegram API
            prices = [
                {
                    "label": title,
                    "amount": amount
                }
            ]
            
            payload_data = {
                'title': title,
                'description': description,
                'payload': str(payload),  # Telegram API requires string
                'currency': currency,
                'prices': prices
            }
            
            # Execute request
            result = await self.api_client.make_request(
                bot_token,
                "createInvoiceLink",
                payload_data
            )
            
            # Process result and return only needed fields
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
                # Return only result and error, without response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Unknown error"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error creating invoice link: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def answer_pre_checkout_query(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """
        Answer payment confirmation request via Telegram API answerPreCheckoutQuery method
        """
        try:
            pre_checkout_query_id = data.get('pre_checkout_query_id')
            if not pre_checkout_query_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "pre_checkout_query_id not specified"
                    }
                }
            
            ok = data.get('ok')
            if ok is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "ok (true/false) not specified"
                    }
                }
            
            payload_data = {
                'pre_checkout_query_id': pre_checkout_query_id,
                'ok': ok
            }
            
            # If rejecting, can specify error message
            if not ok and data.get('error_message'):
                payload_data['error_message'] = data.get('error_message')
            
            # Execute request
            result = await self.api_client.make_request(
                bot_token,
                "answerPreCheckoutQuery",
                payload_data
            )
            
            # Process result and return only needed fields
            if result.get('result') == 'success':
                # According to config.yaml, on success return only result without response_data
                return {"result": "success"}
            else:
                # Return only result and error, without response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Unknown error"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Error answering pre_checkout_query: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }

