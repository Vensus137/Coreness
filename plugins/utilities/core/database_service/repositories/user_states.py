from typing import Any, Dict, Optional

from sqlalchemy import select, update


class UserStatesRepository:
    """
    Репозиторий для работы с таблицей UserStates (состояния пользователей).
    """
    # Поля, которые содержат JSON данные
    JSON_FIELDS = ['state_data']

    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter

    def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить состояние пользователя."""
        try:
            stmt = select(self.model).where(self.model.user_id == user_id)
            user_state = self.session.execute(stmt).scalar_one_or_none()
            
            if not user_state:
                return None
                
            return self.data_converter.to_dict(user_state)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения состояния пользователя {user_id}: {e}")
            return None

    def clear_user_state(self, user_id: int) -> bool:
        """Очистить состояние пользователя."""
        try:
            # Проверяем существование состояния
            stmt = select(self.model).where(self.model.user_id == user_id)
            user_state = self.session.execute(stmt).scalar_one_or_none()
            
            if user_state:
                self.session.delete(user_state)
                self.session.commit()
        
            else:
                self.logger.warning(f"Попытка очистить несуществующее состояние для пользователя {user_id}")
            return True
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка при очистке состояния пользователя {user_id}: {e}")
            return False

    def update_user_state(self, user_id: int, **fields) -> bool:
        """Универсальный метод обновления состояния пользователя."""
        try:
            # Проверяем обязательные поля
            required_fields = ['state_type', 'expired_at']
            missing = [f for f in required_fields if f not in fields or fields[f] is None]
            if missing:
                self.logger.error(f"update_user_state: не указаны обязательные поля: {missing}")
                return False
            
            # Добавляем автоматическое поле updated_at
            if 'updated_at' not in fields:
                fields['updated_at'] = self.datetime_formatter.now_local()

            # Проверяем существование состояния
            stmt = select(self.model).where(self.model.user_id == user_id)
            user_state = self.session.execute(stmt).scalar_one_or_none()

            if user_state:
                # Обновляем существующее состояние
                prepared_fields = self.data_preparer.prepare_for_update(
                    model=self.model,
                    fields=fields,
                    json_fields=self.JSON_FIELDS
                )
                
                if not prepared_fields:
                    self.logger.warning(f"Нет валидных полей для обновления состояния пользователя {user_id}")
                    return False

                # Выполняем обновление
                stmt = update(self.model).where(self.model.user_id == user_id).values(**prepared_fields)
                result = self.session.execute(stmt)
                self.session.commit()

                if result.rowcount > 0:
            
                    return True
                else:
                    self.logger.warning(f"Состояние пользователя {user_id} не найдено для обновления")
                    return False

            else:
                # Создаем новое состояние
                # Добавляем user_id в fields для создания
                fields['user_id'] = user_id
                
                prepared_fields = self.data_preparer.prepare_for_insert(
                    model=self.model,
                    fields=fields,
                    json_fields=self.JSON_FIELDS
                )
                
                if not prepared_fields:
                    self.logger.error("Не удалось подготовить поля для создания состояния пользователя")
                    return False

                # Создаем новое состояние
                new_state = self.model(**prepared_fields)
                self.session.add(new_state)
                self.session.commit()
                self.session.flush()

                return True

        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка операции с состоянием пользователя {user_id}: {e}")
            return False