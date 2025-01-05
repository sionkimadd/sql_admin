from sqlalchemy import text

class DeleteDataQuery:
    def __init__(self, db_engine, table_name, conditions):
        self.db_engine = db_engine
        self.table_name = table_name
        self.conditions = conditions

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                with c.begin():
                    condition_str = " ".join(self.conditions)
                    query = f"DELETE FROM {self.table_name} WHERE {condition_str}"
                    output = c.execute(text(query))
                    rows_deleted = output.rowcount

                if rows_deleted > 0:
                    return f"Succeed: Deleted {rows_deleted} Row(s)", query
                else:
                    return "Warning: Unmatching Data to Delete.", query
        except Exception as e:
            error_message = str(e)

            if "(pymysql.err.OperationalError)" in error_message:
                error_message = error_message.replace("(pymysql.err.OperationalError)", "")

            if "(pymysql.err.ProgrammingError)" in error_message:
                error_message = error_message.replace("(pymysql.err.ProgrammingError) ", "")

            if "(Background on this error at: https://sqlalche.me/e/20/e3q8)" in error_message:
                error_message = error_message.replace("(Background on this error at: https://sqlalche.me/e/20/e3q8)", "")

            if "(Background on this error at: https://sqlalche.me/e/20/f405)" in error_message:
                error_message = error_message.replace("(Background on this error at: https://sqlalche.me/e/20/f405)", "")

            error_message = error_message.strip()
            return f"Failed: Data Not Deleted - {error_message}", None