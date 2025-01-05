from sqlalchemy import text

class ModifyTableQuery:
    def __init__(self, db_engine, table_name, command, column_name, column_type, column_new_name):
        self.db_engine = db_engine
        self.table_name = table_name
        self.command = command
        self.column_name = column_name
        self.column_type = column_type
        self.column_new_name = column_new_name

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                if self.command == "ADD":
                    query = f"ALTER TABLE {self.table_name} ADD COLUMN {self.column_name} {self.column_type}"
                elif self.command == "DROP":
                    query = f"ALTER TABLE {self.table_name} DROP COLUMN {self.column_name}"
                elif self.command == "MODIFY":
                    query = f"ALTER TABLE {self.table_name} MODIFY COLUMN {self.column_name} {self.column_type}"
                elif self.command == "RENAME":
                    query = f"ALTER TABLE {self.table_name} RENAME COLUMN {self.column_name} TO {self.column_new_name}"
                else:
                    return f"Failed: Wrong Command", None
                c.execute(text(query))

            return "Success: Modified Table", query
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
            return f"Failed: Unmodified Table - {error_message}", None