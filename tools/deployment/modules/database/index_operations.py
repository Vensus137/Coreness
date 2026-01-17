"""
Модуль для операций с индексами БД
Пересоздание индексов, удаление старых индексов и constraints
"""

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError


class IndexOperations:
    """Класс для операций с индексами"""
    
    def __init__(self, engine, db_type: str, logger, formatter):
        """
        Инициализация операций с индексами
        """
        self.engine = engine
        self.db_type = db_type
        self.logger = logger
        self.formatter = formatter
    
    def recreate_indexes(self, table_class: Any) -> bool:
        """Пересоздает индексы для таблицы"""
        try:
            table = table_class.__table__
            inspector = inspect(self.engine)
            
            # Получаем существующие индексы
            existing_indexes = {idx['name'] for idx in inspector.get_indexes(table.name)}
            
            # Индексы, определённые в модели
            model_indexes = list(table.indexes)
            
            # Удаляем существующие индексы и constraints
            with self.engine.connect() as conn:
                # Сначала удаляем все типы constraints для PostgreSQL
                if self.db_type == 'postgresql':
                    try:
                        # Check constraints
                        check_constraints = inspector.get_check_constraints(table.name)
                        for constraint in check_constraints:
                            constraint_name = constraint['name']
                            self.formatter.print_info(f"Удаляю check constraint {constraint_name}...")
                            conn.execute(text(f'ALTER TABLE {table.name} DROP CONSTRAINT IF EXISTS "{constraint_name}" CASCADE'))
                        
                        # Unique constraints
                        unique_constraints = inspector.get_unique_constraints(table.name)
                        for constraint in unique_constraints:
                            constraint_name = constraint['name']
                            self.formatter.print_info(f"Удаляю unique constraint {constraint_name}...")
                            conn.execute(text(f'ALTER TABLE {table.name} DROP CONSTRAINT IF EXISTS "{constraint_name}" CASCADE'))
                        
                        # Foreign keys
                        foreign_keys = inspector.get_foreign_keys(table.name)
                        for fk in foreign_keys:
                            fk_name = fk['name']
                            self.formatter.print_info(f"Удаляю foreign key {fk_name}...")
                            conn.execute(text(f'ALTER TABLE {table.name} DROP CONSTRAINT IF EXISTS "{fk_name}" CASCADE'))
                            
                    except Exception as e:
                        self.formatter.print_warning(f"Ошибка при удалении constraints: {e}")
                
                # Затем удаляем индексы
                for idx in existing_indexes:
                    if idx == 'sqlite_autoindex_' + table.name + '_1':
                        continue  # Не трогаем PK
                    try:
                        self.formatter.print_info(f"Удаляю индекс {idx}...")
                        # Используем CASCADE для PostgreSQL
                        if self.db_type == 'postgresql':
                            conn.execute(text(f'DROP INDEX IF EXISTS "{idx}" CASCADE'))
                        else:
                            conn.execute(text(f'DROP INDEX IF EXISTS "{idx}"'))
                    except OperationalError as e:
                        self.formatter.print_warning(f"Ошибка при удалении индекса {idx}: {e}")
            
            # Создаём индексы из модели в отдельных транзакциях
            for idx in model_indexes:
                self.formatter.print_info(f"Создаю индекс {idx.name}...")
                try:
                    # Создаем индекс в отдельной транзакции
                    with self.engine.connect() as idx_conn:
                        idx.create(idx_conn, checkfirst=True)
                        idx_conn.commit()
                    self.formatter.print_success(f"Индекс {idx.name} создан")
                except Exception as e:
                    self.formatter.print_error(f"Ошибка при создании индекса {idx.name}: {e}")
            
            self.formatter.print_success(f"Индексы для таблицы {table.name} успешно пересозданы")
            return True
            
        except Exception as e:
            self.formatter.print_error(f"Ошибка пересоздания индексов для {table_class.__table__.name}: {e}")
            raise
    
    def restore_foreign_keys_in_dependent_tables(self, parent_table_name: str, table_class_map: dict) -> bool:
        """Восстанавливает FK constraints в зависимых таблицах после пересоздания родительской таблицы"""
        try:
            inspector = inspect(self.engine)
            
            # Находим все таблицы, которые имеют FK constraints, ссылающиеся на parent_table_name
            # Ищем через модели SQLAlchemy, а не через inspector, т.к. после CASCADE FK constraints уже удалены
            dependent_tables = {}
            
            for table_name, table_class in table_class_map.items():
                table = table_class.__table__
                # Проверяем все колонки таблицы на наличие FK constraints
                for column in table.columns:
                    for fk in column.foreign_keys:
                        # fk.column.table.name содержит имя таблицы, на которую ссылается FK
                        if fk.column.table.name == parent_table_name:
                            if table_name not in dependent_tables:
                                dependent_tables[table_name] = []
                            dependent_tables[table_name].append({
                                'column': column.name,
                                'fk': fk,
                                'referred_column': fk.column.name
                            })
                            break
            
            if not dependent_tables:
                return True
            
            self.formatter.print_info(f"Восстанавливаю FK constraints в зависимых таблицах: {', '.join(dependent_tables.keys())}")
            
            # Для каждой зависимой таблицы пересоздаем FK constraints из модели
            with self.engine.connect() as conn:
                for dep_table_name, fk_list in dependent_tables.items():
                    for fk_info in fk_list:
                        column_name = fk_info['column']
                        fk = fk_info['fk']
                        referred_column = fk_info['referred_column']
                        
                        # Проверяем, существует ли уже этот FK constraint
                        existing_fks = inspector.get_foreign_keys(dep_table_name)
                        fk_exists = False
                        
                        for existing_fk in existing_fks:
                            if (existing_fk['referred_table'] == parent_table_name and 
                                existing_fk['constrained_columns'] == [column_name]):
                                fk_exists = True
                                break
                        
                        if not fk_exists:
                            # Создаем FK constraint из модели
                            try:
                                fk_name = fk.name or f"{dep_table_name}_{column_name}_fkey"
                                
                                self.formatter.print_info(f"Создаю FK constraint {fk_name} в таблице {dep_table_name} -> {parent_table_name}")
                                
                                # Создаем FK constraint через ALTER TABLE
                                if self.db_type == 'postgresql':
                                    # Проверяем существование constraint через pg_constraint
                                    check_result = conn.execute(text(f"""
                                        SELECT 1 FROM pg_constraint 
                                        WHERE conname = '{fk_name}' 
                                        AND conrelid = '{dep_table_name}'::regclass
                                    """)).fetchone()
                                    
                                    if not check_result:
                                        conn.execute(text(f"""
                                            ALTER TABLE {dep_table_name} 
                                            ADD CONSTRAINT {fk_name} 
                                            FOREIGN KEY ({column_name}) 
                                            REFERENCES {parent_table_name}({referred_column})
                                        """))
                                        conn.commit()
                                        self.formatter.print_success(f"FK constraint {fk_name} создан")
                                    else:
                                        self.formatter.print_info(f"FK constraint {fk_name} уже существует, пропускаю")
                                else:
                                    # Для SQLite просто создаем constraint
                                    conn.execute(text(f"""
                                        ALTER TABLE {dep_table_name} 
                                        ADD CONSTRAINT {fk_name} 
                                        FOREIGN KEY ({column_name}) 
                                        REFERENCES {parent_table_name}({referred_column})
                                    """))
                                    conn.commit()
                                    self.formatter.print_success(f"FK constraint {fk_name} создан")
                            except Exception as e:
                                self.formatter.print_warning(f"Ошибка создания FK constraint в {dep_table_name}: {e}")
            
            return True
            
        except Exception as e:
            self.formatter.print_error(f"Ошибка восстановления FK constraints в зависимых таблицах: {e}")
            return False

