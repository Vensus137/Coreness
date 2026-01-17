"""
TenantCache - подмодуль для кэширования информации о тенанте
"""

from typing import Any, Dict, Optional


class TenantCache:
    """
    Кэш для хранения информации о тенанте
    Вечный кэш, заполняется при первом запросе
    """
    
    def __init__(self, database_manager, logger, datetime_formatter, cache_manager, settings_manager):
        self.database_manager = database_manager
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        self.cache_manager = cache_manager
        
        # Получаем TTL из конфига tenant_hub
        tenant_hub_settings = settings_manager.get_plugin_settings("tenant_hub")
        self._cache_ttl = tenant_hub_settings.get('cache_ttl', 315360000)  # Вечный кэш
    
    def _get_tenant_bot_id_key(self, tenant_id: int) -> str:
        """Генерация ключа кэша для маппинга tenant_id -> bot_id"""
        return f"tenant:{tenant_id}:bot_id"
    
    def _get_bot_cache_key(self, bot_id: int) -> str:
        """Генерация ключа кэша для структурированных данных бота по bot_id"""
        return f"bot:{bot_id}"
    
    def _get_tenant_meta_cache_key(self, tenant_id: int) -> str:
        """Генерация ключа кэша для метаданных тенанта"""
        return f"tenant:{tenant_id}:meta"
    
    def _get_tenant_config_key(self, tenant_id: int) -> str:
        """Генерация ключа кэша для конфига тенанта"""
        return f"tenant:{tenant_id}:config"
    
    async def get_bot_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о боте по tenant_id
        Всегда возвращает структурированные данные с полем 'bot_id'
        Использует маппинг tenant:{tenant_id}:bot_id и структурированные данные bot:{bot_id}
        """
        try:
            # Шаг 1: Получаем bot_id из маппинга
            tenant_bot_id_key = self._get_tenant_bot_id_key(tenant_id)
            cached_bot_id = await self.cache_manager.get(tenant_bot_id_key)
            
            bot_id = None
            bot_data = None
            
            if cached_bot_id:
                # Маппинг есть в кэше
                bot_id = cached_bot_id
            else:
                # Маппинга нет - получаем из БД
                master_repo = self.database_manager.get_master_repository()
                bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
                
                if not bot_data:
                    self.logger.warning(f"[Tenant-{tenant_id}] Бот не найден в БД")
                    return None
                
                bot_id = bot_data.get('id')
                if not bot_id:
                    self.logger.warning(f"[Tenant-{tenant_id}] Бот найден, но bot_id отсутствует")
                    return None
                
                # Сохраняем маппинг в кэш
                await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=self._cache_ttl)
            
            # Шаг 2: Пытаемся получить структурированные данные из bot:{bot_id}
            bot_cache_key = self._get_bot_cache_key(bot_id)
            structured_bot_info = await self.cache_manager.get(bot_cache_key)
            
            if structured_bot_info:
                # Есть структурированные данные - возвращаем их
                return structured_bot_info
            
            # Шаг 3: Структурированных данных нет - создаем их из сырых данных БД
            if not bot_data:
                master_repo = self.database_manager.get_master_repository()
                bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
                if not bot_data:
                    return None
            
            # Получаем команды бота
            master_repo = self.database_manager.get_master_repository()
            commands = await master_repo.get_commands_by_bot(bot_id)
            
            # Формируем структурированные данные (как в BotInfoManager._format_bot_info)
            structured_bot_info = {
                'bot_id': bot_data.get('id'),
                'telegram_bot_id': bot_data.get('telegram_bot_id'),
                'tenant_id': bot_data.get('tenant_id'),
                'bot_token': bot_data.get('bot_token'),
                'username': bot_data.get('username'),
                'first_name': bot_data.get('first_name'),
                'is_active': bot_data.get('is_active'),
                'bot_command': commands or []
            }
            
            # Сохраняем структурированные данные в кэш
            await self.cache_manager.set(bot_cache_key, structured_bot_info, ttl=self._cache_ttl)
            
            return structured_bot_info
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения данных о боте: {e}")
            return None
    
    async def get_bot_id_by_tenant_id(self, tenant_id: int) -> Optional[int]:
        """
        Получение только bot_id по tenant_id
        """
        bot_data = await self.get_bot_by_tenant_id(tenant_id)
        if not bot_data:
            return None
        # Всегда структурированные данные с 'bot_id'
        return bot_data.get('bot_id')
    
    async def invalidate_bot_cache(self, tenant_id: int):
        """
        Инвалидация кэша бота для указанного tenant_id
        Удаляет маппинг tenant:{tenant_id}:bot_id
        """
        tenant_bot_id_key = self._get_tenant_bot_id_key(tenant_id)
        await self.cache_manager.delete(tenant_bot_id_key)
    
    async def clear_bot_cache(self):
        """
        Очистка кэша маппингов tenant -> bot_id
        """
        await self.cache_manager.invalidate_pattern("tenant:*:bot_id")

    # === In-memory данные о тенанте ===
    async def set_last_updated(self, tenant_id: int) -> None:
        cache_key = self._get_tenant_meta_cache_key(tenant_id)
        meta = await self.cache_manager.get(cache_key) or {}
        now_tz = await self.datetime_formatter.now_local_tz()
        meta['last_updated_at'] = await self.datetime_formatter.to_string(now_tz)
        meta.pop('last_error', None)
        meta.pop('last_failed_at', None)
        await self.cache_manager.set(cache_key, meta, ttl=self._cache_ttl)

    async def set_last_failed(self, tenant_id: int, error: dict) -> None:
        """
        Сохранение ошибки в кэш тенанта
        Ожидает объект ошибки с полями: code, message, details (опционально)
        """
        cache_key = self._get_tenant_meta_cache_key(tenant_id)
        meta = await self.cache_manager.get(cache_key) or {}
        now_tz = await self.datetime_formatter.now_local_tz()
        meta['last_failed_at'] = await self.datetime_formatter.to_string(now_tz)
        # Сохраняем весь объект ошибки для доступа через плейсхолдеры ({last_error.message}, {last_error.code})
        meta['last_error'] = error
        await self.cache_manager.set(cache_key, meta, ttl=self._cache_ttl)

    async def get_tenant_cache(self, tenant_id: int) -> Dict[str, Any]:
        cache_key = self._get_tenant_meta_cache_key(tenant_id)
        return await self.cache_manager.get(cache_key) or {}
    
    async def get_tenant_config(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение конфига тенанта с кэшированием
        Возвращает словарь с конфигом (например, {"ai_token": "..."})
        """
        try:
            # Шаг 1: Проверяем кэш
            cache_key = self._get_tenant_config_key(tenant_id)
            cached_config = await self.cache_manager.get(cache_key)
            
            if cached_config is not None:
                return cached_config
            
            # Шаг 2: Кэша нет - получаем из БД
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            
            if not tenant_data:
                return None
            
            # Формируем словарь конфига из всех полей БД (исключаем служебные)
            # Служебные поля: id, processed_at (и relationship поля, но они не попадают в словарь)
            config = {}
            excluded_fields = {'id', 'processed_at'}
            for key, value in tenant_data.items():
                if key not in excluded_fields and value is not None:
                    config[key] = value
            
            # Сохраняем в кэш (даже если пустой, чтобы не запрашивать БД каждый раз)
            await self.cache_manager.set(cache_key, config, ttl=self._cache_ttl)
            
            return config
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения конфига тенанта: {e}")
            return None
    
    async def update_tenant_config_cache(self, tenant_id: int) -> None:
        """
        Обновление кэша конфига тенанта из БД
        Получает актуальные данные из БД и сохраняет в кэш
        Используется после обновления конфига в БД для синхронизации кэша
        """
        try:
            # Получаем данные из БД
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            
            if not tenant_data:
                # Тенант не найден - удаляем кэш
                cache_key = self._get_tenant_config_key(tenant_id)
                await self.cache_manager.delete(cache_key)
                return
            
            # Формируем словарь конфига из всех полей БД (исключаем служебные)
            config = {}
            excluded_fields = {'id', 'processed_at'}
            for key, value in tenant_data.items():
                if key not in excluded_fields and value is not None:
                    config[key] = value
            
            # Обновляем кэш (перезаписываем актуальными данными)
            cache_key = self._get_tenant_config_key(tenant_id)
            await self.cache_manager.set(cache_key, config, ttl=self._cache_ttl)
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка обновления кэша конфига тенанта: {e}")

