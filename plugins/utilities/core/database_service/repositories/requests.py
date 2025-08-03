from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select


class RequestsRepository:
    """
    Репозиторий для работы с таблицей Requests (запросы пользователей).
    """
    # JSON-поля, которые нужно автоматически декодировать
    JSON_FIELDS = ['attachments']
    
    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter

    def add_request(self, **fields) -> int:
        """Добавляет новый запрос пользователя."""
        try:
            # Добавляем автоматические поля
            fields['created_at'] = self.datetime_formatter.now_local()
            fields['updated_at'] = self.datetime_formatter.now_local()
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_insert(
                model=self.model,
                fields=fields,
                json_fields=self.JSON_FIELDS
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для создания запроса")
                return 0
            
            # Создаем и сохраняем запрос
            request = self.model(**prepared_fields)
            self.session.add(request)
            self.session.commit()
            self.session.flush()
            
            request_id = getattr(request, 'id', 0)
            user_id = fields.get('user_id', 0)
    
            return request_id
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка добавления запроса: {e}")
            return 0

    def get_request_by_id(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Получает запрос по ID."""
        try:
            stmt = select(self.model).where(self.model.id == request_id)
            request = self.session.execute(stmt).scalar_one_or_none()
            
            if not request:
                return None
                
            return self.data_converter.to_dict(request, json_fields=self.JSON_FIELDS)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения запроса {request_id}: {e}")
            return None

    def get_requests_with_filters(self, from_date: Optional[datetime] = None, 
                                 request_name: Optional[str | List[str]] = None,
                                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получает список запросов с фильтрацией."""
        try:
            stmt = select(self.model)
            
            # Фильтр по дате
            if from_date:
                stmt = stmt.where(self.model.created_at >= from_date)
            
            # Фильтр по типу запроса (поддерживает как строку, так и массив)
            if request_name:
                if isinstance(request_name, list):
                    # Если передан массив, используем IN для поиска по нескольким типам
                    stmt = stmt.where(self.model.request_name.in_(request_name))
                else:
                    # Если передана строка, используем точное совпадение
                    stmt = stmt.where(self.model.request_name == request_name)
            
            # Сортировка по дате создания (новые сначала)
            stmt = stmt.order_by(self.model.created_at.desc())
            
            # Ограничение по количеству
            if limit is not None:
                stmt = stmt.limit(limit)
            
            requests = self.session.execute(stmt).scalars().all()
            return self.data_converter.to_dict_list(requests, json_fields=self.JSON_FIELDS)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения запросов с фильтрами: {e}")
            return []
