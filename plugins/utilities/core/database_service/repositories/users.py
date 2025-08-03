from typing import Any, Dict, Optional

from sqlalchemy import select, update


class UsersRepository:
    """
    Репозиторий для работы с таблицей Users (пользователи бота).
    """
    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по user_id."""
        try:
            stmt = select(self.model).where(self.model.user_id == user_id)
            user = self.session.execute(stmt).scalar_one_or_none()
            
            if not user:
                return None
                
            return self.data_converter.to_dict(user)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Получает пользователя по username (без учета регистра)."""
        try:
            # Приводим к нижнему регистру для сравнения
            username_lower = username.lower()
            stmt = select(self.model).where(self.model.username.ilike(username_lower))
            user = self.session.execute(stmt).scalar_one_or_none()
            
            if not user:
                return None
                
            return self.data_converter.to_dict(user)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения пользователя по username {username}: {e}")
            return None

    def update_user(self, user_id: int, **fields) -> bool:
        """Обновляет пользователя по user_id."""
        try:
            # Добавляем автоматическое поле updated_at
            if 'updated_at' not in fields:
                fields['updated_at'] = self.datetime_formatter.now_local()
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_update(
                model=self.model,
                fields=fields
            )
            
            if not prepared_fields:
                self.logger.warning(f"Нет валидных полей для обновления пользователя {user_id}")
                return False
            
            # Выполняем обновление
            stmt = update(self.model).where(self.model.user_id == user_id).values(**prepared_fields)
            result = self.session.execute(stmt)
            self.session.commit()
            
            if result.rowcount > 0:
        
                return True
            else:
                self.logger.warning(f"Пользователь {user_id} не найден для обновления")
                return False
                
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка обновления пользователя {user_id}: {e}")
            return False

    def add_user(self, **fields) -> int:
        """Добавляет нового пользователя."""
        try:
            # Добавляем автоматические поля
            if 'created_at' not in fields:
                fields['created_at'] = self.datetime_formatter.now_local()
            if 'updated_at' not in fields:
                fields['updated_at'] = self.datetime_formatter.now_local()
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_insert(
                model=self.model,
                fields=fields
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для создания пользователя")
                return 0
            
            # Создаем нового пользователя
            user = self.model(**prepared_fields)
            self.session.add(user)
            self.session.commit()
            self.session.flush()
            
            user_id = getattr(user, 'user_id', 0)
    
            return user_id
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка создания пользователя: {e}")
            return 0

    def add_or_update(self, user_id: int, **fields) -> bool:
        """Добавляет или обновляет пользователя."""
        try:
            # Проверяем существование пользователя
            stmt = select(self.model).where(self.model.user_id == user_id)
            user = self.session.execute(stmt).scalar_one_or_none()
            
            if user:
                # Обновляем существующего пользователя
                return self.update_user(user_id, **fields)
            else:
                # Создаем нового пользователя
                fields['user_id'] = user_id
                new_user_id = self.add_user(**fields)
                return new_user_id > 0
                
        except Exception as e:
            self.logger.error(f"Ошибка операции с пользователем {user_id}: {e}")
            return False
