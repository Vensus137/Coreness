"""
BotInfoManager - подмодуль для сбора и кэширования информации о ботах
"""

from typing import Any, Dict, List


class BotInfoManager:
    """
    Менеджер информации о ботах
    Собирает данные из базы и кэширует их для быстрого доступа
    """
    
    def __init__(self, database_manager, action_hub, telegram_api, telegram_polling, logger, cache_manager, settings_manager, webhook_manager):
        self.database_manager = database_manager
        self.action_hub = action_hub
        self.telegram_api = telegram_api
        self.telegram_polling = telegram_polling
        self.logger = logger
        self.cache_manager = cache_manager
        self.webhook_manager = webhook_manager
        
        # Получаем TTL из конфига bot_hub
        bot_hub_settings = settings_manager.get_plugin_settings("bot_hub")
        self._bot_ttl = bot_hub_settings.get('cache_ttl', 315360000)  # Вечный кэш
        self._error_ttl = bot_hub_settings.get('error_cache_ttl', 300)  # Кэш ошибок
    
    def _get_bot_cache_key(self, bot_id: int) -> str:
        """Генерация ключа кэша для бота по bot_id"""
        return f"bot:{bot_id}"
    
    def _get_token_cache_key(self, bot_token: str) -> str:
        """Генерация ключа кэша для бота по токену"""
        return f"bot:token:{bot_token}"
    
    def _format_token_for_logs(self, bot_token: str) -> str:
        """
        Форматирование токена для логов: первые 15 символов
        Формат токена: {bot_id}:{secret}, где bot_id можно извлечь из начала
        """
        if not bot_token:
            return "[Bot-Token: unknown]"
        
        # Берем первые 15 символов (обычно это bot_id + часть секрета)
        return f"[Bot-Token: {bot_token[:15]}...]"
    
    async def _get_telegram_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """
        Получение информации о боте через Telegram API
        """
        try:
            result = await self.telegram_api.get_bot_info(bot_token)
            
            if result.get('result') == 'success':
                return result.get('response_data', {})
            else:
                token_info = self._format_token_for_logs(bot_token)
                self.logger.warning(f"{token_info} Не удалось получить информацию о боте: {result.get('error', 'Неизвестная ошибка')}")
                return {}
                
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Ошибка получения информации о боте через Telegram API: {e}")
            return {}
    
    async def get_telegram_bot_info_by_token(self, bot_token: str) -> Dict[str, Any]:
        """
        Получение полной информации о боте по токену (с вечным кэшированием)
        Возвращает результат в стандартном формате ActionHub
        """
        try:
            if not bot_token:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "bot_token обязателен"
                    }
                }
            
            # Проверяем кэш
            cache_key = self._get_token_cache_key(bot_token)
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                # Проверяем, это ошибка или данные
                if cached_data.get('_error'):
                    # Это кэшированная ошибка
                    return {
                        "result": "error",
                        "error": {
                            "code": cached_data.get('code', 'UNKNOWN_ERROR'),
                            "message": cached_data.get('message', 'Неизвестная ошибка')
                        }
                    }
                else:
                    # Это данные бота
                    return {"result": "success", "response_data": cached_data}
            
            # Получаем информацию о боте через Telegram API
            # bot_id недоступен в этом методе, так как он вызывается только по токену
            bot_info = await self._get_telegram_bot_info(bot_token)
            
            # Формируем результат в стандартном формате
            if bot_info and bot_info.get('telegram_bot_id'):
                # Сохраняем в кэш только данные (без обертки)
                await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
                return {
                    "result": "success",
                    "response_data": bot_info
                }
            else:
                # Кэшируем ошибку с коротким TTL
                error_data = {
                    '_error': True,
                    'code': 'API_ERROR',
                    'message': 'Не удалось получить информацию о боте'
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": "Не удалось получить информацию о боте"
                    }
                }
            
        except Exception as e:
            token_info = self._format_token_for_logs(bot_token)
            self.logger.error(f"{token_info} Ошибка получения информации о боте: {e}")
            # Кэшируем ошибку с коротким TTL
            error_data = {
                '_error': True,
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
            await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def get_bot_info(self, bot_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Получение полной информации о боте из базы данных (с кэшированием)
        Возвращает универсальную структуру: {"result": "success/error", "error": "...", "response_data": {...}}
        """
        try:
            # Проверяем кэш
            cache_key = self._get_bot_cache_key(bot_id)
            if not force_refresh:
                cached_data = await self.cache_manager.get(cache_key)
                if cached_data:
                    # Проверяем, это ошибка или данные
                    if cached_data.get('_error'):
                        # Это кэшированная ошибка
                        return {
                            "result": "error",
                            "error": {
                                "code": cached_data.get('code', 'UNKNOWN_ERROR'),
                                "message": cached_data.get('message', 'Неизвестная ошибка')
                            }
                        }
                    else:
                        # Это данные бота
                        return {"result": "success", "response_data": cached_data}
            
            # Собираем информацию из базы
            result = await self._collect_bot_info_from_db(bot_id)
            
            # Проверяем, есть ли ошибка
            if result.get('error'):
                error_info = result['error']
                error_type = error_info.get('type')
                
                if error_type == 'NOT_FOUND':
                    error_code = 'NOT_FOUND'
                    error_message = f'Бот {bot_id} не найден в базе данных'
                else:  # INTERNAL_ERROR
                    error_code = 'INTERNAL_ERROR'
                    error_message = error_info.get('message', 'Ошибка получения информации о боте из БД')
                
                # Кэшируем ошибку с коротким TTL
                error_data = {
                    '_error': True,
                    'code': error_code,
                    'message': error_message
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": error_code,
                        "message": error_message
                    }
                }
            
            # Получаем данные бота
            bot_info = result.get('bot_info')
            if not bot_info:
                # На всякий случай (не должно случиться, но для безопасности)
                error_data = {
                    '_error': True,
                    'code': 'INTERNAL_ERROR',
                    'message': 'Не удалось получить данные о боте'
                }
                await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
                return {
                    "result": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Не удалось получить данные о боте"
                    }
                }
            
            # Сохраняем в кэш только данные (без обертки)
            await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
            
            # Сохраняем маппинг tenant_id -> bot_id для быстрого доступа
            tenant_id = bot_info.get('tenant_id')
            if tenant_id:
                tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
                await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=self._bot_ttl)
            
            # Формируем универсальную структуру для возврата
            return {"result": "success", "response_data": bot_info}
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Неожиданная ошибка получения информации о боте: {e}")
            # Кэшируем ошибку с коротким TTL
            error_data = {
                '_error': True,
                'code': 'INTERNAL_ERROR',
                'message': str(e)
            }
            await self.cache_manager.set(cache_key, error_data, ttl=self._error_ttl)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def get_bot_info_by_tenant_id(self, tenant_id: int) -> Dict[str, Any]:
        """
        Получение информации о боте по tenant_id (с кэшированием)
        Возвращает универсальную структуру: {"result": "success/error", "error": "...", "response_data": {...}}
        """
        try:
            # Получаем мастер-репозиторий
            master_repo = self.database_manager.get_master_repository()
            
            # Получаем bot_id через get_bot_id_by_tenant_id (использует кэш маппинга)
            # Но у нас нет прямого доступа к tenant_cache, поэтому используем прямой запрос
            bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
            
            if not bot_data:
                return {"result": "error", "error": f"Бот для tenant {tenant_id} не найден"}
            
            # Сырые данные из БД используют 'id'
            bot_id = bot_data.get('id')
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Не удалось получить bot_id для tenant {tenant_id}"
                    }
                }
            
            # Используем существующий метод get_bot_info (с кэшированием)
            return await self.get_bot_info(bot_id, force_refresh=False)
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения информации о боте: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def load_all_bots_cache(self) -> List[Dict[str, Any]]:
        """Загрузка кэша для всех ботов при запуске сервиса"""
        try:
            # Получаем мастер-репозиторий
            master_repo = self.database_manager.get_master_repository()
            
            # Получаем всех ботов
            all_bots = await master_repo.get_all_bots()
            
            loaded_count = 0
            loaded_bots = []
            
            for bot_data in all_bots:
                bot_id = bot_data.get('id')
                if bot_id:
                    # Получаем команды для этого бота
                    commands = await master_repo.get_commands_by_bot(bot_id)
                    
                    # Формируем структуру данных используя унифицированный метод
                    # Это гарантирует единообразие формата данных в кэше
                    bot_info = self._format_bot_info(bot_data, commands)
                    
                    # Если данные некорректны - пропускаем (bot_token может быть None - это нормально)
                    if not bot_info.get('tenant_id'):
                        self.logger.warning(f"[Bot-{bot_id}] Пропущен при загрузке кэша: отсутствует tenant_id")
                        continue
                    
                    # Сохраняем в кэш только данные (без обертки)
                    cache_key = self._get_bot_cache_key(bot_id)
                    await self.cache_manager.set(cache_key, bot_info, ttl=self._bot_ttl)
                    
                    # Сохраняем маппинг tenant_id -> bot_id для быстрого доступа
                    tenant_id = bot_info.get('tenant_id')
                    if tenant_id:
                        tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
                        await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=self._bot_ttl)
                    
                    # Для возврата оборачиваем в формат ответа
                    loaded_bots.append({"result": "success", "response_data": bot_info})
                    loaded_count += 1
            
            self.logger.info(f"Загружено {loaded_count} ботов в кэш")
            
            return loaded_bots
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кэша всех ботов: {e}")
            return []
    
    async def refresh_bot_info(self, bot_id: int) -> bool:
        """Принудительное обновление информации о боте"""
        try:
            await self.get_bot_info(bot_id, force_refresh=True)
            return True
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка обновления информации о боте: {e}")
            return False
    
    async def clear_bot_cache(self, bot_id: int = None) -> bool:
        """Очистка кэша для конкретного бота или всего кэша"""
        try:
            if bot_id:
                cache_key = self._get_bot_cache_key(bot_id)
                # Получаем bot_info чтобы узнать tenant_id
                bot_info = await self.cache_manager.get(cache_key)
                if bot_info:
                    tenant_id = bot_info.get('tenant_id')
                    if tenant_id:
                        # Очищаем маппинг tenant -> bot_id
                        tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
                        await self.cache_manager.delete(tenant_bot_id_key)
                
                # Очищаем структурированные данные бота
                await self.cache_manager.delete(cache_key)
                self.logger.info(f"[Bot-{bot_id}] Кэш очищен")
            else:
                # Очищаем все ключи ботов по паттерну
                await self.cache_manager.invalidate_pattern("bot:*")
                # Очищаем все маппинги tenant -> bot_id
                await self.cache_manager.invalidate_pattern("tenant:*:bot_id")
                self.logger.info("Весь кэш ботов очищен")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")
            return False
    
    async def sync_bot_commands(self, bot_id: int, command_list: List[Dict[str, Any]]) -> bool:
        """
        Синхронизация команд бота: удаление старых → сохранение новых → обновление кэша
        """
        try:
            # Получаем мастер-репозиторий
            master_repo = self.database_manager.get_master_repository()
            
            # Удаляем все существующие команды для бота
            await master_repo.delete_commands_by_bot(bot_id)
            
            # Сохраняем новые команды
            saved_count = await master_repo.save_commands_by_bot(bot_id, command_list)
            
            # Обновляем кэш
            cache_key = self._get_bot_cache_key(bot_id)
            cached_bot_info = await self.cache_manager.get(cache_key)
            if cached_bot_info:
                cached_bot_info['bot_command'] = command_list
                await self.cache_manager.set(cache_key, cached_bot_info, ttl=self._bot_ttl)
            
            self.logger.info(f"[Bot-{bot_id}] Сохранено {saved_count} команд в БД")
            return True
            
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка синхронизации команд: {e}")
            return False
    
    async def create_or_update_bot(self, bot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создание или обновление бота: управление БД + кэшем
        """
        try:
            tenant_id = bot_data.get('tenant_id')
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id обязателен в bot_data"
                    }
                }
            
            # Получаем мастер-репозиторий
            master_repo = self.database_manager.get_master_repository()
            
            # Ищем существующего бота для этого тенанта
            existing_bot = None
            all_bots = await master_repo.get_all_bots()
            for bot in all_bots:
                if bot.get('tenant_id') == tenant_id:
                    existing_bot = bot
                    break
            
            bot_id = None
            action = None
            
            # Получаем токен из данных (может быть None если не передан из конфига)
            bot_token = bot_data.get('bot_token')
            # Нормализуем: пустые строки и строки только с пробелами превращаем в None
            # Это нужно для корректной обработки случая, когда токен не указан в конфиге
            if bot_token is not None and not bot_token.strip():
                bot_token = None
            
            # Получаем информацию о боте через Telegram API (только если токен передан)
            telegram_info = {}
            if bot_token:
                telegram_info = await self._get_telegram_bot_info(bot_token)
                    
            if existing_bot:
                # Обновляем существующего бота
                bot_id = existing_bot.get('id')
                update_data = {
                    'is_active': bot_data.get('is_active', True)
                }
                
                # Обновляем токен только если он передан (приоритет конфига)
                if bot_token is not None:
                    update_data['bot_token'] = bot_token
                
                # Добавляем данные из Telegram API (только если токен был передан и валиден)
                if telegram_info:
                    update_data.update({
                        'telegram_bot_id': telegram_info.get('telegram_bot_id'),
                        'username': telegram_info.get('username'),
                        'first_name': telegram_info.get('first_name')
                    })
                
                update_success = await master_repo.update_bot(bot_id, update_data)
                
                if not update_success:
                    return {"result": "error", "error": f"Не удалось обновить бота {bot_id}"}
                
                action = "updated"
                if bot_token is not None:
                    self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Обновлен бот (токен обновлен из конфига)")
                else:
                    self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Обновлен бот (токен из БД сохранен)")
            else:
                # Создаем нового бота (токен опционален, можно установить позже через мастер-бота)
                create_data = {
                    'tenant_id': tenant_id,
                    'bot_token': bot_token,  # Может быть None, если токен не передан
                    'is_active': bot_data.get('is_active', True)
                }
                
                # Добавляем данные из Telegram API (только если токен был передан и валиден)
                if telegram_info:
                    create_data.update({
                        'telegram_bot_id': telegram_info.get('telegram_bot_id'),
                        'username': telegram_info.get('username'),
                        'first_name': telegram_info.get('first_name')
                    })
                
                bot_id = await master_repo.create_bot(create_data)
                
                if not bot_id:
                    return {
                        "result": "error",
                        "error": {
                            "code": "INTERNAL_ERROR",
                            "message": "Не удалось создать бота"
                        }
                    }
                
                action = "created"
                self.logger.info(f"[Tenant-{tenant_id}] [Bot-{bot_id}] Создан новый бот")
            
            # Обновляем кэш - получаем свежие данные из БД
            await self.get_bot_info(bot_id, force_refresh=True)
            
            return {
                "result": "success",
                "response_data": {
                    "bot_id": bot_id,
                    "action": action
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка создания/обновления бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    # === Приватные методы ===
    
    def _format_bot_info(self, bot_data: Dict[str, Any], commands: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Формирование унифицированной структуры bot_info из данных бота и команд
        Используется для единообразия формата данных в кэше
        """
        return {
            'bot_id': bot_data.get('id'),
            'telegram_bot_id': bot_data.get('telegram_bot_id'),
            'tenant_id': bot_data.get('tenant_id'),
            'bot_token': bot_data.get('bot_token'),
            'username': bot_data.get('username'),
            'first_name': bot_data.get('first_name'),
            'is_active': bot_data.get('is_active'),
            'bot_command': commands or []
        }
    
    async def _collect_bot_info_from_db(self, bot_id: int) -> Dict[str, Any]:
        """
        Сбор всей информации о боте из базы данных
        Возвращает структуру: {'bot_info': Dict | None, 'error': Dict | None}
        - Если успех: {'bot_info': {...}, 'error': None}
        - Если NOT_FOUND: {'bot_info': None, 'error': {'type': 'NOT_FOUND'}}
        - Если INTERNAL_ERROR: {'bot_info': None, 'error': {'type': 'INTERNAL_ERROR', 'message': '...'}}
        """
        try:
            # Получаем мастер-репозиторий
            master_repo = self.database_manager.get_master_repository()
            
            # Получаем данные бота
            bot_data = await master_repo.get_bot_by_id(bot_id)
            if not bot_data:
                self.logger.warning(f"Бот {bot_id} не найден в базе данных")
                return {
                    'bot_info': None,
                    'error': {'type': 'NOT_FOUND'}
                }
            
            # Получаем команды бота
            commands = await master_repo.get_commands_by_bot(bot_id)
            
            # Формируем результат используя унифицированный метод
            bot_info = self._format_bot_info(bot_data, commands)
            return {
                'bot_info': bot_info,
                'error': None
            }
            
        except Exception as e:
            # INTERNAL_ERROR - ошибка при запросе к БД
            self.logger.error(f"[Bot-{bot_id}] Ошибка получения информации о боте из БД: {e}")
            return {
                'bot_info': None,
                'error': {
                    'type': 'INTERNAL_ERROR',
                    'message': str(e)
                }
            }
    
    async def get_bot_status(self, data: dict) -> Dict[str, Any]:
        """
        Получение статуса работы бота: пулинг ИЛИ вебхуки
        """
        try:
            bot_id = data.get('bot_id')
            if not bot_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "bot_id обязателен"
                    }
                }
            
            # Получаем информацию о боте из БД (используем кэш)
            bot_info = await self.get_bot_info(bot_id, force_refresh=False)
            is_active = bot_info.get('response_data', {}).get('is_active')
            bot_token = bot_info.get('response_data', {}).get('bot_token')
            
            # Проверяем активность пулинга
            is_polling = self.telegram_polling.is_bot_polling(bot_id)
            
            # Проверяем активность вебхука (если есть токен)
            is_webhook_active = False
            if bot_token:
                try:
                    webhook_info = await self.webhook_manager.get_webhook_info(bot_token, bot_id)
                    if webhook_info.get('result') == 'success':
                        is_webhook_active = webhook_info.get('response_data', {}).get('is_webhook_active', False)
                except Exception as e:
                    self.logger.warning(f"[Bot-{bot_id}] Ошибка проверки статуса вебхука: {e}")
            
            # Общий статус работы: пулинг ИЛИ вебхуки
            is_working = is_polling or is_webhook_active
            
            return {
                "result": "success",
                "response_data": {
                    "is_active": is_active,
                    "is_polling": is_polling,
                    "is_webhook_active": is_webhook_active,
                    "is_working": is_working
                }
            }
                
        except Exception as e:
            self.logger.error(f"[Bot-{bot_id}] Ошибка получения статуса бота: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }