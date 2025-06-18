from sqlalchemy import text

class QueryExecutor:
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def execute_custom_query(self, sql_query):
        if not self.db_engine:
            return "Failed: No Active DB Connection", None, None, None
        
        if not sql_query or not sql_query.strip():
            return "Failed: Empty Query", None, None, None
        
        try:
            with self.db_engine.connect() as c:
                is_select = sql_query.strip().upper().startswith("SELECT")
                
                if is_select:
                    result = c.execute(text(sql_query))
                    rows = result.fetchall()
                    column_names = result.keys()
                    serializable_rows = [dict(row._mapping) for row in rows]
                    return "Succeed: Query executed successfully", sql_query, serializable_rows, list(column_names)
                else:
                    with c.begin():
                        result = c.execute(text(sql_query))
                        return "Succeed: Query executed successfully", sql_query, None, None
        except Exception as e:
            return f"Failed: {str(e)}", None, None, None 