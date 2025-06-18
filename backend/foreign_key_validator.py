from sqlalchemy import inspect

class ForeignKeyValidator:
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def validate_foreign_key(self, foreign_table, foreign_column):
        inspector = inspect(self.db_engine)
        
        if foreign_table not in inspector.get_table_names():
            return False, f"Referenced Table {foreign_table} Unexist"
        
        columns_info = inspector.get_columns(foreign_table)
        indexes = inspector.get_indexes(foreign_table)
        primary_keys = inspector.get_pk_constraint(foreign_table)["constrained_columns"]
        unique_keys = [index["column_names"] for index in indexes if index.get("unique", False)]

        is_primary_key = foreign_column in primary_keys
        is_indexed = any(index["column_names"] == [foreign_column] for index in indexes)
        is_unique_key = [foreign_column] in unique_keys

        is_valid_foreign_key = False
        for col in columns_info:
            if col["name"] == foreign_column:
                if is_primary_key or is_indexed or is_unique_key:
                    is_valid_foreign_key = True
                    break

        if not is_valid_foreign_key:
            return False, f"Referenced Column {foreign_column} in Table {foreign_table} without index, unique key, or primary key"

        return True, "" 