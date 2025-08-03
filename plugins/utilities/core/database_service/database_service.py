from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Action, Base, InviteLink, Request, User, UserState
from .repositories.actions import ActionsRepository
from .repositories.invite_links import InviteLinksRepository
from .repositories.requests import RequestsRepository
from .repositories.user_states import UserStatesRepository
from .repositories.users import UsersRepository


class DatabaseService:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.data_preparer = kwargs['data_preparer']
        self.data_converter = kwargs['data_converter']
        self.action_parser = kwargs['action_parser']
        self.placeholder_processor = kwargs.get('placeholder_processor')
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings("database_service")
        
        self.database_url = settings.get('database_url', 'sqlite:///data/bot_core.db')
        self.echo = settings.get('echo', False)
        
        # Создаём engine и фабрику сессий
        self.engine = create_engine(self.database_url, echo=self.echo, future=True)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    @contextmanager
    def session_scope(self, *repo_names):
        """Контекстный менеджер для сессии и репозиториев.
        
        Args:
            *repo_names: Названия нужных репозиториев ('actions', 'users', 'user_states', 'requests')
        """
        session = self.session_factory()
        try:
            repos = {}
            if 'actions' in repo_names:
                repos['actions'] = ActionsRepository(
                    session=session,
                    logger=self.logger,
                    model=Action,
                    datetime_formatter=self.datetime_formatter,
                    data_preparer=self.data_preparer,
                    data_converter=self.data_converter,
                    action_parser=self.action_parser,
                    placeholder_processor=self.placeholder_processor
                )
            if 'users' in repo_names:
                repos['users'] = UsersRepository(
                    session=session,
                    logger=self.logger,
                    model=User,
                    datetime_formatter=self.datetime_formatter,
                    data_preparer=self.data_preparer,
                    data_converter=self.data_converter
                )
            if 'user_states' in repo_names:
                repos['user_states'] = UserStatesRepository(
                    session=session,
                    logger=self.logger,
                    model=UserState,
                    datetime_formatter=self.datetime_formatter,
                    data_preparer=self.data_preparer,
                    data_converter=self.data_converter
                )
            if 'requests' in repo_names:
                repos['requests'] = RequestsRepository(
                    session=session,
                    logger=self.logger,
                    model=Request,
                    datetime_formatter=self.datetime_formatter,
                    data_preparer=self.data_preparer,
                    data_converter=self.data_converter
                )
            if 'invite_links' in repo_names:
                repos['invite_links'] = InviteLinksRepository(
                    session=session,
                    logger=self.logger,
                    model=InviteLink,
                    datetime_formatter=self.datetime_formatter,
                    data_preparer=self.data_preparer,
                    data_converter=self.data_converter
                )

            yield session, repos
        finally:
            session.close()

    def create_all(self):
        """Создаёт все таблицы в БД согласно моделям."""
        try:
            Base.metadata.create_all(self.engine)
            self.logger.info("Все таблицы успешно созданы.")
        except Exception as e:
            self.logger.error(f"Ошибка при создании таблиц: {e}")
    
    def get_table_class_map(self):
        """Получает карту таблиц: имя таблицы -> класс модели."""
        table_class_map = {}
        for table_name, table in Base.metadata.tables.items():
            # Находим соответствующую модель
            for model_class in Base.registry._class_registry.values():
                if hasattr(model_class, '__tablename__') and model_class.__tablename__ == table_name:
                    table_class_map[table_name] = model_class
                    break
        return table_class_map
