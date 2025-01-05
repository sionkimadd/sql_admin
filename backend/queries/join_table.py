from sqlalchemy import text

class JoinTableQuery:
    def __init__(self, db_engine, table_name, join_types, join_tables, join_conditions, select_columns, where_conditions):
        self.db_engine = db_engine
        self.table_name = table_name
        self.join_types = join_types
        self.join_tables = join_tables
        self.join_conditions = join_conditions
        self.select_columns = select_columns
        self.where_conditions = where_conditions

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                query = f"SELECT {', '.join(self.select_columns)} FROM {self.table_name}"
                for join_type, join_table, join_condition in zip(self.join_types, self.join_tables, self.join_conditions):
                    query += f" {join_type} JOIN {join_table} ON {join_condition}"
                if self.where_conditions:
                    query += f" WHERE {' AND '.join(self.where_conditions)}"
                output = c.execute(text(query))
                rows = output.fetchall()
                column_names = list(output.keys())
            return "Succeed: Join Table", query, rows, column_names
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
            return f"Failed: Unjoin Table - {error_message}", query, [], []