from sqlalchemy import text

class InsertDataQuery:
    def __init__(self, db_engine, table_name, columns, data):
        self.db_engine = db_engine
        self.table_name = table_name
        self.columns = columns
        self.data = data

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                columns_str = ", ".join(self.columns)
                values_str = ", ".join([f":{column}" for column in self.columns])
                query = f"INSERT INTO {self.table_name} ({columns_str}) VALUES ({values_str})"
                
                for row in self.data:
                    c.execute(text(query).bindparams(**row))
                c.commit()
                
            return "Succeed: Inserted Data"
        except Exception:
            return f"Failed: Uninserted Data"