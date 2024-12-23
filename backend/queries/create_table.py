from sqlalchemy import text

class CreateTableQuery:
    def __init__(self, db_engine, table_name, columns):
        self.__db_engine = db_engine
        self.table_name = table_name
        self.columns = columns

    def execute(self):
        try:
            with self.__db_engine.connect() as c:
                column_defs = [f"{name} {type}" for name, type in self.columns]
                query = f"CREATE TABLE {self.table_name} ({', '.join(column_defs)});"
                c.execute(text(query))
            return "Succeed: Created Table", query
        except Exception:
            return "Failed: Uncreated Table", None