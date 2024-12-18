from sqlalchemy import text

class CreateTableQuery:
    def __init__(self, db_engine, table_name, columns):
        self.__db_engine = db_engine
        self.table_name = table_name
        self.columns = columns

    def execute(self):
        column_defs = [f"{name} {type}" for name, type in self.columns]
        query = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(column_defs)});"
        
        try:
            with self.__db_engine.connect() as c:
                c.execute(text(query))
            return "Succeed: Created Table"
        except Exception:
            return "Failed: Uncreated Table"