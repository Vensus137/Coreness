from typing import Optional


class UsersDirectory:
    """Утилита для работы с пользователями через локальную БД (только через database_service)."""

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.database_service = kwargs['database_service']

    def get_user_id_by_username(self, username: str) -> Optional[int]:
        """Вернуть user_id по username (без @). Если не найден — None."""
        try:
            if not username:
                return None
            clean_username = username.lstrip('@')
            with self.database_service.session_scope('users') as (session, repos):
                users_repo = repos['users']
                user = users_repo.get_user_by_username(clean_username)
                if not user:
                    return None
                user_id = user.get('user_id')
                return int(user_id) if user_id is not None else None
        except Exception as e:
            self.logger.error(f'Ошибка поиска user_id по username {username}: {e}')
            return None

    def add_or_update_user(self, user_id: int, username: str) -> bool:
        """Добавить или обновить пользователя (user_id, username)."""
        try:
            clean_username = (username or '').lstrip('@')
            with self.database_service.session_scope('users') as (session, repos):
                users_repo = repos['users']
                success = users_repo.add_or_update(int(user_id), username=clean_username)
                session.commit()
                return bool(success)
        except Exception as e:
            self.logger.error(f'Ошибка добавления/обновления пользователя {user_id} (@{username}): {e}')
            return False


