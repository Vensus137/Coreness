"""
Module for view operations in PostgreSQL
Creating views for access control at DB level
"""

from sqlalchemy import inspect, text


class ViewOperations:
    """Class for view operations (PostgreSQL only)"""
    
    # =============================================================================
    # SIMPLE VIEWS - tables with direct tenant_id
    # =============================================================================
    
    # Pre-prepared views for tables with direct tenant_id
    # Format: view_name -> SQL for creation
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
    # COMPLEX VIEWS - tables linked to tenant_id through other tables (joins)
    # =============================================================================
    
    # Views for tables that are linked to tenant_id through intermediate tables
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
        """Combined dictionary of all views (simple + complex)"""
        return {**self.SIMPLE_TENANT_VIEWS, **self.COMPLEX_TENANT_VIEWS}
    
    def __init__(self, engine, db_type: str, logger):
        """
        Initialize view operations
        """
        self.engine = engine
        self.db_type = db_type
        self.logger = logger
    
    def drop_all_views(self) -> bool:
        """
        Drops all system views for PostgreSQL (ignored for SQLite)
        Drops only views from TENANT_VIEWS list (SIMPLE_TENANT_VIEWS + COMPLEX_TENANT_VIEWS)
        """
        # Views are dropped only for PostgreSQL
        if self.db_type != 'postgresql':
            return True
        
        try:
            # Get list of system views we create
            system_views = list(self.TENANT_VIEWS.keys())
            
            if not system_views:
                self.logger.info("No system views found for deletion")
                return True
            
            inspector = inspect(self.engine)
            existing_views = set(inspector.get_view_names())
            
            # Filter only views that exist in DB and are in our list
            views_to_drop = [view_name for view_name in system_views if view_name in existing_views]
            
            if not views_to_drop:
                self.logger.info("No system views found in DB for deletion")
                return True
            
            self.logger.info(f"Dropping {len(views_to_drop)} system views...")
            dropped_count = 0
            
            with self.engine.begin() as conn:
                for view_name in views_to_drop:
                    try:
                        # Use CASCADE to remove dependencies (e.g., if other views depend on this)
                        # CASCADE removes not only the view itself, but all objects that depend on it
                        conn.execute(text(f'DROP VIEW IF EXISTS {view_name} CASCADE'))
                        self.logger.info(f"View {view_name} dropped")
                        dropped_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to drop view {view_name}: {e}")
                        # Continue dropping other views
                        continue
            
            self.logger.info(f"Dropped system views: {dropped_count} out of {len(views_to_drop)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error dropping views: {e}")
            return False
    
    def create_all_views(self) -> bool:
        """
        Creates all views for PostgreSQL (ignored for SQLite)
        """
        # Views are created only for PostgreSQL
        if self.db_type != 'postgresql':
            self.logger.info("Views are created only for PostgreSQL, skipping")
            return True
        
        try:
            inspector = inspect(self.engine)
            existing_views = set(inspector.get_view_names())
            
            created_count = 0
            updated_count = 0
            
            # First create simple views
            self.logger.info("Creating simple views (direct tenant_id)...")
            for view_name, view_sql in self.SIMPLE_TENANT_VIEWS.items():
                try:
                    with self.engine.begin() as conn:
                        conn.execute(text(view_sql))
                    
                    if view_name in existing_views:
                        self.logger.info(f"View {view_name} updated")
                        updated_count += 1
                    else:
                        self.logger.info(f"View {view_name} created")
                        created_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error creating view {view_name}: {e}")
                    # Don't interrupt process, continue creating other views
                    continue
            
            # Then create complex views (with joins)
            self.logger.info("Creating complex views (via joins)...")
            for view_name, view_sql in self.COMPLEX_TENANT_VIEWS.items():
                try:
                    with self.engine.begin() as conn:
                        conn.execute(text(view_sql))
                    
                    if view_name in existing_views:
                        self.logger.info(f"View {view_name} updated")
                        updated_count += 1
                    else:
                        self.logger.info(f"View {view_name} created")
                        created_count += 1
                        
                except Exception as e:
                    self.logger.error(f"Error creating view {view_name}: {e}")
                    # Don't interrupt process, continue creating other views
                    continue
            
            if created_count > 0 or updated_count > 0:
                self.logger.info(f"Views created: {created_count} new, {updated_count} updated")
            
            # Create user role and grant permissions on all views
            self._setup_user_role()
            
            # Create admin role and grant SELECT permissions on all tables
            self._setup_admin_role()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating views: {e}")
            return False
    
    def _setup_user_role(self) -> bool:
        """
        Creates user role and grants SELECT permissions on all views
        """
        if self.db_type != 'postgresql':
            return True
        
        try:
            all_view_names = list(self.TENANT_VIEWS.keys())
            
            with self.engine.begin() as conn:
                # Create user role if it doesn't exist
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'user') THEN
                            CREATE ROLE "user";
                        END IF;
                    END
                    $$;
                """))
                
                # IMPORTANT: Grant permissions on public schema itself (USAGE - for access to schema objects)
                conn.execute(text('GRANT USAGE ON SCHEMA public TO "user"'))
                
                # Grant SELECT permissions on all views explicitly (only on our views from list)
                # Important: re-grant permissions each time, so they exist even if view was dropped and recreated
                # (on DROP VIEW permissions are removed, on CREATE OR REPLACE VIEW - preserved only if view existed)
                for view_name in all_view_names:
                    try:
                        conn.execute(text(f'GRANT SELECT ON {view_name} TO "user"'))
                    except Exception as e:
                        self.logger.warning(f"Error granting permissions on {view_name} for user role: {e}")
                        continue
            
            self.logger.info(f"User role created/updated, USAGE permissions on public schema and SELECT granted explicitly on {len(all_view_names)} views")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up user role: {e}")
            return False
    
    def _setup_admin_role(self) -> bool:
        """
        Creates admin role and grants SELECT permissions on all tables and views (current and future)
        """
        if self.db_type != 'postgresql':
            return True
        
        try:
            with self.engine.begin() as conn:
                # Create admin role if it doesn't exist
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin') THEN
                            CREATE ROLE admin;
                        END IF;
                    END
                    $$;
                """))
                
                # IMPORTANT: Grant permissions on public schema itself (USAGE - for access to schema objects)
                conn.execute(text('GRANT USAGE ON SCHEMA public TO admin'))
                
                # Grant SELECT permissions on all current tables and views
                conn.execute(text('GRANT SELECT ON ALL TABLES IN SCHEMA public TO admin'))
                
                # Grant permissions on future tables and views (ALTER DEFAULT PRIVILEGES)
                conn.execute(text('''
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                        GRANT SELECT ON TABLES TO admin;
                '''))
                
                # Grant permissions to modify view_access table (INSERT, UPDATE, DELETE)
                conn.execute(text('GRANT INSERT, UPDATE, DELETE ON view_access TO admin'))
            
            self.logger.info("Admin role created/updated, USAGE permissions on public schema and SELECT on all tables and views (current and future), INSERT/UPDATE/DELETE permissions on view_access")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up admin role: {e}")
            return False
    
    def view_exists(self, view_name: str) -> bool:
        """
        Checks if view exists
        """
        if self.db_type != 'postgresql':
            return False
        
        try:
            inspector = inspect(self.engine)
            existing_views = inspector.get_view_names()
            return view_name in existing_views
        except Exception as e:
            self.logger.warning(f"Error checking view existence {view_name}: {e}")
            return False
    
    def drop_view(self, view_name: str) -> bool:
        """
        Drops view
        """
        if self.db_type != 'postgresql':
            self.logger.warning(f"Views are dropped only for PostgreSQL, skipping {view_name}")
            return False
        
        try:
            if not self.view_exists(view_name):
                self.logger.warning(f"View {view_name} does not exist")
                return False
            
            with self.engine.begin() as conn:
                conn.execute(text(f'DROP VIEW IF EXISTS {view_name}'))
            
            self.logger.info(f"View {view_name} dropped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error dropping view {view_name}: {e}")
            return False

