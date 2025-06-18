from sqlalchemy import inspect, text

class TableInfoService:
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def get_db_info(self):
        if not self.db_engine:
            return {"db_status": "Unconnected", "status_class": "fail", "tables": []}

        inspector = inspect(self.db_engine)
        tables = inspector.get_table_names()
        return {"db_status": "Connected", "status_class": "success", "tables": tables}

    def get_table_data(self, table_name):
        if not self.db_engine:
            return None

        with self.db_engine.connect() as c:
            query = f"SELECT * FROM {table_name}"
            output = c.execute(text(query))
            rows = []
            column_names = output.keys()
            for row in output.fetchall():
                row_dict = dict(zip(column_names, row))
                rows.append(row_dict)
            
            column_names_query = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION"
            column_names_output = c.execute(text(column_names_query))
            column_names = []
            column_types = []
            for row in column_names_output.fetchall():
                column_name = row[0]
                column_type = row[1]
                column_names.append(column_name)
                column_types.append(column_type)
                
        return {
            "table_name": table_name, 
            "column_names": column_names, 
            "column_types": column_types, 
            "rows": rows
        } 