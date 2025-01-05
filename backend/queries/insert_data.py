from sqlalchemy import text

class InsertDataQuery:
    def __init__(self, db_engine, table_name, column_names, data):
        self.db_engine = db_engine
        self.table_name = table_name
        self.column_names = column_names
        self.data = data

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                with c.begin():
                    columns_str = ", ".join(self.column_names)
                    values_list = []
                    for row in self.data:
                        parsed_values = []
                        for value in row.values():
                            if value is None or value == "":
                                parsed_values.append("NULL")
                            else:
                                parsed_values.append(f"'{value}'")
                        row_str = ", ".join(parsed_values)
                        values_list.append(f"({row_str})")
                    values_str = ", ".join(values_list)
                    query = f"INSERT INTO {self.table_name} ({columns_str}) VALUES {values_str}"
                    c.execute(text(query))
                
            return "Succeed: Inserted Data", query
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
            return f"Failed: Uninserted Data - {error_message}", None