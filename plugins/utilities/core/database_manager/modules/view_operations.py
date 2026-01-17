"""
Модуль для операций с view в PostgreSQL
Создание view для контроля доступа на уровне БД
"""

from sqlalchemy import inspect, text


class ViewOperations:
    """Класс для операций с view (только для PostgreSQL)"""
    
    # =============================================================================
    # ПРОСТЫЕ VIEW - таблицы с прямым tenant_id
    # =============================================================================
    
    # Заранее подготовленные view для таблиц с прямым tenant_id
    # Формат: имя_view -> SQL для создания
    SIMPLE_TENANT_VIEWS = {
        'v_tenant': """
            create or replace view v_tenant as
            select t.*
              from tenant t
                   inner join view_access acc
                       on (acc.tenant_id = t.id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_tenant_storage': """
            create or replace view v_tenant_storage as
            select st.*
              from tenant_storage st
                   inner join view_access acc
                       on (acc.tenant_id = st.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_user_storage': """
            create or replace view v_user_storage as
            select us.*
              from user_storage us
                   inner join view_access acc
                       on (acc.tenant_id = us.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_tenant_user': """
            create or replace view v_tenant_user as
            select tu.*
              from tenant_user tu
                   inner join view_access acc
                       on (acc.tenant_id = tu.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_bot': """
            create or replace view v_bot as
            select b.*
              from bot b
                   inner join view_access acc
                       on (acc.tenant_id = b.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_scenario': """
            create or replace view v_scenario as
            select s.*
              from scenario s
                   inner join view_access acc
                       on (acc.tenant_id = s.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_invoice': """
            create or replace view v_invoice as
            select i.*
              from invoice i
                   inner join view_access acc
                       on (acc.tenant_id = i.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_vector_storage': """
            create or replace view v_vector_storage as
            select vs.*
              from vector_storage vs
                   inner join view_access acc
                       on (acc.tenant_id = vs.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
    }
    
    # =============================================================================
    # СЛОЖНЫЕ VIEW - таблицы, связанные с tenant_id через другие таблицы (джойны)
    # =============================================================================
    
    # View для таблиц, которые связаны с tenant_id через промежуточные таблицы
    COMPLEX_TENANT_VIEWS = {
        'v_bot_command': """
            create or replace view v_bot_command as
            select bc.*
              from bot_command bc
                   inner join bot b on bc.bot_id = b.id
                   inner join view_access acc
                       on (acc.tenant_id = b.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_scenario_trigger': """
            create or replace view v_scenario_trigger as
            select st.*
              from scenario_trigger st
                   inner join scenario s on st.scenario_id = s.id
                   inner join view_access acc
                       on (acc.tenant_id = s.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_scenario_step': """
            create or replace view v_scenario_step as
            select ss.*
              from scenario_step ss
                   inner join scenario s on ss.scenario_id = s.id
                   inner join view_access acc
                       on (acc.tenant_id = s.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
        'v_scenario_step_transition': """
            create or replace view v_scenario_step_transition as
            select sst.*
              from scenario_step_transition sst
                   inner join scenario_step ss on sst.step_id = ss.id
                   inner join scenario s on ss.scenario_id = s.id
                   inner join view_access acc
                       on (acc.tenant_id = s.tenant_id or acc.tenant_id = 0)
                      and acc.login = current_user
        """,
    }
    
    @property
    def TENANT_VIEWS(self):
        """Объединенный словарь всех view (простые + сложные)"""
        return {**self.SIMPLE_TENANT_VIEWS, **self.COMPLEX_TENANT_VIEWS}
    
    def __init__(self, engine, db_type: str, logger):
        """
        Инициализация операций с view
        """
        self.engine = engine
        self.db_type = db_type
        self.logger = logger
    
    def drop_all_views(self) -> bool:
        """
        Удаляет все системные view для PostgreSQL (для SQLite игнорируется)
        Удаляет только view из списка TENANT_VIEWS (SIMPLE_TENANT_VIEWS + COMPLEX_TENANT_VIEWS)
        """
        # View удаляются только для PostgreSQL
        if self.db_type != 'postgresql':
            return True
        
        try:
            # Получаем список системных view, которые мы создаем
            system_views = list(self.TENANT_VIEWS.keys())
            
            if not system_views:
                self.logger.info("Системные view для удаления не найдены")
                return True
            
            inspector = inspect(self.engine)
            existing_views = set(inspector.get_view_names())
            
            # Фильтруем только те view, которые существуют в БД и есть в нашем списке
            views_to_drop = [view_name for view_name in system_views if view_name in existing_views]
            
            if not views_to_drop:
                self.logger.info("Системные view для удаления не найдены в БД")
                return True
            
            self.logger.info(f"Удаление {len(views_to_drop)} системных view...")
            dropped_count = 0
            
            with self.engine.begin() as conn:
                for view_name in views_to_drop:
                    try:
                        # Используем CASCADE для удаления зависимостей (например, если другие view зависят от этого)
                        # CASCADE удаляет не только сам view, но и все объекты, которые от него зависят
                        conn.execute(text(f'DROP VIEW IF EXISTS {view_name} CASCADE'))
                        self.logger.info(f"View {view_name} удалена")
                        dropped_count += 1
                    except Exception as e:
                        self.logger.warning(f"Не удалось удалить view {view_name}: {e}")
                        # Продолжаем удаление других view
                        continue
            
            self.logger.info(f"Удалено системных view: {dropped_count} из {len(views_to_drop)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления view: {e}")
            return False
    
    def create_all_views(self) -> bool:
        """
        Создаёт все view для PostgreSQL (для SQLite игнорируется)
        """
        # View создаются только для PostgreSQL
        if self.db_type != 'postgresql':
            self.logger.info("View создаются только для PostgreSQL, пропускаем")
            return True
        
        try:
            inspector = inspect(self.engine)
            existing_views = set(inspector.get_view_names())
            
            created_count = 0
            updated_count = 0
            
            # Сначала создаем простые view
            self.logger.info("Создание простых view (прямой tenant_id)...")
            for view_name, view_sql in self.SIMPLE_TENANT_VIEWS.items():
                try:
                    with self.engine.begin() as conn:
                        conn.execute(text(view_sql))
                    
                    if view_name in existing_views:
                        self.logger.info(f"View {view_name} обновлена")
                        updated_count += 1
                    else:
                        self.logger.info(f"View {view_name} создана")
                        created_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Ошибка создания view {view_name}: {e}")
                    # Не прерываем процесс, продолжаем создание других view
                    continue
            
            # Затем создаем сложные view (с джойнами)
            self.logger.info("Создание сложных view (через джойны)...")
            for view_name, view_sql in self.COMPLEX_TENANT_VIEWS.items():
                try:
                    with self.engine.begin() as conn:
                        conn.execute(text(view_sql))
                    
                    if view_name in existing_views:
                        self.logger.info(f"View {view_name} обновлена")
                        updated_count += 1
                    else:
                        self.logger.info(f"View {view_name} создана")
                        created_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Ошибка создания view {view_name}: {e}")
                    # Не прерываем процесс, продолжаем создание других view
                    continue
            
            if created_count > 0 or updated_count > 0:
                self.logger.info(f"View созданы: {created_count} новых, {updated_count} обновлено")
            
            # Создаем роль user и выдаем права на все view
            self._setup_user_role()
            
            # Создаем роль admin и выдаем права SELECT на все таблицы
            self._setup_admin_role()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании view: {e}")
            return False
    
    def _setup_user_role(self) -> bool:
        """
        Создает роль user и выдает права SELECT на все view
        """
        if self.db_type != 'postgresql':
            return True
        
        try:
            all_view_names = list(self.TENANT_VIEWS.keys())
            
            with self.engine.begin() as conn:
                # Создаем роль user если её нет
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'user') THEN
                            CREATE ROLE "user";
                        END IF;
                    END
                    $$;
                """))
                
                # ВАЖНО: Выдаем права на саму схему public (USAGE - для доступа к объектам схемы)
                conn.execute(text('GRANT USAGE ON SCHEMA public TO "user"'))
                
                # Выдаем права SELECT на все view явно (только на наши view из списка)
                # Важно: перевыдаем права каждый раз, чтобы они были даже если view был удален и создан заново
                # (при DROP VIEW права удаляются, при CREATE OR REPLACE VIEW - сохраняются только если view существовал)
                for view_name in all_view_names:
                    try:
                        conn.execute(text(f'GRANT SELECT ON {view_name} TO "user"'))
                    except Exception as e:
                        self.logger.warning(f"Ошибка выдачи прав на {view_name} для роли user: {e}")
                        continue
            
            self.logger.info(f"Роль user создана/обновлена, права USAGE на схему public и SELECT выданы явно на {len(all_view_names)} view")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при настройке роли user: {e}")
            return False
    
    def _setup_admin_role(self) -> bool:
        """
        Создает роль admin и выдает права SELECT на все таблицы и view (текущие и будущие)
        """
        if self.db_type != 'postgresql':
            return True
        
        try:
            with self.engine.begin() as conn:
                # Создаем роль admin если её нет
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin') THEN
                            CREATE ROLE admin;
                        END IF;
                    END
                    $$;
                """))
                
                # ВАЖНО: Выдаем права на саму схему public (USAGE - для доступа к объектам схемы)
                conn.execute(text('GRANT USAGE ON SCHEMA public TO admin'))
                
                # Выдаем права SELECT на все текущие таблицы и view
                conn.execute(text('GRANT SELECT ON ALL TABLES IN SCHEMA public TO admin'))
                
                # Выдаем права на будущие таблицы и view (ALTER DEFAULT PRIVILEGES)
                conn.execute(text('''
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                        GRANT SELECT ON TABLES TO admin;
                '''))
                
                # Выдаем права на изменение таблицы view_access (INSERT, UPDATE, DELETE)
                conn.execute(text('GRANT INSERT, UPDATE, DELETE ON view_access TO admin'))
            
            self.logger.info("Роль admin создана/обновлена, права USAGE на схему public и SELECT на все таблицы и view (текущие и будущие), права INSERT/UPDATE/DELETE на view_access")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при настройке роли admin: {e}")
            return False
    
    def view_exists(self, view_name: str) -> bool:
        """
        Проверяет существование view
        """
        if self.db_type != 'postgresql':
            return False
        
        try:
            inspector = inspect(self.engine)
            existing_views = inspector.get_view_names()
            return view_name in existing_views
        except Exception as e:
            self.logger.warning(f"Ошибка проверки существования view {view_name}: {e}")
            return False
    
    def drop_view(self, view_name: str) -> bool:
        """
        Удаляет view
        """
        if self.db_type != 'postgresql':
            self.logger.warning(f"View удаляются только для PostgreSQL, пропускаем {view_name}")
            return False
        
        try:
            if not self.view_exists(view_name):
                self.logger.warning(f"View {view_name} не существует")
                return False
            
            with self.engine.begin() as conn:
                conn.execute(text(f'DROP VIEW IF EXISTS {view_name}'))
            
            self.logger.info(f"View {view_name} удалена")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления view {view_name}: {e}")
            return False

