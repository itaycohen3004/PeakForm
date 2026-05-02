import socket # ספרייה שמייצרת את חיבור התקשורת (ה"טלפון") בין המחשבים
import ssl # ספרייה להצפנה (כדי שאף אחד לא יוכל לצותת לשיחה)
from protocol import send_message, recv_message # הפונקציות שבנינו כדי לשלוח ולקבל הודעות

class SecureClient:
    """המחלקה שמייצגת את הלקוח - התוכנה שמתחברת לשרת המאובטח שלנו."""
    
    # פונקציה שרצה כשהלקוח נוצר (מגדירים לאיזו כתובת ולאיזה פורט נתחבר)
    def __init__(self, host='127.0.0.1', port=8443):
        self.host = host # כתובת השרת (פה זה המחשב שלנו)
        self.port = port # מספר ה"דלת" (הפורט) שדרכה ניכנס לשרת
        self.conn = None # משתנה שישמור את החיבור עצמו ברגע שנתחבר

    # פונקציה שמתחברת פיזית לשרת
    def connect(self):
        # מכינים את סביבת ההצפנה - איזה סוג הגנה אנחנו רוצים
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False # לא בודקים את שם האתר כרגע (כי אנחנו במחשב המקומי)
        context.verify_mode = ssl.CERT_NONE # סומכים על השרת שלנו גם בלי אישור רשמי מגורם חיצוני
        context.minimum_version = ssl.TLSVersion.TLSv1_3 # דורשים את רמת האבטחה הכי חדשה (TLS 1.3)!

        # יוצרים שקע רגיל לחיבור
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # "עוטפים" את השקע הרגיל בשכבת הצפנה
        self.conn = context.wrap_socket(sock, server_hostname=self.host)
        try:
            self.conn.connect((self.host, self.port)) # מתחברים
            print(f"[CLIENT] Connected to secure server {self.host}:{self.port}")
            return True # הצלחנו!
        except Exception as e:
            print(f"[CLIENT] Connection failed: {e}")
            return False # משהו השתבש בחיבור

    # פונקציה שמאפשרת למשתמש לבחור מה הוא רוצה לעשות (תפריט טקסטואלי)
    def interact(self):
        while True:
            # מדפיסים למסך תפריט יפה
            print("\n--- SECURE VAULT MENU ---")
            print("1. Register (הרשמה)")
            print("2. Login (התחברות)")
            print("3. Save Data (שמירת מידע סודי)")
            print("4. Get Data (שליפת המידע)")
            print("5. External API Integration (Get a Joke - קבלת בדיחה משרת חיצוני)")
            print("6. Exit (יציאה)")
            choice = input("Select an option: ") # מבקשים מהמשתמש לבחור

            # לפי מה שהמשתמש בחר, שולחים הודעה לשרת
            if choice == '1':
                user = input("Username: ")
                pwd = input("Password: ")
                # שולחים פקודת הרשמה עם שם וסיסמה
                send_message(self.conn, {"command": "REGISTER", "username": user, "password": pwd})
            elif choice == '2':
                user = input("Username: ")
                pwd = input("Password: ")
                # שולחים פקודת התחברות
                send_message(self.conn, {"command": "LOGIN", "username": user, "password": pwd})
            elif choice == '3':
                data = input("Enter sensitive data to vault: ")
                # שולחים מידע לשמירה בכספת
                send_message(self.conn, {"command": "SAVE_DATA", "data": data})
            elif choice == '4':
                # מבקשים את המידע שלנו חזרה
                send_message(self.conn, {"command": "GET_DATA"})
            elif choice == '5':
                # מבקשים מהשרת לשלוף לנו בדיחה מהאינטרנט (API)
                send_message(self.conn, {"command": "EXTERNAL_API"})
            elif choice == '6':
                break # יציאה מהלולאה
            else:
                print("Invalid choice.")
                continue # אם הזינו מספר לא נכון, חוזרים להתחלה

            # אחרי ששלחנו, אנחנו מחכים לקבל תשובה מהשרת
            response = recv_message(self.conn)
            if response:
                print(f"[SERVER RESPONSE] Status: {response.get('status')}")
                if response.get('data'):
                    print(f"Data: {response.get('data')}")
                if response.get('message'):
                    print(f"Message: {response.get('message')}")
            else:
                print("[CLIENT] Connection lost.") # השרת ניתק אותנו
                break

        # בסוף מתנתקים בצורה מסודרת
        if self.conn:
            self.conn.close()
            print("[CLIENT] Disconnected.")

# אם מפעילים את הקובץ הזה ישירות, נתחיל את התוכנה!
if __name__ == "__main__":
    client = SecureClient()
    if client.connect(): # אם הצלחנו להתחבר
        client.interact() # מתחילים להציג את התפריט

"""
English Summary:
This file is the client-side application that connects to our custom secure TCP server. 
It wraps a standard socket in a TLS layer to ensure all transmitted data is encrypted. 
It provides an interactive command-line interface for the user to register, login, save data, 
and fetch information from the secure vault.

סיכום בעברית:
קובץ זה מתפקד בתור התוכנה של הלקוח (ה"אפליקציה" שהמשתמש מפעיל במחשב שלו). 
הוא מנסה להתחבר לשרת באמצעות ערוץ מוצפן ובלתי חדיר. ברגע שהחיבור מצליח, הוא מציג
למשתמש תפריט נוח (כמו כספומט) שדרכו הוא יכול לבקש מהשרת פעולות שונות:
להירשם, להתחבר, או לשמור מידע רגיש בתוך הכספת.
"""
