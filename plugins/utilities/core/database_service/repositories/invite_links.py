from typing import Any, Dict, List, Optional

from sqlalchemy import select


class InviteLinksRepository:
    """
    Репозиторий для работы с таблицей InviteLinks (пригласительные ссылки).
    """
    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter

    def add_invite_link(self, **fields) -> int:
        """Добавляет новую пригласительную ссылку."""
        try:
            # Добавляем автоматическое поле created_at
            fields['created_at'] = self.datetime_formatter.now_local()
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_insert(
                model=self.model,
                fields=fields
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для создания ссылки")
                return 0
            
            # Создаем и сохраняем ссылку
            invite_link = self.model(**prepared_fields)
            self.session.add(invite_link)
            self.session.commit()
            self.session.flush()
            
            invite_link_id = getattr(invite_link, 'id', 0)
    
            return invite_link_id
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка добавления ссылки: {e}")
            return 0

    def get_invite_link_by_url(self, invite_link: str) -> Optional[Dict[str, Any]]:
        """Получает ссылку по URL."""
        try:
            stmt = select(self.model).where(self.model.invite_link == invite_link)
            result = self.session.execute(stmt).scalar_one_or_none()
            
            if not result:
                return None
                
            return self.data_converter.to_dict(result)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения ссылки {invite_link}: {e}")
            return None

    def get_invite_links_by_chat(self, chat_id: int) -> List[Dict[str, Any]]:
        """Получает все ссылки для чата."""
        try:
            stmt = select(self.model).where(self.model.chat_id == chat_id)
            results = self.session.execute(stmt).scalars().all()
            return self.data_converter.to_dict_list(results)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения ссылок для чата {chat_id}: {e}")
            return []

    def delete_invite_link(self, invite_link: str) -> bool:
        """Удалить ссылку из базы данных"""
        db_invite_link = self.session.query(self.model).filter_by(invite_link=invite_link).first()
        if db_invite_link:
            try:
                self.session.delete(db_invite_link)
                self.session.commit()
                return True
            except Exception as e:
                self.session.rollback()
                self.logger.error(f"Ошибка удаления ссылки: {e}")
                return False
        return False

    def get_invite_links_by_urls(self, invite_links: List[str]) -> List[Dict[str, Any]]:
        """Получает ссылки по списку URL."""
        try:
            stmt = select(self.model).where(self.model.invite_link.in_(invite_links))
            results = self.session.execute(stmt).scalars().all()
            return self.data_converter.to_dict_list(results)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения ссылок по URL: {e}")
            return [] 