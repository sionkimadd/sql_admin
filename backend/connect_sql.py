from sqlalchemy import create_engine, text

class ConnectSQL:

    def __init__(self, db_url):
        if db_url.startswith("mysql://"):
            db_url = db_url.replace("mysql://", "mysql+pymysql://")
            self.__db_engine = create_engine(db_url, echo=False)

    def get_engine(self):
        return self.__db_engine
    
    def select_one(self):
        try:
            with self.__db_engine.connect() as c:
                query = "SELECT 1"
                output = c.execute(text(query))
                output_row = output.fetchone()
                if output_row and output_row[0] == 1:
                    return "Succeed"
                return "Failed: Query SELECT 1"
        except Exception:
            return "Failed: Unconnected DB"
        
    @property
    def db_engine(self):
        return self.__db_engine