from sqlalchemy import text

class CreateTableQuery:
    def __init__(self, db_engine, table_name, columns, foreign_keys):
        self.__db_engine = db_engine
        self.table_name = table_name
        self.columns = columns
        self.foreign_keys = foreign_keys

    def execute(self):
        try:
            with self.__db_engine.connect() as c:
                column_defs = []
                for name, type, constraints in self.columns:
                    if name and type:
                        if constraints:
                            constraints_str = " ".join(constraints)
                        else:
                            constraints_str = ""
                        column_defs.append(f"{name} {type} {constraints_str}")
                
                column_defs.extend(self.foreign_keys)
                
                query = f"CREATE TABLE {self.table_name} ({', '.join(column_defs)});"
                c.execute(text(query))
            return "Succeed: Created Table", query
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
            return f"Failed: Uncreated Table - {error_message}", None