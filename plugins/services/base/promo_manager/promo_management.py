from typing import Any, Dict

class PromoManagement:
    """Модуль для управления промокодами (просмотр списка, детали)"""
    
    def __init__(self, database_service, logger, settings_manager, datetime_formatter, users_directory):
        self.database_service = database_service
        self.logger = logger
        self.settings_manager = settings_manager
        self.datetime_formatter = datetime_formatter
        self.users_directory = users_directory
    
    async def handle_promo_management(self, action: Dict[str, Any], promo_repo: Any, users_repo: Any) -> Dict[str, Any]:
        """Обрабатывает действие управления промокодами"""
        try:
            operation = action.get('operation')
            
            if operation == 'list':
                return await self._handle_list_operation(action, promo_repo, users_repo)
            elif operation == 'details':
                return await self._handle_details_operation(action, promo_repo, users_repo)
            else:
                return {"error": f"Неизвестная операция: {operation}"}
                
        except Exception as e:
            self.logger.error(f'Ошибка при обработке действия управления промокодами: {e}')
            return {"error": f"Ошибка обработки действия управления: {str(e)}"}
    
    async def _handle_list_operation(self, parsed_action: Dict, promo_repo: Any, users_repo: Any) -> Dict[str, Any]:
        """Обрабатывает операцию получения списка промокодов"""
        try:
            # Получаем параметры фильтрации
            name_pattern = parsed_action.get('name_pattern')
            user_filter = parsed_action.get('user_filter')
            promo_code = parsed_action.get('promo_code')
            date_from = parsed_action.get('date_from')
            date_to = parsed_action.get('date_to')
            expired_before = parsed_action.get('expired_before')  # Добавляем поддержку expired_before
            expired_after = parsed_action.get('expired_after')  # Добавляем поддержку expired_after
            limit = parsed_action.get('limit', 50)
            
            # Обрабатываем user_filter
            user_id = None
            if user_filter:
                if isinstance(user_filter, int):
                    user_id = user_filter
                elif isinstance(user_filter, str):
                    if user_filter.isdigit():
                        user_id = int(user_filter)
                    else:
                        # Используем users_directory для резолва username
                        user_id = self.users_directory.get_user_id_by_username(user_filter)
                else:
                    self.logger.warning(f'Неожиданный тип user_filter: {type(user_filter)}, значение: {user_filter}')
            
            # Обрабатываем даты с поддержкой удобных форматов
            if date_from and isinstance(date_from, str):
                try:
                    date_from = self.datetime_formatter.parse_date_string(date_from)
                except ValueError as e:
                    self.logger.error(f'Ошибка парсинга даты date_from="{date_from}": {e}')
                    return {"error": f"Ошибка парсинга даты: {str(e)}"}
            
            if date_to and isinstance(date_to, str):
                try:
                    date_to = self.datetime_formatter.parse_date_string(date_to)
                except ValueError as e:
                    self.logger.error(f'Ошибка парсинга даты date_to="{date_to}": {e}')
                    return {"error": f"Ошибка парсинга даты: {str(e)}"}
            
            # Обрабатываем expired_before
            if expired_before and isinstance(expired_before, str):
                try:
                    expired_before = self.datetime_formatter.parse_date_string(expired_before)
                except ValueError as e:
                    self.logger.error(f'Ошибка парсинга даты expired_before="{expired_before}": {e}')
                    return {"error": f"Ошибка парсинга даты: {str(e)}"}
            
            # Обрабатываем expired_after
            if expired_after and isinstance(expired_after, str):
                try:
                    expired_after = self.datetime_formatter.parse_date_string(expired_after)
                except ValueError as e:
                    self.logger.error(f'Ошибка парсинга даты expired_after="{expired_after}": {e}')
                    return {"error": f"Ошибка парсинга даты: {str(e)}"}
            
            # Получаем промокоды с фильтрацией
            promos = promo_repo.get_promos_by_filters(
                name_pattern=name_pattern,
                user_id=user_id,
                promo_code=promo_code,
                date_from=date_from,
                date_to=date_to,
                expired_before=expired_before,  # Передаем expired_before
                expired_after=expired_after,  # Передаем expired_after
                limit=limit
            )
            
            # Формируем список для отображения
            if promos:
                # Добавляем заголовок
                header = "<b>Список промокодов"
                if name_pattern:
                    header += f" (название: {name_pattern})"
                if user_filter:
                    header += f" (пользователь: {user_filter})"
                if promo_code:
                    header += f" (код: {promo_code})"
                if expired_before:
                    header += f" (истекает до: {expired_before.strftime('%Y-%m-%d')})"
                if expired_after:
                    header += f" (истекает после: {expired_after.strftime('%Y-%m-%d')})"
                header += ":</b>"
                
                # Формируем упрощенную таблицу
                table_header = "<code> ID |    Код     | Название</code>"
                separator = "<code>------------------------------</code>"
                
                # Формируем строки таблицы
                table_rows = []
                for i, promo in enumerate(promos):
                    # Проверяем, что promo является словарем
                    if not isinstance(promo, dict):
                        self.logger.warning(f'Неожиданный тип данных промокода #{i+1}: {type(promo)}, пропускаем')
                        continue
                    
                    # Проверяем наличие обязательных полей
                    if 'id' not in promo or 'promo_code' not in promo or 'promo_name' not in promo:
                        self.logger.warning(f'Промокод #{i+1} не содержит обязательные поля: {promo}, пропускаем')
                        continue
                    
                    # Сразу преобразуем promo_code в строку (безопасно для любых типов)
                    promo_code_value = str(promo['promo_code'])
                    
                    # ID в моноширинном шрифте с красивым выравниванием
                    if promo['id'] < 1000:  # 3-значные числа
                        promo_id = f"<code>{promo['id']:3d} </code>"  # по правому краю в 3 символах + пробел
                    else:  # 4-значные числа
                        promo_id = f"<code>{promo['id']:4d}</code>"  # по левому краю без пробелов
                    
                    # Код промокода (обрезаем до 12 символов и центрируем)
                    code = f"<code>{promo_code_value[:12].center(12)}</code>"
                    
                    # Название (обрезаем до 20 символов, обычный текст слева)
                    name = (promo['promo_name'] or '')[:20].ljust(20)
                    
                    # Собираем строку с обернутыми в <code> разделителями и пробелами
                    row = f"{promo_id}<code>|</code>{code}<code>| </code>{name}"
                    table_rows.append(row)
                
                # Собираем итоговую таблицу
                response_text = f"{header}\n{separator}\n{table_header}\n{separator}\n" + "\n".join(table_rows) + f"\n{separator}"
            else:
                response_text = "Промокоды не найдены."
            
            return {"response_text": response_text}
            
        except Exception as e:
            self.logger.error(f'Ошибка при формировании списка промокодов: {e}')
            return {"error": f"Ошибка формирования списка: {str(e)}"}
    
    async def _handle_details_operation(self, parsed_action: Dict, promo_repo: Any, users_repo: Any) -> Dict[str, Any]:
        """Обрабатывает операцию получения детальной информации по промокоду"""
        try:
            promo_id = parsed_action.get('promo_id')
            promo_code = parsed_action.get('promo_code')
            event_text = parsed_action.get('event_text', '').strip()
            
            # Определяем ID промокода
            target_id = None
            if promo_id:
                target_id = promo_id
            elif promo_code:
                # Ищем по коду
                promos = promo_repo.get_promos_by_filters(promo_code=promo_code, limit=1)
                if promos:
                    target_id = promos[0]['id']
            elif event_text.isdigit():
                target_id = int(event_text)
            
            if not target_id:
                return {"error": "Не указан ID промокода, код или event_text"}
            
            # Получаем промокод
            promo = promo_repo.get_promo_by_id(target_id)
            if not promo:
                return {"error": f"Промокод с ID={target_id} не найден"}
            
            # Формируем детальную информацию
            lines = []
            lines.append(f"<b>Промокод #{promo['id']}</b>")
            lines.append("")  # Отступ после номера
            
            # Основная информация
            lines.append(f"<b>Код:</b> <code>{promo['promo_code']}</code>")
            
            # Название и статус (без отступа после кода)
            lines.append(f"<b>Название:</b> <code>{promo['promo_name']}</code>")
            
            # Статус сразу после названия
            now = self.datetime_formatter.now_local()
            if promo['started_at'] <= now <= promo['expired_at']:
                status = "🟢 Активен"
            else:
                status = "🔴 Истек"
            lines.append(f"<b>Статус:</b> <code>{status}</code>")
            lines.append("")  # Отступ после названия и статуса
            
            # Пользователь
            if promo['user_id']:
                user = users_repo.get_user_by_id(promo['user_id'])
                username = user.get('username') if user else None
                if username:
                    lines.append(f"<b>Пользователь:</b> @{username}")  # Логин без <code>
                else:
                    lines.append(f"<b>Пользователь:</b> <code>ID {promo['user_id']}</code>")  # ID в <code>
            else:
                lines.append("<b>Пользователь:</b> <code>Все пользователи</code>")  # Текст в <code>
            
            # Даты
            started_at = self.datetime_formatter.to_datetime_string(promo['started_at'])
            expired_at = self.datetime_formatter.to_datetime_string(promo['expired_at'])
            created_at = self.datetime_formatter.to_datetime_string(promo['created_at'])
            
            lines.append(f"<b>Действует с:</b> <code>{started_at}</code>")
            lines.append(f"<b>Действует до:</b> <code>{expired_at}</code>")
            lines.append(f"<b>Создан:</b> <code>{created_at}</code>")
            
            # Убираем соль и хэш - они не нужны
            
            response_text = '\n'.join(lines)
            return {"response_text": response_text}
            
        except Exception as e:
            self.logger.error(f'Ошибка при получении детальной информации: {e}')
            return {"error": f"Ошибка получения детальной информации: {str(e)}"}
