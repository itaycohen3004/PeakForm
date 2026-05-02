import sqlite3 # ספרייה שמדברת עם מסד הנתונים (איפה שהמידע שמור)
import bcrypt # ספרייה מיוחדת להצפנת סיסמאות (כדי שאף אחד לא יידע מה הסיסמה שלך)
import os # ספרייה לעבודה עם מערכת ההפעלה (נתיבים של קבצים וכדומה)

class SecureDatabase:
    """מחלקה (Class) שמנהלת את מסד הנתונים של השרת בצורה מאובטחת. היא שומרת סיסמאות מוסתרות ומונעת פריצות."""
    
    # הפונקציה הזו מופעלת ברגע שאנחנו מפעילים את מסד הנתונים
    def __init__(self, db_path="secure_vault.db"):
        self.db_path = db_path # הכתובת של קובץ מסד הנתונים
        self._initialize_db() # קוראים לפונקציה שבונה את הטבלאות
        
    # פונקציה שיוצרת את הטבלאות בפעם הראשונה
    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn: # מתחברים לקובץ הנתונים
            cursor = conn.cursor()
            # מכינים טבלה בשם users (משתמשים) שתשמור: מספר מזהה, שם משתמש, סיסמה מוצפנת, ומידע כללי
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    data TEXT
                )
            ''')
            conn.commit() # שומרים את השינויים

    # פונקציה להרשמת משתמש חדש
    def register_user(self, username, password):
        try:
            # לפני ששומרים את הסיסמה, מצפינים אותה עם מלח (salt) כדי שתהיה חזקה!
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt) # הסיסמה המוצפנת הסופית
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # שומרים את המשתמש במסד הנתונים בעזרת סימני שאלה (?) שמגינים עלינו מפני פריצות מסוג SQL Injection
                cursor.execute('INSERT INTO users (username, password_hash, data) VALUES (?, ?, ?)',
                               (username, hashed.decode('utf-8'), ''))
                conn.commit() # שומרים
            return True, "User registered successfully." # הצלחה!
        except sqlite3.IntegrityError:
            return False, "Username already exists." # השם תפוס
        except Exception as e:
            return False, f"Database error: {e}" # שגיאה כללית

    # פונקציה לבדיקת התחברות (לוגין)
    def verify_login(self, username, password):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # שולפים את הסיסמה המוצפנת של המשתמש ממסד הנתונים
                cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                
                # אם מצאנו משתמש כזה
                if result:
                    stored_hash = result[0].encode('utf-8')
                    # בודקים אם הסיסמה שהוא הקליד (אחרי הצפנה) שווה לסיסמה ששמורה במערכת
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                        return True, "Login successful." # התחברות הצליחה!
                return False, "Invalid username or password." # סיסמה או שם משתמש שגויים
        except Exception as e:
            return False, f"Database error: {e}"

    # פונקציה לשמירת מידע של המשתמש
    def save_data(self, username, data):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # מעדכנים את שדה המידע (data) של המשתמש
                cursor.execute('UPDATE users SET data = ? WHERE username = ?', (data, username))
                conn.commit()
            return True, "Data saved successfully."
        except Exception as e:
            return False, f"Database error: {e}"

    # פונקציה לשליפת מידע של משתמש
    def get_data(self, username):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # שואלים את מסד הנתונים: "מה המידע של המשתמש הזה?"
                cursor.execute('SELECT data FROM users WHERE username = ?', (username,))
                result = cursor.fetchone()
                if result:
                    return True, result[0] # מחזירים את המידע
                return False, "User not found."
        except Exception as e:
            return False, f"Database error: {e}"

"""
English Summary:
This module manages all persistent storage operations for the custom TCP server using SQLite. 
It is specifically designed with security in mind: all user passwords are mathematically hashed 
using the 'bcrypt' library before being stored, preventing exposure even if the database is breached. 
It utilizes parameterized queries (with '?') to eliminate SQL injection vulnerabilities.

סיכום בעברית:
הקובץ הזה הוא מנהל מסד הנתונים והאבטחה של המידע! כל פעם שמשתמש נרשם או כותב משהו,
הקובץ הזה מטפל בשמירה על הדיסק. הוא תוכנן במיוחד כנגד האקרים - הוא לא שומר סיסמאות 
כמו שהן, אלא מקדד אותן לצופן מסובך (בעזרת bcrypt). בנוסף, הדרך שבה הוא מדבר עם מסד
הנתונים מונעת פריצות נפוצות (כמו חדרת קוד זדוני ל-SQL).
"""
