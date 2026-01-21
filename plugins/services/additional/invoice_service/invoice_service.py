"""
Invoice Service - service for working with invoices (creation, management, payment processing)
"""

from typing import Any, Dict, Optional


class InvoiceService:
    """
    Service for working with invoices:
    - Create invoices (in DB and send/create link)
    - Confirm/reject payments
    - Get invoice information
    - Manage invoices (cancel)
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.database_manager = kwargs['database_manager']
        self.telegram_api = kwargs['telegram_api']
        self.datetime_formatter = kwargs['datetime_formatter']
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('invoice_service')
        
        # Register ourselves in ActionHub
        self.action_hub.register('invoice_service', self)
    
    # === Actions for ActionHub ===
    
    async def create_invoice(self, data: dict) -> Dict[str, Any]:
        """
        Create invoice in DB and send/create link
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            bot_id = data.get('bot_id')
            
            # target_user_id with fallback to user_id from context
            target_user_id = data.get('target_user_id') or data.get('user_id')
            chat_id = data.get('chat_id')
            title = data.get('title')
            description = data.get('description', '')
            currency = data.get('currency', 'XTR')
            amount = data.get('amount')
            as_link = data.get('as_link', False)
            
            # If not creating link, chat_id is required
            if not as_link and not chat_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "chat_id is required for sending invoice"
                    }
                }
            
            # Get bot information through bot_hub
            bot_result = await self.action_hub.execute_action('get_bot_info', {'bot_id': bot_id})
            if bot_result.get('result') != 'success':
                error_msg = bot_result.get('error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Unknown error')
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Failed to get bot information: {error_msg}"
                    }
                }
            
            bot_info = bot_result.get('response_data', {})
            bot_token = bot_info.get('bot_token')
            if not bot_token:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Bot token not found"
                    }
                }
            
            # Create invoice in DB
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
                        "message": "Failed to create invoice in DB"
                    }
                }
            
            # Send invoice or create link
            if as_link:
                # Create link
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
                    # If failed to create link, delete invoice from DB
                    await master_repo.cancel_invoice(tenant_id, invoice_id)
                    error_msg = link_result.get('error', 'Unknown error')
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Unknown error')
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Failed to create link: {error_msg}"
                        }
                    }
                
                invoice_link = link_result.get('response_data', {}).get('invoice_link')
                
                # Update invoice with link
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
                # Send invoice
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
                    # If failed to send, delete invoice from DB
                    await master_repo.cancel_invoice(tenant_id, invoice_id)
                    error_msg = send_result.get('error', 'Unknown error')
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', 'Unknown error')
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Failed to send invoice: {error_msg}"
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
            self.logger.error(f"Error creating invoice: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def _get_bot_token(self, data: dict) -> tuple[Optional[str], Optional[int], Optional[Dict[str, Any]]]:
        """
Get bot_token for confirming/rejecting payment
        
        Input data validation (tenant_id, bot_id, pre_checkout_query_id)
        is done centrally in ActionRegistry
        """
        bot_id = data.get('bot_id')
        
        # Get bot information through bot_hub
        bot_result = await self.action_hub.execute_action('get_bot_info', {'bot_id': bot_id})
        if bot_result.get('result') != 'success':
            error_msg = bot_result.get('error', 'Unknown error')
            if isinstance(error_msg, dict):
                error_msg = error_msg.get('message', 'Unknown error')
            return None, None, {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Failed to get bot information: {error_msg}"
                }
            }
        
        bot_info = bot_result.get('response_data', {})
        bot_token = bot_info.get('bot_token')
        if not bot_token:
            return None, None, {
                "result": "error",
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Bot token not found"
                }
            }
        
        return bot_token, bot_id, None
    
    async def confirm_payment(self, data: dict) -> Dict[str, Any]:
        """
        Confirm payment (answer pre_checkout_query with confirmation)
        """
        try:
            # Validation is done centrally in ActionRegistry
            bot_token, bot_id, error = await self._get_bot_token(data)
            if error:
                return error
            
            pre_checkout_query_id = data.get('pre_checkout_query_id')
            tenant_id = data.get('tenant_id')
            invoice_payload = data.get('invoice_payload')
            
            # If invoice_payload provided, check invoice status
            if invoice_payload and tenant_id:
                try:
                    invoice_id = int(invoice_payload)
                    master_repo = self.database_manager.get_master_repository()
                    invoice = await master_repo.get_invoice_by_id(invoice_id)
                    
                    if invoice:
                        # Get custom error message or use default
                        error_message = data.get('error_message')
                        
                        if invoice.get('is_cancelled'):
                            # Reject payment if invoice cancelled
                            reject_data = {
                                'tenant_id': tenant_id,
                                'bot_id': bot_id,
                                'pre_checkout_query_id': pre_checkout_query_id,
                                'error_message': error_message or 'Payment impossible: invoice was cancelled'
                            }
                            reject_result = await self.reject_payment(reject_data)
                            # Return rejection result (failed - normal business behavior)
                            if reject_result.get('result') == 'success':
                                return {
                                    "result": "failed",
                                    "error": {
                                        "code": "INVOICE_CANCELLED",
                                        "message": error_message or 'Payment impossible: invoice was cancelled'
                                    }
                                }
                            return reject_result
                        
                        if invoice.get('paid_at'):
                            # Reject payment if invoice already paid
                            reject_data = {
                                'tenant_id': tenant_id,
                                'bot_id': bot_id,
                                'pre_checkout_query_id': pre_checkout_query_id,
                                'error_message': error_message or 'Payment impossible: this invoice was already paid'
                            }
                            reject_result = await self.reject_payment(reject_data)
                            # Return rejection result (failed - normal business behavior)
                            if reject_result.get('result') == 'success':
                                return {
                                    "result": "failed",
                                    "error": {
                                        "code": "INVOICE_ALREADY_PAID",
                                        "message": error_message or 'Payment impossible: this invoice was already paid'
                                    }
                                }
                            return reject_result
                except (ValueError, TypeError):
                    # If failed to parse invoice_id, continue without check
                    pass
            
            # Confirm payment through Telegram API
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
            self.logger.error(f"Error confirming payment: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def reject_payment(self, data: dict) -> Dict[str, Any]:
        """
        Reject payment (answer pre_checkout_query with rejection)
        """
        try:
            # Validation is done centrally in ActionRegistry
            bot_token, bot_id, error = await self._get_bot_token(data)
            if error:
                return error
            
            pre_checkout_query_id = data.get('pre_checkout_query_id')
            error_message = data.get('error_message')
            
            # Reject payment through Telegram API
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
            self.logger.error(f"Error rejecting payment: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_invoice(self, data: dict) -> Dict[str, Any]:
        """
        Get invoice information
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            invoice_id = data.get('invoice_id')
            
            master_repo = self.database_manager.get_master_repository()
            invoice = await master_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Invoice not found"
                    }
                }
            
            # Check that invoice belongs to tenant
            if invoice.get('tenant_id') != tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Invoice does not belong to this tenant"
                    }
                }
            
            # Form response (wrap in invoice object to protect from deep merge)
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
            self.logger.error(f"Error getting invoice: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def get_user_invoices(self, data: dict) -> Dict[str, Any]:
        """
        Get all user invoices
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # target_user_id with fallback to user_id from context
            target_user_id = data.get('target_user_id') or data.get('user_id')
            if not target_user_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "target_user_id or user_id is required"
                    }
                }
            
            include_cancelled = data.get('include_cancelled', False)
            
            master_repo = self.database_manager.get_master_repository()
            invoices = await master_repo.get_invoices_by_user(
                tenant_id,
                target_user_id,
                include_cancelled
            )
            
            # Form invoice list
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
            self.logger.error(f"Error getting user invoices: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def cancel_invoice(self, data: dict) -> Dict[str, Any]:
        """
        Cancel invoice (set is_cancelled flag)
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            invoice_id = data.get('invoice_id')
            
            master_repo = self.database_manager.get_master_repository()
            
            # Check that invoice exists and belongs to tenant
            invoice = await master_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Invoice not found"
                    }
                }
            
            if invoice.get('tenant_id') != tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Invoice does not belong to this tenant"
                    }
                }
            
            # Check that invoice is not yet paid
            if invoice.get('paid_at'):
                return {
                    "result": "error",
                    "error": {
                        "code": "INVALID_STATE",
                        "message": "Cannot cancel paid invoice"
                    }
                }
            
            # Cancel invoice
            await master_repo.cancel_invoice(invoice_id)
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error cancelling invoice: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def mark_invoice_as_paid(self, data: dict) -> Dict[str, Any]:
        """
        Mark invoice as paid (process payment_successful event)
        """
        try:
            # Validation is done centrally in ActionRegistry
            tenant_id = data.get('tenant_id')
            invoice_payload = data.get('invoice_payload')
            telegram_payment_charge_id = data.get('telegram_payment_charge_id')
            
            # Parse invoice_id from payload (payload is string with invoice ID)
            try:
                invoice_id = int(invoice_payload)
            except (ValueError, TypeError):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Invalid invoice_payload: {invoice_payload}"
                    }
                }
            
            master_repo = self.database_manager.get_master_repository()
            
            # Check that invoice exists and belongs to tenant
            invoice = await master_repo.get_invoice_by_id(invoice_id)
            if not invoice:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Invoice not found"
                    }
                }
            
            if invoice.get('tenant_id') != tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": "Invoice does not belong to this tenant"
                    }
                }
            
            # Check that invoice is not yet paid
            if invoice.get('paid_at'):
                self.logger.warning(f"[Tenant-{tenant_id}] [Invoice-{invoice_id}] Already marked as paid, skipping update")
                return {"result": "success"}
            
            # Get payment date or use current
            paid_at_str = data.get('paid_at')
            if paid_at_str:
                paid_at = await self.datetime_formatter.parse_date_string(paid_at_str)
                if not paid_at:
                    self.logger.warning(f"[Tenant-{tenant_id}] [Invoice-{invoice_id}] Failed to parse paid_at, using current date")
                    paid_at = await self.datetime_formatter.now_local()
            else:
                paid_at = await self.datetime_formatter.now_local()
            
            # Mark invoice as paid
            success = await master_repo.mark_invoice_as_paid(invoice_id, telegram_payment_charge_id, paid_at)
            if not success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Failed to update invoice"
                    }
                }
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error marking invoice as paid: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }

