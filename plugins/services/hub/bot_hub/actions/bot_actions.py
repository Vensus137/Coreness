"""
BotActions - действия для управления ботами
"""

from typing import Any, Dict


class BotActions:
    """
    Действия для управления ботами
    """
    
    def __init__(self, bot_info_manager, telegram_polling, telegram_api, webhook_manager, settings_manager, logger):
        self.bot_info_manager = bot_info_manager
        self.telegram_polling = telegram_polling
        self.telegram_api = telegram_api
        self.webhook_manager = webhook_manager
        self.settings_manager = settings_manager
        self.logger = logger
        
        # Получаем настройки из bot_hub
        bot_hub_settings = self.settings_manager.get_plugin_settings("bot_hub")
        use_webhooks_setting = bot_hub_settings.get('use_webhooks', False)
        
        # Автоматически переключаем на пулинг, если вебхуки недоступны
        # Проверяем доступность http_server через webhook_manager
        self.use_webhooks = use_webhooks_setting and webhook_manager.http_server is not None
        
        if use_webhooks_setting and not self.use_webhooks:
            self.logger.warning("Вебхуки включены в настройках, но http_server недоступен - автоматически используется пулинг")
    
    async def start_bot(self, data: dict) -> Dict[str, Any]:
        """
        Запуск бота
        """
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
            
            # Запускаем бота в зависимости от режима
            if self.use_webhooks:
                # Устанавливаем вебхук
                result = await self.webhook_manager.set_webhook(bot_id, bot_info['bot_token'])
                if result.get('result') == 'success':
                    return {"result": "success"}
                else:
                    return result
            else:
                # Запускаем пулинг
                success = await self.telegram_polling.start_bot_polling(bot_id, bot_info['bot_token'])
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Не удалось запустить бота {bot_id}"
                        }
                    }
                
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def stop_bot(self, data: dict) -> Dict[str, Any]:
        """
        Остановка конкретного бота
        """
        try:
            bot_id = data.get('bot_id')
            
            # Получаем информацию о боте для получения токена
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
            bot_token = bot_info.get('bot_token')
            
            # Останавливаем бота в зависимости от режима
            if self.use_webhooks:
                # Удаляем вебхук
                if bot_token:
                    result = await self.webhook_manager.delete_webhook(bot_token, bot_id)
                    return result
                else:
                    return {"result": "success"}
            else:
                # Останавливаем пулинг
                success = await self.telegram_polling.stop_bot_polling(bot_id)
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": f"Не удалось остановить бота {bot_id}"
                        }
                    }
                
        except Exception as e:
            self.logger.error(f"Ошибка остановки бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def stop_all_bots(self, data: dict) -> Dict[str, Any]:
        """
        Остановка всех ботов
        """
        try:
            if self.use_webhooks:
                # Для вебхуков нужно получить всех ботов и удалить вебхуки
                # Получаем всех ботов из БД
                master_repo = self.bot_info_manager.database_manager.get_master_repository()
                all_bots = await master_repo.get_all_bots()
                
                errors = []
                for bot_data in all_bots:
                    bot_id = bot_data.get('id')
                    bot_token = bot_data.get('bot_token')
                    
                    if bot_token:
                        result = await self.webhook_manager.delete_webhook(bot_token, bot_id)
                        if result.get('result') != 'success':
                            errors.append(f"Bot-{bot_id}")
                
                if errors:
                    self.logger.warning(f"Ошибки при остановке ботов: {', '.join(errors)}")
                    return {
                        "result": "partial_success",
                        "error": {
                            "code": "PARTIAL_ERROR",
                            "message": f"Не удалось остановить некоторых ботов: {', '.join(errors)}"
                        }
                    }
                
                return {"result": "success"}
            else:
                # Останавливаем все пулинги
                success = await self.telegram_polling.stop_all_polling()
                
                if success:
                    return {"result": "success"}
                else:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Не удалось остановить всех ботов"
                        }
                    }
                
        except Exception as e:
            self.logger.error(f"Ошибка остановки всех ботов: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_bot_config(self, data: dict) -> Dict[str, Any]:
        """
        Синхронизация конфигурации бота: создание/обновление бота + условный перезапуск пуллинга
        Перезапускает пулинг только если изменились критичные поля (bot_token, is_active) или бот создан впервые
        """
        try:
            tenant_id = data.get('tenant_id')
            
            # Получаем текущие данные бота ДО обновления (для сравнения)
            old_bot_data = None
            bot_id = None
            # Пытаемся найти существующего бота по tenant_id
            bot_result = await self.bot_info_manager.get_bot_info_by_tenant_id(tenant_id)
            if bot_result.get('result') == 'success':
                old_bot_data = bot_result.get('response_data', {})
                bot_id = old_bot_data.get('bot_id')
            # Если бот не найден (result == 'error') - это нормально, значит будет создан новый
            
            # Используем BotInfoManager для создания/обновления бота (БД + кэш)
            # Передаем data напрямую, так как он уже содержит все данные бота
            sync_result = await self.bot_info_manager.create_or_update_bot(data)
            
            if sync_result.get('result') != 'success':
                return sync_result
            
            bot_id = sync_result.get('response_data', {}).get('bot_id')
            action = sync_result.get('response_data', {}).get('action')
            
            # Определяем, нужно ли перезапускать пулинг
            # По умолчанию перезапускаем (безопасный подход)
            new_bot_token = data.get('bot_token')
            # Если токен не передан из конфига, используем из БД (старый)
            if new_bot_token is None and old_bot_data:
                new_bot_token = old_bot_data.get('bot_token')
            
            new_is_active = data.get('is_active', True)
            
            # Определяем, нужно ли перезапускать бота
            should_restart = True  # По умолчанию перезапускаем
            
            if action == "updated" and old_bot_data:
                # Бот обновлен - проверяем, изменились ли критичные поля
                old_bot_token = old_bot_data.get('bot_token')
                old_is_active = old_bot_data.get('is_active')
                
                # Проверяем текущее состояние
                if self.use_webhooks:
                    # Для вебхуков: всегда устанавливаем вебхук при синхронизации, если бот активен
                    # Это гарантирует установку вебхука при первом запуске и после перезапуска системы
                    # Telegram API сам обработает конфликт (409), если вебхук уже установлен
                    is_active = False  # Всегда считаем, что нужно установить/переустановить вебхук
                else:
                    # Для пулинга проверяем фактический статус
                    is_active = self.telegram_polling.is_bot_polling(bot_id)
                
                # НЕ перезапускаем только если:
                # 1. Критичные поля совпадают И
                # 2. Бот уже активен (только для пулинга)
                if (old_bot_token == new_bot_token and 
                    old_is_active is not None and 
                    old_is_active == new_is_active):
                    if self.use_webhooks:
                        # Для вебхуков всегда перезапускаем (устанавливаем вебхук)
                        # Это гарантирует установку вебхука при первом запуске и после перезапуска
                        should_restart = True
                    elif is_active:
                        # Для пулинга не перезапускаем, если он уже запущен
                        should_restart = False
                    else:
                        # Пулинг не запущен - нужно запустить
                        should_restart = True
            
            # Перезапускаем бота только если нужно
            if should_restart:
                # Останавливаем существующий режим
                if self.use_webhooks:
                    # Удаляем вебхук
                    if new_bot_token:
                        await self.webhook_manager.delete_webhook(new_bot_token, bot_id)
                else:
                    # Останавливаем пулинг
                    await self.telegram_polling.stop_bot_polling(bot_id)
                
                # Запускаем бота только если он активен
                if new_is_active:
                    if new_bot_token:
                        if self.use_webhooks:
                            # Устанавливаем вебхук
                            result = await self.webhook_manager.set_webhook(bot_id, new_bot_token)
                            if result.get('result') != 'success':
                                self.logger.error(f"[Bot-{bot_id}] Не удалось установить вебхук")
                        else:
                            # Запускаем пулинг
                            success = await self.telegram_polling.start_bot_polling(bot_id, new_bot_token)
                            if not success:
                                self.logger.error(f"[Bot-{bot_id}] Не удалось запустить пулинг")
                    else:
                        self.logger.warning(f"[Bot-{bot_id}] Отсутствует токен, бот не запущен")
            
            return {
                "result": "success",
                "response_data": {
                    "bot_id": bot_id,
                    "action": action
                }
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации конфигурации бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def sync_bot_commands(self, data: dict) -> Dict[str, Any]:
        """
        Синхронизация команд бота: сохранение в БД → применение в Telegram
        """
        try:
            bot_id = data.get('bot_id')
            command_list = data.get('command_list', [])
            
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
            
            # Сначала синхронизируем команды в базе данных
            sync_success = await self.bot_info_manager.sync_bot_commands(bot_id, command_list)
            if not sync_success:
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": f"Не удалось синхронизировать команды в БД для бота {bot_id}"
                    }
                }
            
            # Затем применяем команды в Telegram
            result = await self.telegram_api.sync_bot_commands(
                bot_info['bot_token'], 
                bot_id, 
                command_list
            )
            
            if result.get('result') == 'success':
                return {"result": "success"}
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                if isinstance(error_msg, dict):
                    error_msg = error_msg.get('message', 'Неизвестная ошибка')
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": error_msg
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации команд: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }
    
    async def set_bot_token(self, data: dict) -> Dict[str, Any]:
        """
        Установка токена бота.
        Бот должен быть создан через синхронизацию конфигурации (sync_bot_config).
        Токен будет проверен автоматически при запуске пулинга.
        """
        try:
            # Валидация выполняется централизованно в ActionRegistry
            tenant_id = data.get('tenant_id')
            
            # Проверяем, что поле явно передано (присутствует в data)
            if 'bot_token' not in data:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Нет полей для обновления"
                    }
                }
            
            bot_token = data.get('bot_token')  # Может быть None для удаления
            
            # Получаем текущие данные бота ДО обновления
            # Проверяем, что бот существует (должен быть создан через конфигурацию)
            bot_result = await self.bot_info_manager.get_bot_info_by_tenant_id(tenant_id)
            if bot_result.get('result') != 'success':
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Бот для тенанта {tenant_id} не найден. Сначала создайте бота через синхронизацию конфигурации (sync_bot_config)"
                    }
                }
            
            old_bot_data = bot_result.get('response_data', {})
            
            # Сохраняем токен в БД через create_or_update_bot
            # Токен будет проверен автоматически при запуске пулинга
            bot_data = {
                'tenant_id': tenant_id,
                'bot_token': bot_token,  # Может быть None для удаления
                'is_active': old_bot_data.get('is_active', True)
            }
            
            sync_result = await self.bot_info_manager.create_or_update_bot(bot_data)
            if sync_result.get('result') != 'success':
                return sync_result
            
            updated_bot_id = sync_result.get('response_data', {}).get('bot_id')
            
            # Останавливаем существующий режим (в любом случае, т.к. токен изменился или удален)
            if self.use_webhooks:
                # Удаляем вебхук
                old_token = old_bot_data.get('bot_token')
                if old_token:
                    await self.webhook_manager.delete_webhook(old_token, updated_bot_id)
            else:
                # Останавливаем пулинг
                await self.telegram_polling.stop_bot_polling(updated_bot_id)
            
            # Если токен не None и бот активен - запускаем бота с новым токеном
            if bot_token is not None and bot_data.get('is_active', True):
                if self.use_webhooks:
                    # Устанавливаем вебхук
                    result = await self.webhook_manager.set_webhook(updated_bot_id, bot_token)
                    if result.get('result') != 'success':
                        self.logger.warning(f"[Bot-{updated_bot_id}] Не удалось установить вебхук после установки токена (возможно, токен неверный)")
                else:
                    # Запускаем пулинг
                    success = await self.telegram_polling.start_bot_polling(updated_bot_id, bot_token)
                    if not success:
                        self.logger.warning(f"[Bot-{updated_bot_id}] Не удалось запустить пулинг после установки токена (возможно, токен неверный)")
            elif bot_token is None:
                # Токен удален - бот уже остановлен
                mode = "вебхук" if self.use_webhooks else "пулинг"
                self.logger.info(f"[Bot-{updated_bot_id}] Токен бота удален, {mode} остановлен")
            
            self.logger.info(f"[Tenant-{tenant_id}] [Bot-{updated_bot_id}] Токен установлен")
            
            return {
                "result": "success",
                "response_data": {}
            }
                
        except Exception as e:
            self.logger.error(f"Ошибка установки токена бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Внутренняя ошибка: {str(e)}"
                }
            }