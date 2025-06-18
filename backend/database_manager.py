import time
import secrets
import hashlib
from sqlalchemy import create_engine, text

class DatabaseManager:
    def __init__(self):
        self.db_connections = {}

    def generate_session_key(self):
        current_time = str(time.time_ns())
        random_1 = secrets.token_hex(8)
        random_2 = secrets.token_hex(8)
        random_3 = secrets.token_hex(8)
        raw_session_key = f"{current_time}_{random_1}_{random_2}_{random_3}"
        return self._hash_session_key(raw_session_key)

    def _hash_session_key(self, raw_session_key):
        hashed_session_key = hashlib.sha512(raw_session_key.encode()).hexdigest()
        return hashed_session_key

    def connect_database(self, connection_mode, **kwargs):
        db_url = None
        
        if connection_mode == "url":
            db_url = kwargs.get("db_url", "").strip()
            if not db_url:
                return None, "Failed: Required DB URL"
                
        elif connection_mode == "custom":
            username = kwargs.get("username", "").strip()
            password = kwargs.get("password", "").strip()
            host = kwargs.get("host", "").strip()
            port = kwargs.get("port", "").strip()
            database = kwargs.get("database", "").strip()
            
            if not all([username, password, host, port, database]):
                return None, "Failed: Required custom connection details"
                
            db_url = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"

        try:
            if db_url.startswith("mysql://"):
                db_url = db_url.replace("mysql://", "mysql+pymysql://")

            engine = create_engine(db_url, echo=False)

            with engine.connect() as c:
                c.execute(text("SELECT 1"))

            session_key = self.generate_session_key()
            self.db_connections[session_key] = {"engine": engine}

            return session_key, "Succeed: Connected DB"
            
        except Exception as e:
            return None, f"Failed: {str(e)}"

    def get_db_engine(self, session_key):
        if not session_key or session_key not in self.db_connections:
            return None
        return self.db_connections[session_key]["engine"]

    def dispose_database(self, session_key):
        if not session_key or session_key not in self.db_connections:
            return "Failed: No Active DB Connection"

        if session_key in self.db_connections:
            self.db_connections[session_key]["engine"].dispose()
            del self.db_connections[session_key]
            return "Succeed: Disposed DB"
        else:
            return "Failed: No Active DB Connection" 