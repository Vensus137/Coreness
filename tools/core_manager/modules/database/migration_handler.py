"""Database migration handler - entry point for migration."""

from pathlib import Path

from ..i18n.translator import Translator
from ..ui.colors import Colors
from ..ui.dialogs import confirm
from .config.database_context import DatabaseContext
from .connection.database_connection import DatabaseConnection
from .backup.backup_handler import run_backup
from .docker.compose_finder import ensure_postgres_container_running
from .backup.restore_handler import run_restore_latest
from .migration.migration import UniversalMigration
from .migration.output import MigrationFormatter, MigrationLogger


class MigrationHandler:
    """Handles universal database migrations."""

    def __init__(self, project_root: Path, translator: Translator, config: dict):
        self.project_root = project_root
        self.translator = translator
        self.config = config
        self.formatter = MigrationFormatter()
        self.logger = MigrationLogger()

    def run(self, skip_confirm: bool = False) -> bool:
        """Run database migration. skip_confirm=True when called from update resume step. Returns True on success."""
        print("\n" + "="*60)
        print(Colors.bold(self.translator.get('database.migration_title').center(60)))
        print("="*60 + "\n")

        try:
            # Build context
            context = DatabaseContext(
                project_root=self.project_root,
                database_config=self.config,
                docker_compose_config=self.config.get("docker_compose", {}),
                environment=self.config.get("environment", "prod"),
                deployment_mode=self.config.get("deployment_mode", "docker")
            )

            if context.is_docker_mode():
                ensure_postgres_container_running(
                    self.project_root,
                    context.environment,
                    context.docker_compose_config,
                )

            db_connection = DatabaseConnection(context)
            db_connection.connect()

            db_type = db_connection.db_type
            conn_info = db_connection.get_connection_info()

            print(Colors.info(f"{self.translator.get('database.db_type')}: {db_type.upper()}"))
            if db_type == 'sqlite':
                print(Colors.info(f"{self.translator.get('database.db_path')}: {db_connection.db_path}"))
            else:
                host = conn_info.get('host', 'localhost')
                port = conn_info.get('port', 5432)
                database = conn_info.get('database', 'core_db')
                print(Colors.info(f"{self.translator.get('database.db_connection')}: {host}:{port}/{database}"))

            print()

            if not skip_confirm and not confirm(self.translator.get('database.confirm_migration'), default=True, translator=self.translator):
                print(Colors.info(self.translator.get('messages.cancelled')))
                db_connection.cleanup()
                return False

            print()
            if not run_backup(self.project_root, self.config, self.translator):
                print(Colors.error(f"\n✗ {self.translator.get('database.backup_failed_skip_migration')}"))
                db_connection.cleanup()
                return False
            print()
            migrator = UniversalMigration(db_connection, self.logger, self.formatter, self.translator)
            migrator.migrate_database()
            return True

        except ImportError as e:
            print(Colors.error(f"\n✗ {e}"))
            print(Colors.info(self.translator.get('database.install_dependencies')))
            return False
        except Exception as e:
            print(Colors.error(f"\n✗ {self.translator.get('database.migration_failed')}: {e}"))
            import traceback
            traceback.print_exc()
            print()
            if not run_restore_latest(self.project_root, self.config, self.translator):
                print(Colors.error(self.translator.get("database.restore_failed_manual")))
            return False
        finally:
            try:
                db_connection.cleanup()
            except NameError:
                pass
