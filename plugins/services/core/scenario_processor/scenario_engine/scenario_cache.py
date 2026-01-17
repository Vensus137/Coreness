"""
Кэш сценариев по tenant'ам
Управляет кэшированием сценариев и получением метаданных для изоляции обработки событий
"""

from typing import Any, Dict, Optional


class ScenarioCache:
    """
    Кэш сценариев по tenant'ам
    - Хранение сценариев в памяти через cache_manager
    - Получение метаданных сценариев для изоляции обработки событий
    - Перезагрузка кэша для конкретного tenant'а
    """
    
    def __init__(self, logger, cache_manager, settings_manager):
        self.logger = logger
        self.cache_manager = cache_manager
        
        # Получаем TTL из конфига scenario_processor
        scenario_settings = settings_manager.get_plugin_settings("scenario_processor")
        self._scenarios_ttl = scenario_settings.get('cache_ttl', 315360000)  # Вечный кэш
    
    def _get_cache_key(self, tenant_id: int) -> str:
        """Генерация ключа кэша в формате cache_manager"""
        return f"tenant:{tenant_id}:scenarios"
    
    async def get_scenario_metadata(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Получение метаданных сценариев тенанта для изоляции обработки события"""
        try:
            cache_key = self._get_cache_key(tenant_id)
            original_cache = await self.cache_manager.get(cache_key)
            
            if original_cache is None:
                return None
            
            # Используем ссылки на все структуры (не копируем)
            # Безопасно, т.к. все структуры только читаются во время выполнения сценариев
            # Изменения происходят только при reload_tenant_scenarios, который удаляет старый кэш
            # Ссылки остаются валидными до завершения обработки события (GC удалит старый кэш после)
            metadata = {
                'search_tree': original_cache['search_tree'],  # Ссылка
                'scenario_index': original_cache['scenario_index'],  # Ссылка
                'scenario_name_index': original_cache['scenario_name_index']  # Ссылка
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Ошибка получения метаданных сценариев для tenant {tenant_id}: {e}")
            return None
    
    async def get_tenant_cache(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Получение кэша для tenant'а"""
        cache_key = self._get_cache_key(tenant_id)
        return await self.cache_manager.get(cache_key)
    
    async def set_tenant_cache(self, tenant_id: int, cache: Dict[str, Any]) -> None:
        """Установка кэша для tenant'а"""
        cache_key = self._get_cache_key(tenant_id)
        await self.cache_manager.set(cache_key, cache, ttl=self._scenarios_ttl)
    
    async def has_tenant_cache(self, tenant_id: int) -> bool:
        """Проверка наличия кэша для tenant'а"""
        cache_key = self._get_cache_key(tenant_id)
        return await self.cache_manager.exists(cache_key)
    
    async def reload_tenant_scenarios(self, tenant_id: int) -> bool:
        """Перезагрузка кэша сценариев для конкретного tenant'а. Удаляет старый кэш"""
        try:
            # Очищаем кэш для конкретного tenant'а
            cache_key = self._get_cache_key(tenant_id)
            await self.cache_manager.delete(cache_key)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка перезагрузки сценариев для tenant {tenant_id}: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Очистка всех ресурсов"""
        try:
            # Очищаем кэш сценариев по паттерну
            await self.cache_manager.invalidate_pattern("tenant:*:scenarios")
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки: {e}")

