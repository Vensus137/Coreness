from typing import Any, Dict, List, Optional

from sqlalchemy import select, update


class ActionsRepository:
    """
    Репозиторий для работы с таблицей Actions (очередь действий).
    """
    # JSON-поля, которые нужно автоматически декодировать
    JSON_FIELDS = ['action_data', 'prev_data', 'response_data', 'chain_drop_status', 'unlock_status']
    
    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter, action_parser, placeholder_processor=None):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter
        self.action_parser = action_parser
        self.placeholder_processor = placeholder_processor

    def add_action(self, **fields) -> int:
        """Добавляет новое действие в очередь. """
        try:
            # Добавляем автоматическое поле created_at
            fields['created_at'] = self.datetime_formatter.now_local()
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_insert(
                model=self.model,
                fields=fields,
                json_fields=self.JSON_FIELDS
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для создания действия")
                return 0
            
            # Создаем и сохраняем действие
            action = self.model(**prepared_fields)
            self.session.add(action)
            self.session.commit()
            self.session.flush()
            
            action_id = getattr(action, 'id', 0)
            action_type = fields.get('action_type', 'unknown')
    
            return action_id
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка добавления действия: {e}")
            return 0

    def get_pending_actions_by_type(self, action_type: str | List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список pending-действий для указанного типа или типов."""
        try:
            # Формируем запрос в зависимости от типа параметра
            if isinstance(action_type, str):
                stmt = (select(self.model)
                       .where(self.model.status == 'pending', self.model.action_type == action_type)
                       .order_by(self.model.created_at.asc())
                       .limit(limit))
            else:
                stmt = (select(self.model)
                       .where(self.model.status == 'pending', self.model.action_type.in_(action_type))
                       .order_by(self.model.created_at.asc())
                       .limit(limit))

            # Выполняем запрос и конвертируем через универсальный конвертер
            actions = self.session.execute(stmt).scalars().all()
            return self.data_converter.to_dict_list(actions, json_fields=self.JSON_FIELDS)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения pending действий по типу/типам {action_type}: {e}")
            return []

    def get_pending_actions_by_type_parsed(self, action_type: str | List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список pending-действий для указанного типа или типов с автоматическим парсингом и обработкой плейсхолдеров."""
        actions = self.get_pending_actions_by_type(action_type, limit)
        parsed_actions = []
        
        for action in actions:
            processed_action = self._process_action_with_placeholders(action)
            if processed_action:
                parsed_actions.append(processed_action)
        
        return parsed_actions

    def update_action(self, action_id: int, **fields) -> bool:
        """Универсальный метод обновления действия по ID."""
        try:
            # Добавляем автоматическое поле processed_at, если его нет
            if 'processed_at' not in fields:
                fields['processed_at'] = self.datetime_formatter.now_local()
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_update(
                model=self.model,
                fields=fields,
                json_fields=self.JSON_FIELDS
            )
            
            if not prepared_fields:
                self.logger.warning(f"Нет валидных полей для обновления действия {action_id}")
                return False
            
            # Выполняем обновление
            stmt = update(self.model).where(self.model.id == action_id).values(**prepared_fields)
            result = self.session.execute(stmt)
            self.session.commit()
            
            # Принудительно обновляем сессию чтобы избежать кэширования
            self.session.expire_all()
            
            if result.rowcount > 0:
                return True
            else:
                self.logger.warning(f"Действие {action_id} не найдено для обновления")
                return False
                
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка обновления действия {action_id}: {e}")
            return False

    def get_actions_by_prev_action_id(self, prev_action_id: int, statuses: str | List[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получает действия с конкретным prev_action_id, отфильтрованные по статусам."""
        try:
            stmt = select(self.model).where(self.model.prev_action_id == prev_action_id)
            
            # Добавляем фильтр по статусам, если указаны
            if statuses:
                if isinstance(statuses, str):
                    # Один статус
                    stmt = stmt.where(self.model.status == statuses)
                else:
                    # Список статусов
                    stmt = stmt.where(self.model.status.in_(statuses))
            
            stmt = stmt.order_by(self.model.processed_at.asc())
            
            if limit:
                stmt = stmt.limit(limit)
                
            actions = self.session.execute(stmt).scalars().all()
            result = self.data_converter.to_dict_list(actions, json_fields=self.JSON_FIELDS)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка получения действий по prev_action_id {prev_action_id}: {e}")
            return []

    def get_actions_by_prev_action_id_parsed(self, prev_action_id: int, statuses: str | List[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получает действия с конкретным prev_action_id, отфильтрованные по статусам, с автоматическим парсингом."""
        actions = self.get_actions_by_prev_action_id(prev_action_id, statuses, limit)
        return [self.action_parser.parse_action(action) for action in actions]

    def get_action_by_id(self, action_id: int) -> Optional[Dict[str, Any]]:
        """Получает действие по ID."""
        try:
            stmt = select(self.model).where(self.model.id == action_id)
            action = self.session.execute(stmt).scalar_one_or_none()
            
            if not action:
                return None
                
            return self.data_converter.to_dict(action, json_fields=self.JSON_FIELDS)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения действия {action_id}: {e}")
            return None

    def get_action_by_id_parsed(self, action_id: int) -> Optional[Dict[str, Any]]:
        """Получает действие по ID с автоматическим парсингом и обработкой плейсхолдеров."""
        
        action = self.get_action_by_id(action_id)
        if not action:
            self.logger.debug(f"❌ Действие {action_id} не найдено в БД")
            return None
            
        return self._process_action_with_placeholders(action)

    def cleanup_old_actions(self, cutoff_datetime, batch_size: Optional[int] = None) -> int:
        """Удаляет старые действия старше cutoff_datetime."""
        try:
            # Формируем базовый запрос по времени
            query = self.session.query(self.model).filter(
                self.model.created_at < cutoff_datetime
            ).order_by(self.model.created_at)
            
            # Удаляем записи
            if batch_size:
                # Пакетное удаление
                ids = [row[0] for row in query.with_entities(self.model.id).limit(batch_size).all()]
                if not ids:
            
                    return 0
                    
                result = self.session.query(self.model).filter(self.model.id.in_(ids)).delete(synchronize_session=False)
            else:
                # Удаление всех подходящих записей
                result = query.delete(synchronize_session=False)
                
            self.session.commit()
            self.logger.info(f"Удалено {result} старых действий")
            return result
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка очистки старых действий: {e}")
            return 0

    def get_actions_for_unlocker(self, statuses: str | List[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получает действия для проверки анлокером (не проверенные, с указанными статусами)."""
        try:
            # Используем значения по умолчанию, если статусы не указаны
            if statuses is None:
                statuses = ['completed', 'failed', 'drop']
            
            stmt = (select(self.model)
                   .where(self.model.is_unlocker_checked == False))
            
            # Добавляем фильтр по статусам
            if isinstance(statuses, str):
                # Один статус
                stmt = stmt.where(self.model.status == statuses)
            else:
                # Список статусов
                stmt = stmt.where(self.model.status.in_(statuses))
            
            stmt = stmt.order_by(self.model.created_at.asc())
            
            if limit:
                stmt = stmt.limit(limit)
                
            actions = self.session.execute(stmt).scalars().all()
            return self.data_converter.to_dict_list(actions, json_fields=self.JSON_FIELDS)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения действий для анлокера: {e}")
            return []

    def _process_action_with_placeholders(self, action: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Внутренний метод для обработки действия с плейсхолдерами."""
        action_id = action.get('id')
        
        # Парсим действие - получаем flat_action
        flat_action = self.action_parser.parse_action(action)
        if not flat_action:
            return None
        
        # Проверяем, нужно ли обрабатывать плейсхолдеры
        placeholders_enabled = flat_action.get('placeholder')
        
        if placeholders_enabled is True and self.placeholder_processor:
            try:
                # Создаем копию flat_action для обработки плейсхолдеров
                flat_action_copy = flat_action.copy()
                
                # Обрабатываем плейсхолдеры в копии flat_action, используя исходный как словарь значений
                processed_flat = self.placeholder_processor.process_placeholders_full(
                    data_with_placeholders=flat_action_copy,
                    values_dict=flat_action  # Используем исходный как источник значений
                )
                
                # Обрабатываем плейсхолдеры во всем flat_action и обогащаем prev_data
                processed_data = self.placeholder_processor.process_placeholders(
                    data_with_placeholders=flat_action_copy,  # Используем копию для безопасности
                    values_dict=flat_action  # Используем исходный как источник значений
                )
                
                # Если есть обработанные данные, обогащаем prev_data
                if processed_data:
                    # Получаем текущий prev_data из исходного action (не из flat_action!)
                    current_prev_data = action.get('prev_data', {})
                    if not isinstance(current_prev_data, dict):
                        current_prev_data = {}
                    
                    # Объединяем с перезаписью (новые данные имеют приоритет)
                    enriched_prev_data = {**current_prev_data, **processed_data}
                    
                    # Обновляем в БД только если prev_data действительно изменился
                    if enriched_prev_data != current_prev_data:
                        self.update_action(action_id, prev_data=enriched_prev_data)
                
                return processed_flat
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки плейсхолдеров для действия {action_id}: {e}")
                # Возвращаем исходный flat_action без обработки плейсхолдеров в случае ошибки
        
        return flat_action
