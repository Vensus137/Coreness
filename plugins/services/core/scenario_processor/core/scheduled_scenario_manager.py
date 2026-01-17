"""
Модуль для управления scheduled сценариями
- Кэширование метаданных scheduled сценариев
- Фоновый цикл проверки и запуска
- Обновление метаданных после выполнения
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional


class ScheduledScenarioManager:
    """
    Менеджер для управления scheduled сценариями
    - Кэширует метаданные scheduled сценариев
    - Проверяет расписание и запускает сценарии
    - Обновляет метаданные после выполнения
    """
    
    def __init__(self, scenario_engine, data_loader, scheduler, logger, datetime_formatter, database_manager, task_manager, cache_manager):
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        self.database_manager = database_manager
        self.task_manager = task_manager
        self.cache_manager = cache_manager
        
        self.scenario_engine = scenario_engine
        self.data_loader = data_loader
        self.scheduler = scheduler
        
        # Кэш метаданных scheduled сценариев
        # {scenario_id: {'cron': str, 'last_run': datetime | None, 'next_run': datetime, 'tenant_id': int, 'scenario_name': str, 'is_running': bool}}
        self._scheduled_metadata: Dict[int, Dict[str, Any]] = {}
        
        # Состояние сервиса
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None
    
    async def run(self):
        """Основной цикл работы менеджера scheduled сценариев"""
        try:
            self.is_running = True
            
            # Загружаем все scheduled сценарии при старте
            await self.load_all_scheduled_scenarios()
            
            # Запускаем фоновый цикл проверки scheduled сценариев
            self._scheduler_task = asyncio.create_task(self._run_scheduler_loop())
            await self._scheduler_task
            
        except asyncio.CancelledError:
            self.logger.info("ScheduledScenarioManager остановлен")
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле ScheduledScenarioManager: {e}")
        finally:
            self.is_running = False
    
    def shutdown(self):
        """Синхронный graceful shutdown менеджера"""
        if not self.is_running:
            return
        
        self.logger.info("Останавливаем ScheduledScenarioManager...")
        self.is_running = False
        
        # Отменяем фоновый цикл если он запущен
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
        
        self.logger.info("ScheduledScenarioManager остановлен")
    
    async def load_all_scheduled_scenarios(self):
        """Загрузка всех scheduled сценариев при старте сервиса"""
        try:
            # Загружаем все scheduled сценарии (без фильтра по tenant)
            scheduled_scenarios = await self.data_loader.load_scheduled_scenarios()
            
            # Обрабатываем загруженные сценарии напрямую
            loaded_count = 0
            tenants_count = set()
            
            for scenario in scheduled_scenarios:
                scenario_id = scenario['id']
                cron = scenario['schedule']
                last_run = scenario.get('last_scheduled_run')
                tenant_id = scenario['tenant_id']
                
                tenants_count.add(tenant_id)
                
                # Вычисляем next_run
                if last_run:
                    next_run = await self.scheduler.get_next_run_time(cron, last_run)
                else:
                    # Если не было запусков - от текущего локального времени
                    now = await self.datetime_formatter.now_local()
                    next_run = await self.scheduler.get_next_run_time(cron, now)
                
                if next_run is None:
                    self.logger.warning(f"Не удалось вычислить next_run для сценария {scenario_id} с cron '{cron}'")
                    continue
                
                # Обновляем кэш (bot_id получаем при запуске из БД)
                self._scheduled_metadata[scenario_id] = {
                    'cron': cron,
                    'last_run': last_run,
                    'next_run': next_run,
                    'tenant_id': tenant_id,
                    'scenario_name': scenario['scenario_name'],
                    'is_running': False
                }
                loaded_count += 1
            
            if loaded_count > 0:
                self.logger.info(f"Загружено ({loaded_count} scheduled сценариев) для ({len(tenants_count)} tenant'ов)")
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки всех scheduled сценариев при старте: {e}")
    
    async def reload_scheduled_metadata(self, tenant_id: int) -> bool:
        """
        Перезагрузка метаданных scheduled сценариев для tenant
        """
        try:
            # Удаляем все старые scenario_id для этого tenant_id из кэша
            for sid in list(self._scheduled_metadata.keys()):
                if self._scheduled_metadata[sid]['tenant_id'] == tenant_id:
                    del self._scheduled_metadata[sid]
            
            # Загружаем все scheduled сценарии из БД для tenant
            scheduled_scenarios = await self.data_loader.load_scheduled_scenarios(tenant_id)
            
            loaded_count = 0
            for scenario in scheduled_scenarios:
                scenario_id = scenario['id']
                cron = scenario['schedule']
                last_run = scenario.get('last_scheduled_run')
                
                # Вычисляем next_run
                if last_run:
                    next_run = await self.scheduler.get_next_run_time(cron, last_run)
                else:
                    # Если не было запусков - от текущего локального времени
                    now = await self.datetime_formatter.now_local()
                    next_run = await self.scheduler.get_next_run_time(cron, now)
                
                if next_run is None:
                    self.logger.warning(f"Не удалось вычислить next_run для сценария {scenario_id} с cron '{cron}'")
                    continue
                
                # Обновляем кэш (bot_id получаем при запуске из БД)
                self._scheduled_metadata[scenario_id] = {
                    'cron': cron,
                    'last_run': last_run,
                    'next_run': next_run,
                    'tenant_id': scenario['tenant_id'],
                    'scenario_name': scenario['scenario_name'],
                    'is_running': False
                }
                loaded_count += 1
            
            self.logger.info(f"[Tenant-{tenant_id}] Загружено ({loaded_count} scheduled сценариев)")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка перезагрузки scheduled метаданных для tenant {tenant_id}: {e}")
            return False
    
    async def _run_scheduler_loop(self):
        """Фоновый цикл проверки scheduled сценариев"""
        while True:
            try:
                await self._check_scheduled_scenarios()
                
                # Ждем до начала следующей минуты
                now = await self.datetime_formatter.now_local()
                seconds_to_wait = 60 - now.second
                await asyncio.sleep(seconds_to_wait)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduler loop остановлен")
                break
            except Exception as e:
                self.logger.error(f"Ошибка в scheduler loop: {e}")
                await asyncio.sleep(60)
    
    async def _check_scheduled_scenarios(self):
        """Проверка и запуск scheduled сценариев"""
        try:
            # Получаем текущее локальное время
            now = await self.datetime_formatter.now_local()
            
            # Округляем до начала минуты для точности
            now = now.replace(second=0, microsecond=0)
            
            # Фильтруем сценарии которые нужно запустить
            scenarios_to_run = []
            
            for scenario_id, metadata in self._scheduled_metadata.items():
                # Проверяем по next_run (быстрее чем проверять cron каждый раз)
                # И проверяем что сценарий не выполняется уже
                if metadata['next_run'] <= now and not metadata.get('is_running', False):
                    scenarios_to_run.append({
                        'scenario_id': scenario_id,
                        **metadata
                    })
            
            # Запускаем найденные сценарии через TaskManager
            # Используем очередь action для scheduled сценариев
            for scenario_info in scenarios_to_run:
                scenario_id = scenario_info['scenario_id']
                
                # Создаем async-обертку для TaskManager (как в ActionRegistry._create_action_wrapper)
                # Фиксируем scenario_info через параметр по умолчанию (вычисляется при создании функции)
                async def scenario_wrapper(sc_info=scenario_info):
                    await self._run_scheduled_scenario(sc_info)
                
                # Отправляем в очередь action с fire_and_forget=True
                asyncio.create_task(
                    self.task_manager.submit_task(
                        task_id=f"scheduled_scenario_{scenario_id}",
                        coro=scenario_wrapper,
                        queue_name='action',
                        fire_and_forget=True
                    )
                )
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки scheduled сценариев: {e}")
    
    async def _run_scheduled_scenario(self, scenario_info: Dict[str, Any]):
        """Запуск scheduled сценария"""
        scenario_id = scenario_info['scenario_id']
        tenant_id = scenario_info['tenant_id']
        scenario_name = scenario_info['scenario_name']
        cron = scenario_info['cron']
        
        # Проверяем еще раз что сценарий не выполняется (race condition защита)
        if self._scheduled_metadata.get(scenario_id, {}).get('is_running', False):
            return
        
        # Помечаем сценарий как выполняющийся
        self._scheduled_metadata[scenario_id]['is_running'] = True
        
        try:
            # Создаем синтетическое событие для scheduled сценария
            scheduled_at = await self.datetime_formatter.now_local()
            
            # Получаем bot_id через cache_manager (как в TenantCache)
            # Шаг 1: Пытаемся получить bot_id из маппинга tenant:{tenant_id}:bot_id
            tenant_bot_id_key = f"tenant:{tenant_id}:bot_id"
            cached_bot_id = await self.cache_manager.get(tenant_bot_id_key)
            
            bot_id = None
            if cached_bot_id:
                # Маппинг есть в кэше
                bot_id = cached_bot_id
            else:
                # Маппинга нет - получаем из БД
                master_repo = self.database_manager.get_master_repository()
                bot_data = await master_repo.get_bot_by_tenant_id(tenant_id)
                if not bot_data:
                    self.logger.error(f"[Tenant-{tenant_id}] Бот не найден для scheduled сценария '{scenario_name}' (ID: {scenario_id})")
                    return
                # Сырые данные из БД используют 'id'
                bot_id = bot_data.get('id')
                if not bot_id:
                    self.logger.error(f"[Tenant-{tenant_id}] Бот найден, но bot_id отсутствует для scheduled сценария '{scenario_name}' (ID: {scenario_id})")
                    return
                # Сохраняем маппинг в кэш (TTL берем из настроек, но для простоты используем большой TTL)
                await self.cache_manager.set(tenant_bot_id_key, bot_id, ttl=315360000)
            
            if not bot_id:
                self.logger.error(f"[Tenant-{tenant_id}] Не удалось получить bot_id для scheduled сценария '{scenario_name}' (ID: {scenario_id})")
                return
            
            if not bot_id:
                self.logger.error(f"[Tenant-{tenant_id}] Не удалось получить bot_id для scheduled сценария '{scenario_name}' (ID: {scenario_id})")
                return
            
            # Получаем конфиг тенанта из общего кэша с fallback на БД
            cache_key = f"tenant:{tenant_id}:config"
            tenant_config = await self.cache_manager.get(cache_key)
            
            # Если кэша нет - загружаем из БД (fallback для решения проблемы рассинхрона)
            if tenant_config is None:
                self.logger.warning(f"[Tenant-{tenant_id}] Конфиг тенанта не найден в кэше для scheduled сценария '{scenario_name}', загружаем из БД")
                
                try:
                    master_repo = self.database_manager.get_master_repository()
                    tenant_data = await master_repo.get_tenant_by_id(tenant_id)
                    
                    if tenant_data:
                        # Формируем словарь конфига из всех полей БД (исключаем служебные)
                        config = {}
                        excluded_fields = {'id', 'processed_at'}
                        for key, value in tenant_data.items():
                            if key not in excluded_fields and value is not None:
                                config[key] = value
                        
                        # Не сохраняем в кэш - им управляет TenantCache
                        # Это редкий кейс, когда кэша нет, поэтому просто возвращаем данные из БД
                        tenant_config = config
                except Exception as e:
                    self.logger.error(f"[Tenant-{tenant_id}] Ошибка загрузки конфига тенанта из БД для scheduled сценария '{scenario_name}': {e}")
            
            # Формируем системные поля (как в обычных событиях)
            system_fields = {
                'tenant_id': tenant_id,
                'bot_id': bot_id
            }
            
            # Преобразуем scheduled_at в ISO строку локального времени
            scheduled_at_iso = await self.datetime_formatter.to_iso_local_string(scheduled_at)
            
            synthetic_event = {
                'system': system_fields,
                'tenant_id': tenant_id,
                'bot_id': bot_id,
                'scheduled_at': scheduled_at_iso,  # ISO формат локального времени
                'scheduled_scenario_id': scenario_id,
                'scheduled_scenario_name': scenario_name
            }
            
            # Добавляем конфиг тенанта в событие (если есть)
            if tenant_config:
                synthetic_event['_config'] = tenant_config
            
            # Запускаем через scenario_engine.execute_scenario_by_name
            result, _ = await self.scenario_engine._execute_scenario_by_name(
                tenant_id=tenant_id,
                scenario_name=scenario_name,
                data=synthetic_event
            )
            
            # Получаем время окончания выполнения
            completion_time = await self.datetime_formatter.now_local()
            
            # Логируем ошибку если была, но продолжаем обновление метаданных
            if result == 'error':
                self.logger.warning(f"[Tenant-{tenant_id}] Ошибка выполнения scheduled сценария '{scenario_name}' (ID: {scenario_id})")
            
            # Обновляем last_run всегда (и в кэше, и в БД) - запуск был, независимо от результата
            # Это гарантирует предсказуемое поведение при перезапуске сервиса
            self._scheduled_metadata[scenario_id]['last_run'] = scheduled_at
            await self._update_last_run_in_db(scenario_id, scheduled_at)
            
            # Вычисляем next_run от момента окончания выполнения (стандартное поведение cron)
            # Пропущенные запуски просто пропускаются, следующий будет в будущем
            # Обновляем всегда, даже при ошибке, чтобы избежать повторных запусков
            next_run = await self.scheduler.get_next_run_time(cron, completion_time)
            if next_run:
                self._scheduled_metadata[scenario_id]['next_run'] = next_run
            else:
                self.logger.warning(f"Не удалось вычислить next_run для сценария {scenario_id}")
                
        except Exception as e:
            self.logger.error(f"Ошибка запуска scheduled сценария {scenario_id}: {e}")
        finally:
            # Снимаем флаг выполнения
            self._scheduled_metadata[scenario_id]['is_running'] = False
    
    async def _update_last_run_in_db(self, scenario_id: int, last_run: datetime):
        """Обновление last_scheduled_run в БД"""
        try:
            master_repo = self.database_manager.get_master_repository()
            await master_repo.update_scenario_last_run(scenario_id, last_run)
        except Exception as e:
            self.logger.error(f"Ошибка обновления last_scheduled_run для сценария {scenario_id}: {e}")

