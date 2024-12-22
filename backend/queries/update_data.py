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
                target_data = ", ".join([f"{column} = '{value}'" for column, value in zip(self.target_columns, self.target_values)])
                query = f"UPDATE {self.table_name} SET {target_data} WHERE {self.condition_column} = '{self.condition_value}'"
                c.execute(text(query))
                c.commit()
            return "Succeed: Data Updated"
        except Exception:
            return f"Failed: Data Unupdated"