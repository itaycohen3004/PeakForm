import sqlite3
import bcrypt
import os

class SecureDatabase:
    """Manages SQLite connection, schema creation, and secure data operations."""
    
    def __init__(self, db_path="secure_vault.db"):
        self.db_path = db_path
        self._initialize_db()
        
    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    data TEXT
                )
            ''')
            conn.commit()

    def register_user(self, username, password):
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Parameterized query to prevent SQL Injection
                cursor.execute('INSERT INTO users (username, password_hash, data) VALUES (?, ?, ?)',
                               (username, hashed.decode('utf-8'), ''))
                conn.commit()
            return True, "User registered successfully."
        except sqlite3.IntegrityError:
            return False, "Username already exists."
        except Exception as e:
            return False, f"Database error: {e}"

    def verify_login(self, username, password):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                
                if result:
                    stored_hash = result[0].encode('utf-8')
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                        return True, "Login successful."
                return False, "Invalid username or password."
        except Exception as e:
            return False, f"Database error: {e}"

    def save_data(self, username, data):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET data = ? WHERE username = ?', (data, username))
                conn.commit()
            return True, "Data saved successfully."
        except Exception as e:
            return False, f"Database error: {e}"

    def get_data(self, username):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT data FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result:
                    return True, result[0]
                return False, "User not found."
        except Exception as e:
            return False, f"Database error: {e}"
