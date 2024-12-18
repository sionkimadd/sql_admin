from sqlalchemy import text

class DropTableQuery:
    def __init__(self, db_engine, table_name):
        self.db_engine = db_engine
        self.table_name = table_name

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                query = f"DROP TABLE {self.table_name}"
                c.execute(text(query))
            return f"Succeed: Dropped Table {self.table_name}"
        except Exception:
            return f"Failed: Undropped Table {self.table_name}"