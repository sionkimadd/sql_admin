class DisposeSQL:

    def __init__(self, db_engine):
        self.__db_engine = db_engine

    def close_connection(self):
        try:
            self.__db_engine.dispose() 
            return "Succeed: Disposed DB"
        except Exception:
            return f"Failed: Undispose DB"
        
    @property
    def db_engine(self):
        return self.__db_engine