import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_directory: str):
        self.db_directory = db_directory
        os.makedirs(self.db_directory, exist_ok=True)
        self.conn = None

    def set_file(self, filename: str) -> bool:
        """Returns True if successful, False if file already exists."""
        filepath = os.path.join(self.db_directory, f"{filename}.sqlite")
        
        if os.path.exists(filepath):
            return False
            
        self.conn = sqlite3.connect(filepath, check_same_thread=False)
        self._create_schema()
        return True

    def _create_schema(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                timestamp DATETIME,
                device_name TEXT,
                channel INTEGER,
                metric TEXT,
                value REAL
            )
        ''')
        self.conn.commit()

    def insert_reading(self, timestamp: str, device_name: str, channel: int, metric: str, value: float):
        if not self.conn:
            return # Fails silently if no DB is configured, or you could raise an Exception
            
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO readings VALUES (?, ?, ?, ?, ?)",
            (timestamp, device_name, channel, metric, value)
        )
        self.conn.commit()