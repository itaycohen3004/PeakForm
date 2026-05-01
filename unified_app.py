import os
import sqlite3
import bcrypt
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables (primary and secondary keys)
load_dotenv('config.env')

# --- Database Component ---
class SecureDatabase:
    """Manages SQLite connection, schema creation, and secure data operations."""
    
    def __init__(self, db_path="unified_secure_vault.db"):
        self.db_path = db_path
        self._initialize_db()
        
    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS secure_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    log_entry TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            ''')
            conn.commit()

    def register_user(self, username, password):
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                               (username, hashed.decode('utf-8')))
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
                cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                
                if result:
                    user_id, stored_hash = result
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        return True, user_id
                return False, "Invalid username or password."
        except Exception as e:
            return False, f"Database error: {e}"

    def save_log(self, user_id, log_entry):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO secure_logs (user_id, log_entry) VALUES (?, ?)', (user_id, log_entry))
                conn.commit()
            return True, "Log saved successfully."
        except Exception as e:
            return False, f"Database error: {e}"

    def get_logs(self, user_id):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT log_entry FROM secure_logs WHERE user_id = ?', (user_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []


# --- AI Component with Fallback Logic ---
class AICoach:
    """Handles AI logic with automatic fallback for quotas and multiple keys."""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.secondary_key = os.getenv("GEMINI_SECONDARY_API_KEY", "AIzaSyC2hAx9517YRPW2LlCO5PVhD__HIku_p2g")
        
        self.active_key = self.api_key if self.api_key else self.secondary_key
        
        self.available_models = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
        self.current_model_index = 0
        self.model_name = self.available_models[self.current_model_index]
        self._client = None
        self._is_ready = False

    def _initialize(self):
        if self._is_ready: return
        if not self.active_key:
            print("[AI] No API key available.")
            return

        try:
            genai.configure(api_key=self.active_key)
            self._client = genai.GenerativeModel(self.model_name)
            self._is_ready = True
            print(f"[AI] Initialized with model {self.model_name} and Key ending in ...{self.active_key[-4:]}")
        except Exception as e:
            print(f"[AI] Initialization error: {e}")

    def _failover(self) -> bool:
        """Switch to next model or secondary API key."""
        self.current_model_index += 1
        if self.current_model_index < len(self.available_models):
            self.model_name = self.available_models[self.current_model_index]
            print(f"[AI] 🔄 Failover: Switching to model {self.model_name}")
            self._client = genai.GenerativeModel(self.model_name)
            return True
            
        if self.active_key == self.api_key and self.secondary_key:
            print("[AI] 🔄 Failover: Primary key models exhausted. Switching to secondary API key.")
            self.active_key = self.secondary_key
            genai.configure(api_key=self.active_key)
            self.current_model_index = 0
            self.model_name = self.available_models[self.current_model_index]
            self._client = genai.GenerativeModel(self.model_name)
            return True
            
        return False

    def ask(self, prompt: str) -> str:
        self._initialize()
        if not self._is_ready:
            return "Error: AI is not configured."

        max_attempts = len(self.available_models) * 2
        attempts = 0
        
        while attempts < max_attempts:
            try:
                response = self._client.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                err_str = str(e)
                attempts += 1
                if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower():
                    print(f"\n[AI] ⚠️ Quota error on {self.model_name}. Attempting failover...")
                    if self._failover():
                        continue
                    else:
                        return "Error: All models and backup keys have exhausted their quotas."
                elif "403" in err_str or "400" in err_str:
                    return f"API Error (Region/Proxy 403): {err_str}"
                else:
                    return f"API Error: {err_str}"
        return "Error: Maximum fallback attempts reached."


# --- Main Application Controller ---
class UnifiedApp:
    def __init__(self):
        self.db = SecureDatabase()
        self.ai = AICoach()
        self.current_user_id = None
        self.current_username = None

    def run(self):
        print("="*45)
        print("  Welcome to the Unified AI & Secure Vault")
        print("="*45)
        
        while True:
            if not self.current_user_id:
                self._auth_menu()
            else:
                self._main_menu()

    def _auth_menu(self):
        print("\n--- Authentication ---")
        print("1. Login")
        print("2. Register")
        print("3. Exit App")
        
        choice = input("Select an option: ")
        if choice == '1':
            u = input("Username: ")
            p = input("Password: ")
            success, result = self.db.verify_login(u, p)
            if success:
                self.current_user_id = result
                self.current_username = u
                print(f"\n✅ Welcome back, {u}!")
            else:
                print(f"\n❌ Login failed: {result}")
        elif choice == '2':
            u = input("Choose a Username: ")
            p = input("Choose a Password: ")
            success, msg = self.db.register_user(u, p)
            print(f"\n{'✅' if success else '❌'} {msg}")
        elif choice == '3':
            print("Exiting...")
            exit(0)
        else:
            print("Invalid choice.")

    def _main_menu(self):
        print(f"\n--- Main Menu ({self.current_username}) ---")
        print("1. Ask AI Coach")
        print("2. Log Secure Data")
        print("3. View Secure Logs")
        print("4. Logout")
        
        choice = input("Select an option: ")
        if choice == '1':
            prompt = input("\nAsk AI: ")
            print("Thinking...")
            reply = self.ai.ask(prompt)
            print(f"\n🤖 AI Coach:\n{reply}")
            
        elif choice == '2':
            data = input("\nEnter secure log entry: ")
            self.db.save_log(self.current_user_id, data)
            print("✅ Saved securely to your vault.")
            
        elif choice == '3':
            logs = self.db.get_logs(self.current_user_id)
            print("\n--- Your Secure Logs ---")
            if not logs:
                print("No logs found.")
            for i, log in enumerate(logs, 1):
                print(f"[{i}] {log}")
                
        elif choice == '4':
            self.current_user_id = None
            self.current_username = None
            print("✅ Logged out.")
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    app = UnifiedApp()
    app.run()
