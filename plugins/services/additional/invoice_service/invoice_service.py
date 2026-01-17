"""
Invoice Service - сервис для работы с инвойсами (создание, управление, обработка платежей)
"""

from typing import Any, Dict, Optional


class InvoiceService:
    """
    Сервис для работы с инвойсами:
    - Создание инвойсов (в БД и отправка/создание ссылки)
    - Подтверждение/отклонение платежей
    - Получение информации об инвойсах
    - Управление инвойсами (отмена)
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        self.telegram_api = kwargs['telegram_api']
        self.datetime_formatter = kwargs['datetime_formatter']
        # Получаем настройки
        self.settings = self.settings_manager.get_plugin_settings('invoice_service')
        
        # Регистрируем себя в ActionHub
        self.action_hub.register('invoice_service', self)
    
    # === Actions для ActionHub ===
    
    async def create_invoice(self, data: dict) -> Dict[str, Any]:
        """
        Создание инвойса в БД и отправка/создание ссылки
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            bot_id = data.get('bot_id')
            
            # target_user_id с fallback на user_id из контекста
            target_user_id = data.get('target_user_id') or data.get('user_id')
            chat_id = data.get('chat_id')
            title = data.get('title')
            description = data.get('description', '')
            currency = data.get('currency', 'XTR')
            amount = data.get('amount')
            as_link = data.get('as_link', False)
            
            # Если не создаем ссылку, нужен chat_id
            if not as_link and not chat_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "chat_id обязателен для отправки инвойса"
                    }
                }
            
            # Получаем информацию о боте через bot_hub
            bot_result = await self.action_hub.execute_action('get_bot_info', {'bot_id': bot_id})
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Неизвестная ошибка')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Неизвестная ошибка')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Не удалось получить информацию о боте: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            bot_token = bot_info.get('bot_token')
            if not bot_token:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Токен бота не найден"
                    }
                }
            
            # Создаем инвойс в БД
            master_repo = self.database_manager.get_master_repository()
            
            invoice_data = {
                'tenant_id': tenant_id,
                'user_id': target_user_id,
                'title': title,
                'description': description,
                'amount': amount
            }
            
            invoice_id = await master_repo.create_invoice(invoice_data)
            if not invoice_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось создать инвойс в БД"
                    }
                }
            
            # Отправляем инвойс или создаем ссылку
            if as_link:
                # Создаем ссылку
                link_result = await self.telegram_api.create_invoice_link(
                    bot_token,
                    bot_id,
                    {
                        'title': title,
                        'description': description,
                        'payload': str(invoice_id),
                        'amount': amount,
                        'currency': currency
                    }
                )
                
                if link_result.get('result') != 'success':
                    # Если не удалось создать ссылку, удаляем инвойс из БД
                    await master_repo.cancel_invoice(tenant_id, invoice_id)
                    error_msg = link_result.get('error', 'Неизвестная ошибка')
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Неизвестная ошибка')
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Не удалось создать ссылку: {error_msg}"
                        }
                    }
                
                invoice_link = link_result.get('response_data', {}).get('invoice_link')
                
                # Обновляем инвойс с ссылкой
                await master_repo.update_invoice(
                    invoice_id,
                    {'link': invoice_link}
                )
                
                return {
                    "result": "success",
                    "response_data": {
                        "invoice_id": invoice_id,
                        "invoice_link": invoice_link
                    }
                }
            else:
                # Отправляем инвойс
                send_result = await self.telegram_api.send_invoice(
                    bot_token,
                    bot_id,
                    {
                        'chat_id': chat_id,
                        'title': title,
                        'description': description,
                        'payload': str(invoice_id),
                        'amount': amount,
                        'currency': currency
                    }
                )
                
                if send_result.get('result') != 'success':
                    # Если не удалось отправить, удаляем инвойс из БД
                    await master_repo.cancel_invoice(tenant_id, invoice_id)
                    error_msg = send_result.get('error', 'Неизвестная ошибка')
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Неизвестная ошибка')
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Не удалось отправить инвойс: {error_msg}"
                        }
                    }
                
                invoice_message_id = send_result.get('response_data', {}).get('invoice_message_id')
                
                return {
                    "result": "success",
                    "response_data": {
                        "invoice_id": invoice_id,
                        "invoice_message_id": invoice_message_id
                    }
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка создания инвойса: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def _get_bot_token(self, data: dict) -> tuple[Optional[str], Optional[int], Optional[Dict[str, Any]]]:
        """
        Получение bot_token для подтверждения/отклонения платежа
        
        Валидация входных данных (tenant_id, bot_id, pre_checkout_query_id) 
        выполняется централизованно в ActionRegistry
        """
        bot_id = data.get('bot_id')
        
        # Получаем информацию о боте через bot_hub
        bot_result = await self.action_hub.execute_action('get_bot_info', {'bot_id': bot_id})
        if bot_result.get('result') != 'success':
            error_msg = bot_result.get('error', 'Неизвестная ошибка')
            if isinstance(error_msg, dict):
                error_msg = error_msg.get('message', 'Неизвестная ошибка')
            return None, None, {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Не удалось получить информацию о боте: {error_msg}"
                }
            }
        
        bot_info = bot_result.get('response_data', {})
        bot_token = bot_info.get('bot_token')
        if not bot_token:
            return None, None, {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Токен бота не найден"
                }
            }
        
        return bot_token, bot_id, None
    
    async def confirm_payment(self, data: dict) -> Dict[str, Any]:
        """
        Подтверждение платежа (ответ на pre_checkout_query с подтверждением)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            bot_token, bot_id, error = await self._get_bot_token(data)
            if error:
                return error
            
            pre_checkout_query_id = data.get('pre_checkout_query_id')
            tenant_id = data.get('tenant_id')
            invoice_payload = data.get('invoice_payload')
            
            # Если передан invoice_payload, проверяем статус инвойса
            if invoice_payload and tenant_id:
                try:
                    invoice_id = int(invoice_payload)
                    master_repo = self.database_manager.get_master_repository()
                    invoice = await master_repo.get_invoice_by_id(invoice_id)
                    
                    if invoice:
                        # Получаем кастомное сообщение об ошибке или используем дефолтное
                        error_message = data.get('error_message')
                        
                        if invoice.get('is_cancelled'):
                            # Отклоняем платеж, если инвойс отменен
                            reject_data = {
                                'tenant_id': tenant_id,
                                'bot_id': bot_id,
                                'pre_checkout_query_id': pre_checkout_query_id,
                                'error_message': error_message or 'Платеж невозможен: счет был отменен'
                            }
                            reject_result = await self.reject_payment(reject_data)
                            # Возвращаем результат отклонения (failed - нормальное бизнес-поведение)
                            if reject_result.get('result') == 'success':
                                return {
                                    "result": "failed",
                                    "error": {
                                        "code": "INVOICE_CANCELLED",
                                        "message": error_message or 'Платеж невозможен: счет был отменен'
                                    }
                                }
                            return reject_result
                        
                        if invoice.get('paid_at'):
                            # Отклоняем платеж, если инвойс уже оплачен
                            reject_data = {
                                'tenant_id': tenant_id,
                                'bot_id': bot_id,
                                'pre_checkout_query_id': pre_checkout_query_id,
                                'error_message': error_message or 'Платеж невозможен: этот счет уже был оплачен'
                            }
                            reject_result = await self.reject_payment(reject_data)
                            # Возвращаем результат отклонения (failed - нормальное бизнес-поведение)
                            if reject_result.get('result') == 'success':
                                return {
                                    "result": "failed",
                                    "error": {
                                        "code": "INVOICE_ALREADY_PAID",
                                        "message": error_message or 'Платеж невозможен: этот счет уже был оплачен'
                                    }
                                }
                            return reject_result
                except (ValueError, TypeError):
                    # Если не удалось распарсить invoice_id, продолжаем без проверки
                    pass
            
            # Подтверждаем платеж через Telegram API
            result = await self.telegram_api.answer_pre_checkout_query(
                bot_token,
                bot_id,
                {
                    'pre_checkout_query_id': pre_checkout_query_id,
                    'ok': True
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка подтверждения платежа: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def reject_payment(self, data: dict) -> Dict[str, Any]:
        """
        Отклонение платежа (ответ на pre_checkout_query с отклонением)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            bot_token, bot_id, error = await self._get_bot_token(data)
            if error:
                return error
            
            pre_checkout_query_id = data.get('pre_checkout_query_id')
            error_message = data.get('error_message')
            
            # Отклоняем платеж через Telegram API
            payload = {
                'pre_checkout_query_id': pre_checkout_query_id,
                'ok': False
            }
            if error_message:
                payload['error_message'] = error_message
            
            result = await self.telegram_api.answer_pre_checkout_query(
                bot_token,
                bot_id,
                payload
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка отклонения платежа: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_invoice(self, data: dict) -> Dict[str, Any]:
        """
        Получение информации об инвойсе
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            invoice_id = data.get('invoice_id')
            
            master_repo = self.database_manager.get_master_repository()
            invoice = await master_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Инвойс не найден"
                    }
                }
            
            # Проверяем, что инвойс принадлежит тенанту
            if invoice.get('tenant_id') != tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Инвойс не принадлежит данному тенанту"
                    }
                }
            
            # Формируем ответ (оборачиваем в объект invoice для защиты от deep merge)
            invoice_data = {
                "invoice": {
                    "invoice_id": invoice.get('id'),
                    "tenant_id": invoice.get('tenant_id'),
                    "user_id": invoice.get('user_id'),
                    "title": invoice.get('title'),
                    "description": invoice.get('description'),
                    "amount": invoice.get('amount'),
                    "link": invoice.get('link'),
                    "is_cancelled": invoice.get('is_cancelled'),
                    "telegram_payment_charge_id": invoice.get('telegram_payment_charge_id'),
                    "paid_at": await self.datetime_formatter.to_iso_string(invoice.get('paid_at')) if invoice.get('paid_at') else None,
                    "created_at": await self.datetime_formatter.to_iso_string(invoice.get('created_at')) if invoice.get('created_at') else None
                }
            }
            
            return {
                "result": "success",
                "response_data": invoice_data
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения инвойса: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def get_user_invoices(self, data: dict) -> Dict[str, Any]:
        """
        Получение всех инвойсов пользователя
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # target_user_id с fallback на user_id из контекста
            target_user_id = data.get('target_user_id') or data.get('user_id')
            if not target_user_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "target_user_id или user_id обязателен"
                    }
                }
            
            include_cancelled = data.get('include_cancelled', False)
            
            master_repo = self.database_manager.get_master_repository()
            invoices = await master_repo.get_invoices_by_user(
                tenant_id,
                target_user_id,
                include_cancelled
            )
            
            # Формируем список инвойсов
            invoices_list = []
            for invoice in invoices:
                invoices_list.append({
                    "invoice_id": invoice.get('id'),
                    "tenant_id": invoice.get('tenant_id'),
                    "user_id": invoice.get('user_id'),
                    "title": invoice.get('title'),
                    "description": invoice.get('description'),
                    "amount": invoice.get('amount'),
                    "link": invoice.get('link'),
                    "is_cancelled": invoice.get('is_cancelled'),
                    "telegram_payment_charge_id": invoice.get('telegram_payment_charge_id'),
                    "paid_at": await self.datetime_formatter.to_iso_string(invoice.get('paid_at')) if invoice.get('paid_at') else None,
                    "created_at": await self.datetime_formatter.to_iso_string(invoice.get('created_at')) if invoice.get('created_at') else None
                })
            
            return {
                "result": "success",
                "response_data": {
                    "invoices": invoices_list
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения инвойсов пользователя: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def cancel_invoice(self, data: dict) -> Dict[str, Any]:
        """
        Отмена инвойса (установка флага is_cancelled)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            invoice_id = data.get('invoice_id')
            
            master_repo = self.database_manager.get_master_repository()
            
            # Проверяем, что инвойс существует и принадлежит тенанту
            invoice = await master_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Инвойс не найден"
                    }
                }
            
            if invoice.get('tenant_id') != tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Инвойс не принадлежит данному тенанту"
                    }
                }
            
            # Проверяем, что инвойс еще не оплачен
            if invoice.get('paid_at'):
                return {
                    "result": "error",
                    "error": {
                        "code": "INVALID_STATE",
                        "message": "Нельзя отменить оплаченный инвойс"
                    }
                }
            
            # Отменяем инвойс
            await master_repo.cancel_invoice(invoice_id)
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка отмены инвойса: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def mark_invoice_as_paid(self, data: dict) -> Dict[str, Any]:
        """
        Отметить инвойс как оплаченный (обработка события payment_successful)
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            invoice_payload = data.get('invoice_payload')
            telegram_payment_charge_id = data.get('telegram_payment_charge_id')
            
            # Парсим invoice_id из payload (payload - это строка с ID инвойса)
            try:
                invoice_id = int(invoice_payload)
            except (ValueError, TypeError):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Некорректный invoice_payload: {invoice_payload}"
                    }
                }
            
            master_repo = self.database_manager.get_master_repository()
            
            # Проверяем, что инвойс существует и принадлежит тенанту
            invoice = await master_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Инвойс не найден"
                    }
                }
            
            if invoice.get('tenant_id') != tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Инвойс не принадлежит данному тенанту"
                    }
                }
            
            # Проверяем, что инвойс еще не оплачен
            if invoice.get('paid_at'):
                self.logger.warning(f"[Tenant-{tenant_id}] [Invoice-{invoice_id}] Уже помечен как оплаченный, пропускаем обновление")
                return {"result": "success"}
            
            # Получаем дату оплаты или используем текущую
            paid_at_str = data.get('paid_at')
            if paid_at_str:
                paid_at = await self.datetime_formatter.parse_date_string(paid_at_str)
                if not paid_at:
                    self.logger.warning(f"[Tenant-{tenant_id}] [Invoice-{invoice_id}] Не удалось распарсить paid_at, используем текущую дату")
                    paid_at = await self.datetime_formatter.now_local()
            else:
                paid_at = await self.datetime_formatter.now_local()
            
            # Отмечаем инвойс как оплаченный
            success = await master_repo.mark_invoice_as_paid(invoice_id, telegram_payment_charge_id, paid_at)
            if not success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось обновить инвойс"
                    }
                }
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Ошибка отметки инвойса как оплаченного: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }

