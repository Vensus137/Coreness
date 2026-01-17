from typing import Any, Dict, List, Optional, Union


class DatetimeFormatter:

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("datetime_formatter")
        self.timezone = settings.get('timezone', 'Europe/Moscow')
        self.format_name = settings.get('format', 'iso')
        self._tz = None  # Ленивая инициализация

    def _get_timezone(self):
        """Ленивая инициализация timezone"""
        if self._tz is None:
            from zoneinfo import ZoneInfo
            self._tz = ZoneInfo(self.timezone)
        return self._tz

    def _normalize_to_utc_datetime(self, dt):
        """
        Нормализовать datetime или Unix timestamp в UTC datetime.
        
        ВАЖНО: Если передан naive datetime, считаем что это локальное время (не UTC).
        Это позволяет корректно обрабатывать datetime из to_local() и now_local(),
        которые возвращают naive datetime в локальной временной зоне.
        """
        import datetime
        
        # Если передан Unix timestamp (int или float)
        if isinstance(dt, (int, float)):
            # Преобразуем timestamp в UTC datetime
            return datetime.datetime.fromtimestamp(dt, tz=datetime.timezone.utc)
        
        # Если naive datetime, считаем что это локальное время (не UTC!)
        # Конвертируем в UTC через локальную временную зону
        if dt.tzinfo is None:
            # Сначала добавляем локальную таймзону
            local_dt = dt.replace(tzinfo=self._get_timezone())
            # Затем конвертируем в UTC
            return local_dt.astimezone(datetime.timezone.utc)
        
        # Если уже timezone-aware, преобразуем в UTC
        return dt.astimezone(datetime.timezone.utc)

    async def now_utc(self):
        """Получить текущее время в UTC (naive datetime)"""
        import datetime
        # Возвращает naive UTC, но получает время через timezone-aware способ
        return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    async def now_utc_tz(self):
        """Получить текущее время в UTC (timezone-aware datetime)"""
        import datetime
        return datetime.datetime.now(datetime.timezone.utc)

    async def now_local(self):
        """Получить текущее время в локальной временной зоне (naive datetime)"""
        import datetime
        return datetime.datetime.now(self._get_timezone()).replace(tzinfo=None)

    async def now_local_tz(self):
        """Получить текущее время в локальной временной зоне (timezone-aware datetime)"""
        import datetime
        return datetime.datetime.now(self._get_timezone())

    async def to_utc(self, dt):
        """Преобразовать datetime или Unix timestamp в UTC (naive)"""
        # Нормализуем в UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        
        # Убираем tzinfo для naive UTC
        return utc_dt.replace(tzinfo=None)

    async def to_utc_tz(self, dt):
        """Преобразовать datetime или Unix timestamp в UTC (timezone-aware)"""
        # Нормализуем в UTC datetime
        return self._normalize_to_utc_datetime(dt)

    async def to_local(self, dt):
        """Преобразовать datetime или Unix timestamp в локальную временную зону (naive)"""
        # Нормализуем в UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        
        # Преобразуем в локальную временную зону и убираем tzinfo
        return utc_dt.astimezone(self._get_timezone()).replace(tzinfo=None)

    async def to_local_tz(self, dt):
        """Преобразовать datetime или Unix timestamp в локальную временную зону (timezone-aware)"""
        # Нормализуем в UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        
        # Преобразуем в локальную временную зону
        return utc_dt.astimezone(self._get_timezone())

    async def format(self, dt) -> str:
        """Форматировать datetime в строку по настройкам"""
        if self.format_name == 'iso':
            return dt.isoformat()
        # Можно добавить другие форматы по необходимости
        return dt.isoformat()

    async def to_string(self, dt, fmt: Optional[str] = None) -> str:
        """
        Преобразует datetime в строку по формату (по умолчанию ISO).
        fmt: 'iso' (default), либо любой формат strftime.
        """
        if fmt is None:
            fmt = self.format_name
        if fmt == 'iso':
            return dt.isoformat()
        return dt.strftime(fmt)

    async def to_iso_string(self, dt) -> str:
        """
        Короткий алиас для ISO-строки в UTC.
        Поддерживает datetime и Unix timestamp.
        """
        # Нормализуем в UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        return utc_dt.isoformat()
    
    async def to_iso_local_string(self, dt) -> str:
        """
        Преобразует datetime в ISO строку в локальном часовом поясе.
        Поддерживает datetime и Unix timestamp.
        Полезно для event_date, чтобы плейсхолдеры корректно форматировали дату.
        """
        # Нормализуем в UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        # Конвертируем в локальную временную зону
        local_dt = utc_dt.astimezone(self._get_timezone())
        return local_dt.isoformat()

    async def to_datetime_string(self, dt: Union[Any, str]) -> str:
        """
        Преобразует datetime или ISO-строку в читаемый формат ДДДД-ММ-ГГ ЧЧ:ММ:СС.
        Универсальный метод: принимает datetime.datetime или строку ISO формата.
        """
        import datetime
        if isinstance(dt, str):
            # Если передана строка - парсим её в datetime
            dt = await self.parse(dt)
        elif not isinstance(dt, datetime.datetime):
            self.logger.error(f"Ожидается datetime или строка ISO, получено: {type(dt)}")
            return None
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    async def to_date_string(self, dt: Union[Any, str]) -> str:
        """
        Преобразует datetime или ISO-строку в формат даты ДДДД-ММ-ГГ.
        Универсальный метод: принимает datetime.datetime или строку ISO формата.
        """
        import datetime
        if isinstance(dt, str):
            # Если передана строка - парсим её в datetime
            dt = await self.parse(dt)
        elif not isinstance(dt, datetime.datetime):
            self.logger.error(f"Ожидается datetime или строка ISO, получено: {type(dt)}")
            return None
        
        return dt.strftime('%Y-%m-%d')

    async def to_serializable(self, obj: Union[Dict, List, Any]) -> Union[Dict, List, str, Any]:
        """
        Рекурсивно преобразует все datetime в строку (ISO) для сериализации в JSON.
        """
        import datetime
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                result[k] = await self.to_serializable(v)
            return result
        elif isinstance(obj, list):
            return [await self.to_serializable(i) for i in obj]
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return obj

    async def parse(self, dt_str: str) -> Any:
        """Парсить ISO строку в datetime"""
        import datetime
        dt = datetime.datetime.fromisoformat(dt_str)
        # Возвращаем как есть: если в строке есть tzinfo — будет aware, если нет — naive
        return dt

    async def parse_to_local(self, dt_str: str) -> Any:
        """
        Парсит строку с датой и возвращает datetime в локальном времени (naive).
        Предполагает, что входная строка в локальном времени.
        Поддерживает форматы: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO формат.
        """
        dt = await self.parse_date_string(dt_str)  # Используем универсальный парсер
        # Если datetime naive - считаем его локальным
        if dt.tzinfo is None:
            return dt
        # Если datetime aware - конвертируем в локальное время
        return await self.to_local(dt)

    async def parse_to_local_tz(self, dt_str: str) -> Any:
        """
        Парсит строку с датой и возвращает datetime в локальном времени с timezone.
        Предполагает, что входная строка в локальном времени.
        Поддерживает форматы: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO формат.
        """
        dt = await self.parse_date_string(dt_str)  # Используем универсальный парсер
        # Если datetime naive - считаем его локальным и добавляем timezone
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self._get_timezone())
        # Если datetime aware - конвертируем в локальное время
        return await self.to_local_tz(dt)

    async def parse_to_utc(self, dt_str: str) -> Any:
        """
        Парсит строку с датой и возвращает datetime в UTC (naive).
        Если datetime naive - считаем его ЛОКАЛЬНЫМ временем и конвертируем в UTC.
        Если datetime aware - конвертируем в UTC.
        Поддерживает форматы: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO формат.
        """
        dt = await self.parse_date_string(dt_str)  # Используем универсальный парсер
        # Если datetime naive - считаем его ЛОКАЛЬНЫМ временем и конвертируем в UTC
        import datetime
        if dt.tzinfo is None:
            # Добавляем локальную таймзону и конвертируем в UTC
            dt_local = dt.replace(tzinfo=self._get_timezone())
            return dt_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        # Если datetime aware - конвертируем в UTC
        return await self.to_utc(dt)

    async def parse_to_utc_tz(self, dt_str: str) -> Any:
        """
        Парсит строку с датой и возвращает datetime в UTC с timezone.
        Если datetime naive - считаем его ЛОКАЛЬНЫМ временем и конвертируем в UTC.
        Если datetime aware - конвертируем в UTC.
        Поддерживает форматы: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO формат.
        """
        dt = await self.parse_date_string(dt_str)  # Используем универсальный парсер
        # Если datetime naive - считаем его ЛОКАЛЬНЫМ временем и конвертируем в UTC
        import datetime
        if dt.tzinfo is None:
            # Добавляем локальную таймзону и конвертируем в UTC
            dt_local = dt.replace(tzinfo=self._get_timezone())
            return dt_local.astimezone(datetime.timezone.utc)
        # Если datetime aware - конвертируем в UTC
        return await self.to_utc_tz(dt)

    async def parse_date_string(self, date_str: str) -> Any:
        """
        Универсальный метод для парсинга дат из строк в различных форматах.
        
        Поддерживаемые форматы:
        - ГГГГ-ММ-ДД (например, "2025-01-15")
        - ГГГГ-ММ-ДД ЧЧ:ММ:СС (например, "2025-01-15 14:30:00")
        - ISO формат с таймзоной (например, "2025-01-15T14:30:00+03:00")
        - ISO формат без таймзоны (например, "2025-01-15T14:30:00")
        - ISO формат с микросекундами (например, "2025-01-15T14:30:00.123456")
        """
        if not date_str or not isinstance(date_str, str):
            self.logger.error(f"Ожидается непустая строка, получено: {date_str}")
            return None
        
        date_str = date_str.strip()
        
        # Список форматов для попытки парсинга (в порядке приоритета)
        formats = [
            # ISO формат с таймзоной и микросекундами
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            # ISO формат с таймзоной
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            # Обычный формат с секундами
            "%Y-%m-%d %H:%M:%S",
            # Только дата
            "%Y-%m-%d",
        ]
        
        import datetime
        # Сначала пробуем стандартный ISO парсер (он лучше обрабатывает таймзоны)
        try:
            return datetime.datetime.fromisoformat(date_str)
        except ValueError:
            pass
        
        # Затем пробуем наши форматы
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(date_str, fmt)
                return dt
            except ValueError:
                continue
        
        # Если ничего не подошло, пробуем более гибкие варианты
        try:
            # Пробуем парсить как ISO, но с заменой пробела на T
            if ' ' in date_str and 'T' not in date_str:
                iso_str = date_str.replace(' ', 'T')
                return datetime.datetime.fromisoformat(iso_str)
        except ValueError:
            pass
        
        # Если все попытки не удались
        self.logger.error(f"Не удалось распарсить дату '{date_str}'. "
                         f"Поддерживаемые форматы: ГГГГ-ММ-ДД, ГГГГ-ММ-ДД ЧЧ:ММ:СС, ISO формат")
        return None

    async def time_diff(self, dt1: Union[Any, str], dt2: Union[Any, str]) -> Any:
        """
        Вычисляет разность между двумя datetime объектами с учетом часовых поясов.
        """
        # Парсим строки в datetime если нужно
        if isinstance(dt1, str):
            dt1 = await self.parse(dt1)
        if isinstance(dt2, str):
            dt2 = await self.parse(dt2)
        
        # Приводим к UTC для корректного сравнения
        dt1_utc = await self.to_utc_tz(dt1)
        dt2_utc = await self.to_utc_tz(dt2)
        
        return dt2_utc - dt1_utc

    async def is_older_than(self, dt: Union[Any, str], seconds: int) -> bool:
        """
        Проверяет, прошло ли больше указанного количества секунд с момента dt.
        """
        time_diff = await self.time_diff(dt, await self.now_local())
        return time_diff.total_seconds() > seconds

    async def is_newer_than(self, dt: Union[Any, str], seconds: int) -> bool:
        """
        Проверяет, прошло ли меньше указанного количества секунд с момента dt.
        """
        time_diff = await self.time_diff(dt, await self.now_local())
        return time_diff.total_seconds() < seconds

    async def subtract_seconds(self, dt: Union[Any, str], seconds: int) -> Any:
        """
        Вычитает указанное количество секунд из datetime.
        Поддерживает datetime и строки ISO.
        """
        import datetime
        
        # Парсим строку в datetime если нужно
        if isinstance(dt, str):
            dt = await self.parse(dt)
        
        # Вычитаем секунды
        return dt - datetime.timedelta(seconds=seconds)


