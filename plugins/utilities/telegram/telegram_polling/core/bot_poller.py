"""
BotPoller - индивидуальный пулинг для одного бота
"""

import asyncio
from typing import Callable, Optional

import aiohttp


class BotPoller:
    """
    Простой пулинг для одного бота без метрик и health check
    """
    
    def __init__(self, bot_id: int, token: str, settings: dict, logger, datetime_formatter):
        self.bot_id = bot_id
        self.token = token
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        
        # Настройки пулинга (стандартные для Telegram Bot API)
        self.polling_timeout = settings.get('polling_timeout', 20)
        self.polling_relax = settings.get('polling_relax', 0.1)
        self.polling_limit = settings.get('polling_limit', 100)
        self.polling_start_delay = settings.get('polling_start_delay', 0.5)
        self.allowed_updates = settings.get('allowed_updates', ['message', 'callback_query'])
        
        # Retry настройки
        self.retry_delay = settings.get('retry_delay', 5)
        self.retry_after_rate_limit = settings.get('retry_after_rate_limit', 30)
        
        # HTTP клиент
        self.request_timeout = settings.get('request_timeout', 35)
        
        # Таймауты остановки пулинга
        self.stop_polling_timeout = settings.get('stop_polling_timeout', 2.0)
        self.session_close_timeout = settings.get('session_close_timeout', 0.5)
        
        # Состояние
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        self.offset = 0
        
        # Время запуска пуллинга для фильтрации событий
        self.polling_start_time = None
        
        # Callback для событий
        self.event_callback: Optional[Callable] = None
        
        # Задача основного цикла пулинга
        self._polling_task: Optional[asyncio.Task] = None
        
        # Счетчик критических ошибок
        self.consecutive_critical_errors = 0
        self.max_critical_errors = settings.get('max_critical_errors', 3)
        self.critical_error_codes = settings.get('critical_error_codes', [401, 403])
    
    async def reset_bot_settings(self):
        """
        КРИТИЧЕСКИ ВАЖНО: Сброс настроек бота и установка allowed_updates для пулинга
        
        Telegram кэширует настройки allowed_updates из предыдущих вебхуков.
        Без явной установки через setWebhook с пустым URL мы можем не получать
        нужные события (например, pre_checkout_query) даже если передаем их в getUpdates.
        
        Этот метод должен вызываться ОДИН РАЗ при первом запуске бота, а не при каждом перезапуске пулинга.
        """
        try:
            api_url = f"https://api.telegram.org/bot{self.token}"
            
            self.logger.info(f"[Bot-{self.bot_id}] 🔄 Установка allowed_updates для пулинга: {self.allowed_updates}")
            
            # Создаем временную сессию для сброса настроек
            async with aiohttp.ClientSession() as session:
                # 1. Удаляем вебхук БЕЗ drop_pending_updates, чтобы сохранить накопленные обновления
                delete_url = f"{api_url}/deleteWebhook"
                async with session.post(delete_url, json={}) as response:
                    data = await response.json()
                    if not data.get('ok'):
                        self.logger.warning(f"[Bot-{self.bot_id}] Предупреждение при удалении вебхука: {data.get('description', 'Неизвестная ошибка')}")
                
                # 2. Устанавливаем allowed_updates через setWebhook с пустым URL
                # Это устанавливает allowed_updates для режима getUpdates
                # КРИТИЧЕСКИ ВАЖНО: без этого Telegram может игнорировать allowed_updates в getUpdates
                set_webhook_url = f"{api_url}/setWebhook"
                payload = {
                    "url": "",  # Пустой URL отключит webhook и активирует getUpdates
                    "allowed_updates": self.allowed_updates
                }
                async with session.post(set_webhook_url, json=payload) as response:
                    data = await response.json()
                    if data.get('ok'):
                        self.logger.info(f"[Bot-{self.bot_id}] ✅ allowed_updates установлены: {self.allowed_updates}")
                    else:
                        error_msg = data.get('description', 'Неизвестная ошибка')
                        self.logger.error(f"[Bot-{self.bot_id}] ❌ ОШИБКА установки allowed_updates: {error_msg}")
                        # Это критично - без правильных allowed_updates мы можем не получать события
                        raise Exception(f"Не удалось установить allowed_updates: {error_msg}")
                        
        except Exception as e:
            # Это критично - без правильных настроек мы можем не получать события
            self.logger.error(f"[Bot-{self.bot_id}] ❌ КРИТИЧЕСКАЯ ОШИБКА при установке allowed_updates: {e}")
            # Продолжаем работу, но логируем как критическую ошибку
            raise
    
    async def start_polling(self, event_callback: Callable):
        """
        Запуск пулинга для этого бота
        """
        try:
            # Сохраняем callback
            self.event_callback = event_callback
            
            # Устанавливаем время запуска пуллинга
            self.polling_start_time = await self.datetime_formatter.now_local()
            
            # Сбрасываем счетчик критических ошибок при запуске
            self.consecutive_critical_errors = 0
            
            # Создаем HTTP сессию
            self.session = await self._create_session()
            
            # Сразу помечаем как запущенный (защита от race condition)
            self.is_running = True
            
            # Задержка запуска для предотвращения конфликтов
            start_delay = self.polling_start_delay
            if start_delay > 0:
                await asyncio.sleep(start_delay)
            
            # Запускаем основной цикл пулинга в отдельной задаче
            self._polling_task = asyncio.create_task(self._polling_loop())
            
            # Ждем завершения задачи
            await self._polling_task
            
        except Exception as e:
            self.logger.error(f"[Bot-{self.bot_id}] Ошибка запуска пулинга: {e}")
            await self.stop_polling()
            raise
    
    def _handle_network_error(self, error: Exception, context: str):
        """Обработка сетевых ошибок с детальным логированием"""
        error_str = str(error)
        if "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in error_str:
            # Это ошибка при перезапуске - логируем как warning
            self.logger.warning(f"[Bot-{self.bot_id}] SSL соединение закрыто при {context} (race condition)")
        elif "Errno 1" in error_str:
            # Errno 1 - операция запрещена, обычно при закрытии соединения
            self.logger.warning(f"[Bot-{self.bot_id}] Соединение закрыто системой при {context} (race condition)")
        else:
            # Другие сетевые ошибки - логируем как warning
            self.logger.warning(f"[Bot-{self.bot_id}] Сетевая ошибка при {context}: {error}")
    
    def _handle_critical_error(self, error_code: int, description: str):
        """Обработка критических ошибок с автоматическим отключением пулинга"""
        self.consecutive_critical_errors += 1
        
        if self.consecutive_critical_errors >= self.max_critical_errors:
            self.logger.error(f"[Bot-{self.bot_id}] Критическая ошибка HTTP {error_code}: {description}, пулинг остановлен после {self.consecutive_critical_errors} попыток")
            # Отключаем пулинг ДО выброса исключения
            self.is_running = False

    async def _create_session(self) -> aiohttp.ClientSession:
        """Создание новой HTTP сессии"""
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        return aiohttp.ClientSession(timeout=timeout)
    
    async def _recreate_session(self):
        """Пересоздание сессии после сетевых ошибок"""
        if self.session:
            try:
                if not self.session.closed:
                    await self._close_session_safely(self.session)
            except Exception as e:
                # Логируем только если произошла неожиданная ошибка при закрытии
                self.logger.warning(f"[Bot-{self.bot_id}] Ошибка при закрытии старой сессии перед пересозданием: {e}")
            finally:
                self.session = None
        
        # Создаем новую сессию (всегда создаем новую, даже если старая не закрылась)
        try:
            self.session = await self._create_session()
        except Exception as e:
            # Не удалось создать новую сессию - это критично
            self.logger.error(f"[Bot-{self.bot_id}] Критическая ошибка: не удалось создать новую сессию: {e}")
            raise

    async def _close_session_safely(self, session, timeout=None):
        """Безопасное закрытие сессии с обработкой ошибок"""
        if timeout is None:
            timeout = self.session_close_timeout
        
        # Проверяем, не закрыта ли уже сессия
        if session.closed:
            return
            
        # Пытаемся закрыть сессию
        try:
            await asyncio.wait_for(session.close(), timeout=timeout)
            return  # Успешно закрыли
        except asyncio.TimeoutError:
            # Сессия не закрылась в срок, пытаемся закрыть коннектор
            pass
        except Exception:
            # Ошибка при закрытии, пытаемся закрыть коннектор
            pass
        
        # Если сессия не закрылась, пытаемся закрыть коннектор принудительно
        if hasattr(session, '_connector') and session._connector:
            try:
                if not session._connector._closed:
                    session._connector.close()
                    return  # Коннектор закрыт, проблема решена
            except Exception:
                pass  # Коннектор тоже не закрылся, проблема не решена
        
        # Не удалось закрыть ни сессию, ни коннектор - логируем
        self.logger.warning(f"[Bot-{self.bot_id}] Не удалось закрыть сессию и коннектор")

    def stop_polling_sync(self):
        """Синхронная остановка пулинга (для shutdown)"""
        try:
            self.is_running = False
            
            if self.session and not self.session.closed:
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(self._close_session_safely(self.session))
                    loop.run_until_complete(task)
                except RuntimeError:
                    # Если нет event loop - создаем новый
                    asyncio.run(self._close_session_safely(self.session))
                
                self.session = None
            
            self.logger.info(f"[Bot-{self.bot_id}] Пулинг остановлен")
            
        except Exception as e:
            self.logger.error(f"[Bot-{self.bot_id}] Ошибка синхронной остановки пулинга: {e}")

    async def stop_polling(self):
        """Остановка пулинга"""
        try:
            self.is_running = False
            
            # Закрываем сессию ПЕРЕД ожиданием завершения задачи, чтобы избежать создания новых сессий
            if self.session:
                await self._close_session_safely(self.session)
                self.session = None
            
            # Ждем завершения основного цикла пулинга
            if hasattr(self, '_polling_task') and self._polling_task and not self._polling_task.done():
                try:
                    await asyncio.wait_for(self._polling_task, timeout=self.stop_polling_timeout)
                except asyncio.TimeoutError:
                    self.logger.warning(f"[Bot-{self.bot_id}] Пулинг не остановился за {self.stop_polling_timeout} секунд, принудительное завершение")
                    # Принудительно отменяем задачу
                    self._polling_task.cancel()
                    try:
                        await self._polling_task
                    except asyncio.CancelledError:
                        pass
                except Exception as e:
                    self.logger.warning(f"[Bot-{self.bot_id}] Ошибка при ожидании завершения пулинга: {e}")
            
            # КРИТИЧНО: После завершения задачи еще раз проверяем и закрываем сессию
            # Это нужно, потому что в _polling_loop может быть создана новая сессия через _recreate_session()
            if self.session and not self.session.closed:
                try:
                    await self._close_session_safely(self.session)
                except Exception as e:
                    self.logger.warning(f"[Bot-{self.bot_id}] Ошибка при финальном закрытии сессии: {e}")
                finally:
                    self.session = None
            
            self.logger.info(f"[Bot-{self.bot_id}] Пулинг остановлен")
            
        except Exception as e:
            self.logger.error(f"[Bot-{self.bot_id}] Ошибка остановки пулинга: {e}")
    
    async def _polling_loop(self):
        """Основной цикл пулинга"""
        while self.is_running:
            try:
                # Получаем обновления
                updates = await self._get_updates()
                
                # Обрабатываем каждое обновление
                for update in updates:
                    self.offset = update['update_id'] + 1
                    
                    # Добавляем системные данные с временем запуска пуллинга
                    if 'system' not in update:
                        update['system'] = {}
                    
                    update['system'].update({
                        'bot_id': self.bot_id,
                        'polling_start_time': self.polling_start_time
                    })
                    
                    # Передаем событие в callback
                    if self.event_callback:
                        try:
                            if asyncio.iscoroutinefunction(self.event_callback):
                                await self.event_callback(update)
                            else:
                                self.event_callback(update)
                        except Exception as e:
                            self.logger.error(f"[Bot-{self.bot_id}] Ошибка обработки события: {e}")
                            # Продолжаем обработку других событий
                
                # Задержка между запросами (стандартная для Telegram Bot API)
                if self.is_running:
                    try:
                        await asyncio.sleep(self.polling_relax)
                    except asyncio.CancelledError:
                        self.logger.info(f"[Bot-{self.bot_id}] Получен сигнал отмены во время задержки")
                        break
                
            except asyncio.CancelledError:
                self.logger.info(f"[Bot-{self.bot_id}] Получен сигнал отмены, завершаем пулинг")
                break
                
            except aiohttp.ClientError as e:
                # Обрабатываем сетевые ошибки
                self._handle_network_error(e, "получении обновлений")
                
                # Пересоздаем сессию после сетевой ошибки
                try:
                    await self._recreate_session()
                except Exception as recreate_error:
                    self.logger.warning(f"[Bot-{self.bot_id}] Ошибка пересоздания сессии: {recreate_error}")
                    # Продолжаем работу, возможно сессия все еще рабочая
                
                # Ждем перед повторной попыткой
                if self.is_running:
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                # Не логируем критические ошибки здесь - они логируются в _handle_critical_error при достижении лимита
                error_msg = str(e)
                if not error_msg.startswith("Critical error"):
                    # Проверяем, что ошибка не пустая и содержит информацию
                    if error_msg:
                        self.logger.error(f"[Bot-{self.bot_id}] Неожиданная ошибка в пулинге: {error_msg}")
                    else:
                        # Если ошибка пустая, выводим тип исключения
                        exception_type = type(e).__name__
                        self.logger.error(f"[Bot-{self.bot_id}] Неожиданная ошибка в пулинге ({exception_type}): {repr(e)}")
                
                # Если пулинг отключен из-за критических ошибок, не ждем
                if not self.is_running:
                    break
                # Ждем перед повторной попыткой только если пулинг еще активен
                if self.is_running:
                    await asyncio.sleep(self.retry_delay)
    
    async def _get_updates(self):
        """Получение обновлений через Telegram API с фильтрацией"""
        try:
            # Проверяем состояние сессии перед использованием
            if not self.session or self.session.closed:
                self.session = await self._create_session()
            
            url = f"https://api.telegram.org/bot{self.token}/getUpdates"
            # ВАЖНО: Явно указываем allowed_updates с pre_checkout_query для получения платежных событий
            # По документации Telegram, если не указать allowed_updates, могут не приходить некоторые типы событий
            params = {
                'offset': self.offset,
                'timeout': self.polling_timeout,
                'limit': self.polling_limit,
                'allowed_updates': ['message', 'callback_query', 'pre_checkout_query']  # Явно указываем типы событий
            }
            
            async with self.session.get(url, params=params) as response:
                try:
                    data = await response.json()
                except Exception:
                    # Если JSON не парсится, но HTTP статус критический - обрабатываем как критическую ошибку
                    if response.status in self.critical_error_codes:
                        status_code = response.status
                        description = f'HTTP {status_code} - {response.reason}'
                        self._handle_critical_error(status_code, description)
                        raise Exception(f"Critical error {status_code}: {description}") from None
                    raise
                
                if data.get('ok'):
                    updates = data.get('result', [])
                    # Сбрасываем счетчик ошибок при успешном запросе
                    self.consecutive_critical_errors = 0
                    return updates
                else:
                    # Обработка специфичных ошибок Telegram API
                    error_code = data.get('error_code')
                    description = data.get('description', 'Unknown error')
                    
                    # Проверяем критичность по error_code (основной случай для Telegram API)
                    if error_code in self.critical_error_codes:
                        self._handle_critical_error(error_code, description)
                        raise Exception(f"Critical error {error_code}: {description}")
                    elif error_code == 429:
                        self.logger.warning(f"[Bot-{self.bot_id}] Rate limit: {description}")
                        
                        # Получаем retry_after из ответа (если есть)
                        retry_after = data.get('retry_after', self.retry_after_rate_limit)
                        self.logger.info(f"[Bot-{self.bot_id}] Ждем {retry_after} секунд перед повторной попыткой")
                        
                        # Ждем указанное время
                        await asyncio.sleep(retry_after)
                        raise Exception(f"Rate limited: {description}")
                    elif error_code == 409:
                        self.logger.warning(f"[Bot-{self.bot_id}] Конфликт webhook: {description}")
                        raise Exception(f"Webhook conflict: {description}")
                    else:
                        self.logger.error(f"[Bot-{self.bot_id}] API ошибка: {error_code} - {description}")
                        raise Exception(f"API Error {error_code}: {description}")
                    
        except aiohttp.ClientError as e:
            # Обрабатываем сетевые ошибки
            self._handle_network_error(e, "получении обновлений")
            raise
            