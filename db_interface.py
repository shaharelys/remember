import sqlite3
from typing import List, Dict, Any, Optional
import json


class DatabaseInterface:
    def __init__(self, db_path: str = "whatsapp.db"):
        self.db_path = db_path
        self._initialize_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)

    def _initialize_database(self):
        """Create the necessary table if it doesn't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            embeddings TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        conn.close()

    def get_messages_by_sender(self, sender: str) -> List[Dict[str, Any]]:
        """Retrieve messages sent by a specific sender."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        SELECT content, embeddings, timestamp
        FROM messages
        WHERE sender = ?
        ''', (sender,))

        rows = cursor.fetchall()
        messages = []
        for row in rows:
            content, embeddings_json, timestamp = row
            embeddings = json.loads(embeddings_json)
            messages.append({
                'message': content,
                'embeddings': embeddings,
                'date': timestamp
            })

        conn.close()
        return messages

    def get_all_messages(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
                SELECT sender, content, timestamp
                FROM messages
                ''', ())

        rows = cursor.fetchall()
        messages = []
        for row in rows:
            sender, content, timestamp = row
            messages.append({
                'sender': sender,
                'message': content,
                'date': timestamp
            })
        conn.close()
        return messages


    def save_message(self, sender: str, message: str, embeddings: List[float]) -> bool:
        """Save a message to the database."""
        conn = self._get_connection()

        try:
            cursor = conn.cursor()
            embeddings_json = json.dumps(embeddings)

            cursor.execute('''
            INSERT INTO messages (sender, content, embeddings) 
            VALUES (?, ?, ?)
            ''', (sender, message, embeddings_json))

            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error saving message: {e}")
            return False
        finally:
            conn.close()
