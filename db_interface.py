import mysql.connector
from mysql.connector import Error
from typing import List, Dict, Optional, Any, Union
from mysql.connector.connection import MySQLConnection
import json

class DatabaseInterface:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.db_config: Dict[str, str] = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }

    def _get_connection(self) -> Optional[MySQLConnection]:
        try:
            connection = mysql.connector.connect(**self.db_config)
            if connection.is_connected():
                return connection
        except Error as e:
            print(f"Error: {e}")
            return None
        
    def get_messages_by_sender(self, sender: str) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        if conn is None:
            print("Failed to connect to the database.")
            return []

        cursor = conn.cursor()
        cursor.execute('''
        SELECT message, embeddings, date
        FROM messages
        WHERE sender_number = %s
        ORDER BY date DESC
        ''', (sender,))

        rows = cursor.fetchall()
        messages = []
        
        for row in rows:
            message, embeddings_json, date = row
            embeddings = json.loads(embeddings_json)
            messages.append({
                'message': message,
                'embeddings': embeddings,
                'date': date
            })

        conn.close()
        return messages

    def save_message(self, sender: str, message: str, embeddings: List[float]) -> bool:
        conn = self._get_connection()
        if conn is None:
            print("Failed to connect to the database.")
            return False

        try:
            cursor = conn.cursor()
            embeddings_json = json.dumps(embeddings)

            cursor.execute('''
            INSERT INTO messages (sender_number, message, embeddings) 
            VALUES (%s, %s, %s)
            ''', (sender, message, embeddings_json))

            conn.commit()
            return True
        except Error as e:
            print(f"Error saving message: {e}")
            return False
        finally:
            conn.close()