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
            return f"Succeed: Dropped Table {self.table_name}", query
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
            return f"Failed: Undropped Table {self.table_name} - {error_message}", None