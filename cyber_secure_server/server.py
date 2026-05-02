import socket # ספרייה שמאפשרת למחשב להאזין ולהתחבר ברשת
import ssl # ספריית הצפנה
import threading # ספרייה שמאפשרת לשרת לעשות כמה דברים במקביל (כמו לטפל בכמה לקוחות בו זמנית)
from protocol import send_message, recv_message # פונקציות השליחה והקבלה שלנו
from database_manager import SecureDatabase # חיבור למסד הנתונים ששומר את היוזרים

class ClientHandler(threading.Thread):
    """מחלקה (Thread) מיוחדת שמטפלת בלקוח אחד.
       לכל מי שמתחבר לשרת, השרת פותח "עותק" חדש כזה כדי לא לעכב את האחרים."""
    
    def __init__(self, conn, addr, db):
        super().__init__()
        self.conn = conn # החיבור הספציפי ללקוח הזה
        self.addr = addr # כתובת ה-IP שלו
        self.db = db # גישה למסד הנתונים
        self.username = None # ברגע שהוא יתחבר, נשמור את השם שלו כאן

    # ברגע שהחיבור אושר, הפונקציה הזו רצה בלולאה כל עוד הלקוח מחובר
    def run(self):
        print(f"[SERVER] Connection established from {self.addr}")
        try:
            while True:
                msg = recv_message(self.conn) # מחכים לקבל הודעה
                if not msg:
                    break # אם אין הודעה (הוא התנתק), יוצאים
                self.handle_message(msg) # מעבירים לפונקציה שתחליט מה לעשות
        except Exception as e:
            print(f"[SERVER] Error with {self.addr}: {e}")
        finally:
            print(f"[SERVER] Connection closed from {self.addr}")
            self.conn.close() # סוגרים את החיבור בצורה נקייה

    # הפונקציה שקוראת את ההודעה מהלקוח ומחליטה איך לענות
    def handle_message(self, msg):
        cmd = msg.get("command") # שולפים את סוג הפקודה (הרשמה, התחברות וכו')
        
        if cmd == "REGISTER": # בקשת הרשמה
            username = msg.get("username")
            password = msg.get("password")
            # שולחים למסד הנתונים את המידע ומקבלים תשובה
            success, info = self.db.register_user(username, password)
            # עונים ללקוח אם זה הצליח או לא
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "message": info})
            
        elif cmd == "LOGIN": # בקשת התחברות
            username = msg.get("username")
            password = msg.get("password")
            success, info = self.db.verify_login(username, password)
            if success:
                self.username = username # שומרים את השם כדי שנדע מי זה הלקוח
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "message": info})
            
        elif cmd == "SAVE_DATA": # בקשה לשמור מידע בכספת
            if not self.username:
                send_message(self.conn, {"status": "ERROR", "message": "Not authenticated."}) # אסור אם לא התחברת
                return
            data = msg.get("data")
            success, info = self.db.save_data(self.username, data)
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "message": info})
            
        elif cmd == "GET_DATA": # בקשה למשוך את המידע
            if not self.username:
                send_message(self.conn, {"status": "ERROR", "message": "Not authenticated."})
                return
            success, info = self.db.get_data(self.username)
            send_message(self.conn, {"status": "SUCCESS" if success else "ERROR", "data": info if success else None, "message": info if not success else "Data retrieved."})
            
        elif cmd == "EXTERNAL_API": # פנייה לשרת חיצוני בשביל בדיחה (דוגמה לאינטגרציה)
            try:
                import urllib.request
                import json
                # פונים לכתובת אינטרנט של אתר בדיחות חינמי
                req = urllib.request.Request("https://official-joke-api.appspot.com/random_joke", headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    joke_data = json.loads(response.read().decode()) # מפענחים את התשובה (JSON)
                    joke = f"{joke_data['setup']} - {joke_data['punchline']}" # מרכיבים את הבדיחה
                send_message(self.conn, {"status": "SUCCESS", "message": joke}) # מחזירים ללקוח
            except Exception as e:
                send_message(self.conn, {"status": "ERROR", "message": f"External API failed: {e}"}) # שגיאה
            
        else:
            send_message(self.conn, {"status": "ERROR", "message": "Unknown command."}) # לא הבנו מה הלקוח רוצה

class ServerEngine:
    """המנוע הראשי של השרת - המוח שמאזין לבקשות חדשות."""
    
    def __init__(self, host='127.0.0.1', port=8443, certfile='cert.pem', keyfile='key.pem'):
        self.host = host
        self.port = port
        self.certfile = certfile # קובץ ה"תעודה" הציבורית
        self.keyfile = keyfile   # קובץ המפתח הסודי להצפנה
        self.db = SecureDatabase() # מכינים את מסד הנתונים

    # מפעילים את השרת
    def start(self):
        # מכינים את ההצפנה שבה השרת ישתמש כדי לדבר עם כולם
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            # טוענים את התעודה והמפתח כדי שההצפנה תעבוד
            context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)
        except FileNotFoundError:
            print(f"[SERVER] Error: Certificates not found. Please run cert_gen.py first.") # שכחת לייצר מפתחות!
            return

        # דורשים רמת אבטחה גבוהה במיוחד (TLS 1.3)
        context.minimum_version = ssl.TLSVersion.TLSv1_3

        # פותחים דלת האזנה (Socket)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sock:
            sock.bind((self.host, self.port))
            sock.listen(5) # מאזינים לעד 5 חיבורים שממתינים בתור
            # מוסיפים את ההצפנה על ה"דלת" שלנו
            with context.wrap_socket(sock, server_side=True) as ssock:
                print(f"[SERVER] Listening securely on {self.host}:{self.port}...")
                try:
                    while True: # השרת עובד תמיד
                        conn, addr = ssock.accept() # ברגע שמישהו מתחבר...
                        # אנחנו יוצרים בשבילו מטפל פרטי (Thread)
                        handler = ClientHandler(conn, addr, self.db)
                        handler.start() # והוא מתחיל לדבר איתו, בזמן שהשרת המרכזי חוזר להקשיב לעוד אנשים!
                except KeyboardInterrupt:
                    print("\n[SERVER] Shutting down...") # סוגרים כשלוחצים קונטרול+C

if __name__ == "__main__":
    server = ServerEngine()
    server.start()

"""
English Summary:
This is the main entry point for the custom, multi-threaded secure TCP server. 
It establishes a TLS 1.3 encrypted socket to listen for incoming connections. 
Each connected client is handled by a dedicated thread (ClientHandler) to ensure non-blocking, 
concurrent execution. It routes commands (register, login, vault data) to the SecureDatabase manager.

סיכום בעברית:
קובץ זה מפעיל את השרת המאובטח שלנו (ה"מוח" של המערכת). השרת מאזין באופן רצוף לבקשות
תקשורת, וברגע שמתקבלת פנייה מלקוח חדש, הוא פותח ערוץ תקשורת מוצפן (כדי למנוע האזנות סתר).
השרת משתמש בטכנולוגיית ריבוי-תהליכים (Threads), מה שאומר שהוא מסוגל לטפל בהמון משתמשים
במקביל מבלי לקרוס או להיתקע.
"""
