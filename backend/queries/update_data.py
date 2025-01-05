from sqlalchemy import text

class UpdateDataQuery:
    def __init__(self, db_engine, table_name, condition_column, condition_value, target_columns, target_values):
        self.db_engine = db_engine
        self.table_name = table_name
        self.condition_column = condition_column
        self.condition_value = condition_value
        self.target_columns = target_columns
        self.target_values = target_values

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                with c.begin():
                    target_data = ', '.join([f"{column} = {value}" for column, value in zip(self.target_columns, self.target_values)])
                    query = f"UPDATE {self.table_name} SET {target_data} WHERE {self.condition_column} = {self.condition_value}"
                    c.execute(text(query))

            return "Succeed: Data Updated", query
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
            return f"Failed: Data Unupdated - {error_message}", None