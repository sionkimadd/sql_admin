from sqlalchemy import text

class SortingTableQuery:
    def __init__(self, db_engine, table_name, order_columns, order_sortings, select_columns):
        self.db_engine = db_engine
        self.table_name = table_name
        self.order_columns = order_columns
        self.order_sortings = order_sortings
        self.select_columns = select_columns

    def execute(self):
        try:
            with self.db_engine.connect() as c:
                query = f"SELECT {", ".join(self.select_columns)} FROM {self.table_name}"
                orders = []
                for col, sor in zip(self.order_columns, self.order_sortings):
                    order = f"{col} {sor}"
                    orders.append(order)
                query += f" ORDER BY {", ".join(orders)}"
                output = c.execute(text(query))
                rows = output.fetchall()
                column_names = list(output.keys())
            return "Succeed: Sorted Table", query, rows, column_names
        except Exception:
            return "Failed: Unsorted Table", query, [], []
