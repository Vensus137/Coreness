import datetime
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    raise ImportError("Для работы DatetimeFormatter требуется Python 3.9+ с модулем zoneinfo. Пожалуйста, обновите Python.")

class DatetimeFormatter:

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("datetime_formatter")
        self.timezone = settings.get('timezone', 'Europe/Moscow')
        self.format_name = settings.get('format', 'iso')
        self._tz = ZoneInfo(self.timezone)

    def now_utc(self) -> datetime.datetime:
        # Возвращает naive UTC, но получает время через timezone-aware способ
        return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    def now_utc_tz(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)

    def now_local(self) -> datetime.datetime:
        return datetime.datetime.now(self._tz).replace(tzinfo=None)

    def now_local_tz(self) -> datetime.datetime:
        return datetime.datetime.now(self._tz)

    def to_utc(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self._tz)
        return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    def to_utc_tz(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=self._tz)
        return dt.astimezone(datetime.timezone.utc)

    def to_local(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(self._tz).replace(tzinfo=None)

    def to_local_tz(self, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(self._tz)

    def format(self, dt: datetime.datetime) -> str:
        if self.format_name == 'iso':
            return dt.isoformat()
        # Можно добавить другие форматы по необходимости
        return dt.isoformat()

    def to_string(self, dt: datetime.datetime, fmt: Optional[str] = None) -> str:
        """
        Преобразует datetime в строку по формату (по умолчанию ISO).
        fmt: 'iso' (default), либо любой формат strftime.
        """
        if fmt is None:
            fmt = self.format_name
        if fmt == 'iso':
            return dt.isoformat()
        return dt.strftime(fmt)

    def to_iso_string(self, dt: datetime.datetime) -> str:
        """
        Короткий алиас для ISO-строки.
        """
        return dt.isoformat()

    def to_datetime_string(self, dt) -> str:
        """
        Преобразует datetime или ISO-строку в читаемый формат ДДДД-ММ-ГГ ЧЧ:ММ:СС.
        Универсальный метод: принимает datetime.datetime или строку ISO формата.
        """
        if isinstance(dt, str):
            # Если передана строка - парсим её в datetime
            dt = self.parse(dt)
        elif not isinstance(dt, datetime.datetime):
            raise ValueError(f"Ожидается datetime или строка ISO, получено: {type(dt)}")
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    def to_date_string(self, dt) -> str:
        """
        Преобразует datetime или ISO-строку в формат даты ДДДД-ММ-ГГ.
        Универсальный метод: принимает datetime.datetime или строку ISO формата.
        """
        if isinstance(dt, str):
            # Если передана строка - парсим её в datetime
            dt = self.parse(dt)
        elif not isinstance(dt, datetime.datetime):
            raise ValueError(f"Ожидается datetime или строка ISO, получено: {type(dt)}")
        
        return dt.strftime('%Y-%m-%d')

    def to_serializable(self, obj):
        """
        Рекурсивно преобразует все datetime в строку (ISO) для сериализации в JSON.
        """
        import datetime
        if isinstance(obj, dict):
            return {k: self.to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.to_serializable(i) for i in obj]
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return obj

    def parse(self, dt_str: str) -> datetime.datetime:
        dt = datetime.datetime.fromisoformat(dt_str)
        # Возвращаем как есть: если в строке есть tzinfo — будет aware, если нет — naive
        return dt

    def parse_date_string(self, date_str: str) -> datetime.datetime:
        """
        Универсальный метод для парсинга дат из строк в различных форматах.
        
        Поддерживаемые форматы:
        - ГГГГ-ММ-ДД (например, "2025-01-15")
        - ГГГГ-ММ-ДД ЧЧ:ММ:СС (например, "2025-01-15 14:30:00")
        - ISO формат с таймзоной (например, "2025-01-15T14:30:00+03:00")
        - ISO формат без таймзоны (например, "2025-01-15T14:30:00")
        - ISO формат с микросекундами (например, "2025-01-15T14:30:00.123456")
        
        Args:
            date_str: Строка с датой для парсинга
            
        Returns:
            datetime.datetime: Объект datetime (aware если есть tzinfo, иначе naive)
            
        Raises:
            ValueError: Если строка не соответствует ни одному из поддерживаемых форматов
        """
        if not date_str or not isinstance(date_str, str):
            raise ValueError(f"Ожидается непустая строка, получено: {date_str}")
        
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
        raise ValueError(f"Не удалось распарсить дату '{date_str}'. "
                        f"Поддерживаемые форматы: ГГГГ-ММ-ДД, ГГГГ-ММ-ДД ЧЧ:ММ:СС, ISO формат")


