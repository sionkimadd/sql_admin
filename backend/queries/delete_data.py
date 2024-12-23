from sqlalchemy import text

class DeleteDataQuery:
    def __init__(self, db_engine, table_name, conditions):
        self.db_engine = db_engine
        self.table_name = table_name
        self.conditions = conditions

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                condition_str = " ".join(self.conditions)
                query = f"DELETE FROM {self.table_name} WHERE {condition_str}"
                output = c.execute(text(query))
                rows_deleted = output.rowcount
                c.commit()
                if rows_deleted > 0:
                    return f"Succeed: Deleted {rows_deleted} Row(s)", query
                else:
                    return "Warning: Unmatching Data to Delete.", query
        except Exception:
            return "Failed: Data Not Deleted", None