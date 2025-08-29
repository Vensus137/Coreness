from datetime import datetime, timedelta
from typing import Dict, Any

class PromoOperations:
    """Модуль для операций с промокодами (создание, модификация, проверка)"""
    
    def __init__(self, hash_manager, datetime_formatter, settings_manager):
        self.hash_manager = hash_manager
        self.datetime_formatter = datetime_formatter
        self.settings_manager = settings_manager
        
        # Получаем настройки
        settings = self.settings_manager.get_plugin_settings("promo_manager")
        self.default_code_length = settings.get('default_code_length', 8)
        self.default_expire_days = settings.get('default_expire_days', 30)
        self.default_global_promos = settings.get('default_global_promos', False)
    
    async def create_promo(self, data: Dict[str, Any], promo_repo: Any) -> Dict[str, Any]:
        """Создает новый промокод"""
        try:
            # Проверяем обязательные поля
            if 'promo_name' not in data:
                return {'error': 'Отсутствует обязательное поле: promo_name'}
            
            # Извлекаем нужные поля из action
            promo_name = data.get('promo_name')
            promo_code = data.get('promo_code')
            target_user_id = data.get('target_user_id')
            started_at = data.get('started_at')
            expired_at = data.get('expired_at')
            expire_seconds = data.get('expire_seconds')
            length = data.get('length', self.default_code_length)
            use_digits = data.get('use_digits', True)
            use_letters = data.get('use_letters', True)
            salt = data.get('salt', 'default')
            use_random = data.get('use_random', False)
            
            # Обрабатываем даты
            now = self.datetime_formatter.now_local()
            
            # Проверяем permanent
            if data.get('permanent', False):
                # Постоянный промокод: 2000-2999 год
                started_at = datetime(2000, 1, 1)
                expired_at = datetime(2999, 12, 31, 23, 59, 59)
            else:
                # Обычный промокод
                if not started_at:
                    started_at = now
                else:
                    started_at = self.datetime_formatter.parse(started_at)
                
                if not expired_at:
                    # Проверяем expire_seconds
                    if expire_seconds:
                        expired_at = now + timedelta(seconds=expire_seconds)
                    else:
                        expired_at = now + timedelta(days=self.default_expire_days)
                else:
                    expired_at = self.datetime_formatter.parse(expired_at)
            
            # Обрабатываем target_user_id
            if target_user_id in ['Null', 'Any', '']:
                user_id = None  # Промокод доступен всем
            elif target_user_id is not None:
                user_id = target_user_id  # Промокод привязан к конкретному пользователю
            else:
                # target_user_id не указан - используем настройку по умолчанию
                if self.default_global_promos:
                    user_id = None  # Глобальный промокод
                else:
                    # Берем user_id из события (если есть)
                    user_id = data.get('user_id')
                    if user_id is None:
                        # Если и в событии нет - делаем глобальным
                        user_id = None
            
            # Генерируем код промокода, если не указан
            if not promo_code:
                try:
                    if use_random:
                        # Для случайных промокодов генерируем случайную соль
                        salt = f"random_{self.hash_manager.generate_code(length=8, use_digits=True, use_letters=True, random=True)}"
                        promo_code = self._generate_promo_code({
                            'length': length,
                            'use_digits': use_digits,
                            'use_letters': use_letters,
                            'salt': salt,  # Случайная соль для уникальности
                            'use_random': False,  # Используем детерминированную генерацию с случайной солью
                            'user_id': user_id,
                            'promo_name': promo_name
                        })
                    else:
                        # Детерминированная генерация с обычной солью
                        promo_code = self._generate_promo_code({
                            'length': length,
                            'use_digits': use_digits,
                            'use_letters': use_letters,
                            'salt': salt,
                            'use_random': False,
                            'user_id': user_id,
                            'promo_name': promo_name
                        })
                except Exception as e:
                    return {'error': f'Не удалось сгенерировать промокод: {e}'}
            
            # Генерируем уникальный хэш-идентификатор только из стабильных полей
            hash_id = self._generate_hash_id({
                'promo_name': promo_name,
                'user_id': user_id,
                'salt': salt
            })
            
            # Проверяем, существует ли уже промокод с таким хэшем
            existing_promo = promo_repo.get_promo_by_hash_id(hash_id)
            if existing_promo:
                # Возвращаем существующий промокод
                return {
                    'success': True,
                    'promo_id': existing_promo.get('id'),
                    'hash_id': hash_id,
                    'promo_code': existing_promo.get('promo_code'),
                    'promo_name': existing_promo.get('promo_name'),
                    'started_at': self.datetime_formatter.to_datetime_string(existing_promo.get('started_at')),
                    'expired_at': self.datetime_formatter.to_datetime_string(existing_promo.get('expired_at')),
                    # Параметры генерации кода
                    'target_user_id': user_id,
                    'permanent': data.get('permanent', False),
                    'use_digits': use_digits,
                    'use_letters': use_letters,
                    'salt': salt,
                    'use_random': use_random
                }
            
            # Создаем промокод
            promo_id = promo_repo.create_promo(
                promo_code=promo_code,
                promo_name=promo_name,
                user_id=user_id,
                salt=salt,
                started_at=started_at,
                expired_at=expired_at,
                hash_id=hash_id
            )
            
            if promo_id:
                return {
                    'success': True,
                    'promo_id': promo_id,
                    'hash_id': hash_id,
                    'promo_code': promo_code,
                    'promo_name': promo_name,
                    'started_at': self.datetime_formatter.to_datetime_string(started_at),
                    'expired_at': self.datetime_formatter.to_datetime_string(expired_at),
                    # Параметры генерации кода
                    'target_user_id': user_id,
                    'permanent': data.get('permanent', False),
                    'use_digits': use_digits,
                    'use_letters': use_letters,
                    'salt': salt,
                    'use_random': use_random
                }
            else:
                return {'error': 'Не удалось создать промокод'}
                
        except Exception as e:
            return {'error': str(e)}
    
    async def modify_promo(self, data: Dict[str, Any], promo_repo: Any) -> Dict[str, Any]:
        """Изменяет промокод"""
        try:
            promo_id = data.get('promo_id')
            if not promo_id:
                return {'error': 'Отсутствует promo_id'}
            
            # Получаем текущий промокод для проверки изменений
            current_promo = promo_repo.get_promo_by_id(promo_id)
            if not current_promo:
                return {'error': 'Промокод не найден'}
            
            # Извлекаем нужные поля из action
            promo_code = data.get('promo_code')
            promo_name = data.get('promo_name')
            target_user_id = data.get('target_user_id')
            started_at = data.get('started_at')
            expired_at = data.get('expired_at')
            expire_seconds = data.get('expire_seconds')
            permanent = data.get('permanent')
            
            # Подготавливаем поля для обновления
            fields = {}
            
            if promo_code is not None:
                fields['promo_code'] = promo_code
            if promo_name is not None:
                fields['promo_name'] = promo_name
            if target_user_id is not None:
                # Обрабатываем target_user_id
                if target_user_id in ['Null', 'Any', '']:
                    fields['user_id'] = None  # Промокод доступен всем
                else:
                    fields['user_id'] = target_user_id  # Промокод привязан к конкретному пользователю
            else:
                # target_user_id не указан - используем настройку по умолчанию
                if self.default_global_promos:
                    fields['user_id'] = None  # Глобальный промокод
                else:
                    # Берем user_id из события (если есть)
                    user_id = data.get('user_id')
                    if user_id is not None:
                        fields['user_id'] = user_id  # Привязываем к пользователю из события
            if started_at is not None:
                fields['started_at'] = self.datetime_formatter.parse(started_at)
            if expired_at is not None:
                fields['expired_at'] = self.datetime_formatter.parse(expired_at)
            
            # Обрабатываем expire_seconds и permanent
            if expire_seconds is not None:
                now = self.datetime_formatter.now_local()
                fields['expired_at'] = now + timedelta(seconds=expire_seconds)
            elif permanent is not None:
                if permanent:
                    fields['started_at'] = datetime(2000, 1, 1)
                    fields['expired_at'] = datetime(2999, 12, 31, 23, 59, 59)
            
            if not fields:
                return {'error': 'Нет полей для обновления'}
            
            # При любых изменениях всегда обновляем хэш
            # Формируем новые данные для генерации хэша только из стабильных полей
            new_data = {
                'promo_name': current_promo.get('promo_name', ''),
                'user_id': current_promo.get('user_id'),
                'salt': current_promo.get('salt', 'default')
            }
            # Обновляем только те поля, которые влияют на хэш
            if 'promo_name' in fields:
                new_data['promo_name'] = fields['promo_name']
            if 'user_id' in fields:
                new_data['user_id'] = fields['user_id']
            
            new_hash_id = self._generate_hash_id(new_data)
            fields['hash_id'] = new_hash_id
            
            # Проверяем, не существует ли уже промокод с новым хэшем
            existing_promo = promo_repo.get_promo_by_hash_id(new_hash_id)
            if existing_promo and existing_promo.get('id') != promo_id:
                return {'error': 'Промокод с такими параметрами уже существует'}
            
            # Обновляем промокод
            success = promo_repo.update_promo(promo_id, **fields)
            
            if success:
                # Получаем обновленные данные для response
                updated_promo = promo_repo.get_promo_by_id(promo_id)
                if updated_promo:
                    return {
                        'success': True,
                        'promo_id': promo_id,
                        'hash_id': updated_promo.get('hash_id'),
                        'promo_code': updated_promo.get('promo_code'),
                        'promo_name': updated_promo.get('promo_name'),
                        'started_at': self.datetime_formatter.to_datetime_string(updated_promo.get('started_at')),
                        'expired_at': self.datetime_formatter.to_datetime_string(updated_promo.get('expired_at')),
                        # Параметры генерации кода
                        'target_user_id': updated_promo.get('user_id'),
                        'permanent': permanent if permanent is not None else (updated_promo.get('started_at') == datetime(2000, 1, 1) and updated_promo.get('expired_at') == datetime(2999, 12, 31, 23, 59, 59)),
                        'use_digits': True,  # По умолчанию для существующих промокодов
                        'use_letters': True,  # По умолчанию для существующих промокодов
                        'salt': updated_promo.get('salt', 'default'),
                        'use_random': False  # По умолчанию детерминированная генерация для существующих
                    }
                else:
                    return {
                        'success': True, 
                        'promo_id': promo_id,
                        # Параметры генерации кода (по умолчанию для существующих)
                        'target_user_id': updated_promo.get('user_id') if updated_promo else None,
                        'permanent': False,  # По умолчанию не постоянный
                        'use_digits': True,  # По умолчанию для существующих промокодов
                        'use_letters': True,  # По умолчанию для существующих промокодов
                        'salt': 'default',  # По умолчанию
                        'use_random': False  # По умолчанию детерминированная генерация
                    }
            else:
                return {'error': 'Промокод не найден или не обновлен'}
                
        except Exception as e:
            return {'error': str(e)}
    
    async def check_promo(self, data: Dict[str, Any], promo_repo: Any) -> Dict[str, Any]:
        """Проверяет доступность промокода"""
        try:
            promo_code = data.get('promo_code')
            user_id = data.get('user_id')
            
            if not promo_code:
                return {'error': 'Отсутствует promo_code'}
            
            if not user_id:
                return {'error': 'Отсутствует user_id'}
            
            # Получаем промокоды по коду
            promos = promo_repo.get_promos_by_filters(promo_code=promo_code)
            
            if not promos:
                return {
                    'promo_available': False,
                    'reason': 'Промокод не найден'
                }
            
            # Проверяем доступность для пользователя
            now = self.datetime_formatter.now_local()
            available_promos = []
            
            for promo in promos:
                # Проверяем, что промокод активен
                if (promo['started_at'] <= now and promo['expired_at'] > now):
                    # Проверяем доступность для пользователя
                    if promo['user_id'] is None or promo['user_id'] == user_id:
                        available_promos.append(promo)
            
            if available_promos:
                # Возвращаем первый доступный промокод
                promo = available_promos[0]
                # Конвертируем datetime в строки для JSON сериализации
                promo_data = {
                    'id': promo.get('id'),
                    'hash_id': promo.get('hash_id'),
                    'promo_code': promo.get('promo_code'),
                    'promo_name': promo.get('promo_name'),
                    'user_id': promo.get('user_id'),
                    'salt': promo.get('salt'),
                    'started_at': self.datetime_formatter.to_datetime_string(promo.get('started_at')),
                    'expired_at': self.datetime_formatter.to_datetime_string(promo.get('expired_at')),
                    'created_at': self.datetime_formatter.to_datetime_string(promo.get('created_at')),
                    'updated_at': self.datetime_formatter.to_datetime_string(promo.get('updated_at'))
                }
                return {
                    'promo_available': True,
                    'promo_data': promo_data
                }
            else:
                return {
                    'promo_available': False,
                    'reason': 'Промокод недоступен для данного пользователя или истек'
                }
                
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_hash_id(self, data: Dict[str, Any]) -> str:
        """Генерирует уникальный хэш-идентификатор для промокода"""
        try:
            # Формируем атрибуты для хэша (только стабильные)
            attributes = {
                'promo_name': data.get('promo_name', ''),
                'user_id': data.get('user_id'),
                'salt': data.get('salt', 'default')
            }
            
            # Генерируем хэш через hash_manager
            return self.hash_manager.generate_hash_from_attributes(**attributes)
            
        except Exception as e:
            raise Exception(f"Не удалось сгенерировать хэш-идентификатор: {e}")

    def _generate_promo_code(self, config: Dict[str, Any]) -> str:
        """Генерирует код промокода на основе конфигурации"""
        try:
            # Параметры генерации
            length = config.get('length', self.default_code_length)
            use_digits = config.get('use_digits', True)
            use_letters = config.get('use_letters', True)
            salt = config.get('salt', 'default')
            use_random = config.get('use_random', False)
            
            # Используем универсальный метод generate_code
            if use_random:
                # Случайная генерация - используем random=True
                return self.hash_manager.generate_code(
                    length=length,
                    use_digits=use_digits,
                    use_letters=use_letters,
                    random=True
                ).upper()
            else:
                # Детерминированная генерация на основе стабильных атрибутов
                return self.hash_manager.generate_code(
                    length=length,
                    use_digits=use_digits,
                    use_letters=use_letters,
                    random=False,
                    salt=salt,
                    user_id=config.get('user_id'),
                    promo_name=config.get('promo_name', '')
                ).upper()
                
        except Exception as e:
            raise Exception(f"Не удалось сгенерировать промокод: {e}")
