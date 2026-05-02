import json # ספרייה שלוקחת מידע והופכת אותו לטקסט מיוחד שאפשר להעביר ברשת
import struct # ספרייה שעוזרת לנו לעבוד עם "בייטים" ולשלוח מספרים שמייצגים גדלים

# פונקציה שעוזרת לנו לשלוח הודעה (גם בשרת וגם בלקוח משתמשים בה)
def send_message(sock, message_dict):
    """
    כדי לשלוח הודעה, אנחנו צריכים להגיד לצד השני בדיוק כמה תווים יש בהודעה שלנו
    לפני שאנחנו שולחים אותה, כדי שהוא יידע מתי לסיים להקשיב.
    """
    try:
        # הופכים את ההודעה (מילון בפייתון) לטקסט שנקרא JSON, ואז ל"בייטים" שזורמים ברשת
        msg_bytes = json.dumps(message_dict).encode('utf-8')
        
        # מחשבים מה האורך של ההודעה (כמה בייטים היא), ושומרים את המספר הזה בעזרת ה-struct
        # זה יוצר 4 בייטים מיוחדים (קידומת) שמכילים את הגודל המדויק.
        prefix = struct.pack('!I', len(msg_bytes))
        
        # שולחים את הקוד של הקידומת וישר אחריו את ההודעה האמיתית
        sock.sendall(prefix + msg_bytes)
        return True # ההודעה נשלחה בהצלחה!
    except Exception as e:
        print(f"Send error: {e}")
        return False

# פונקציה שעוזרת לנו לקבל הודעות ממישהו אחר
def recv_message(sock):
    """
    כשאנחנו מקבלים הודעה, קודם נקרא רק את 4 התווים הראשונים, כדי לדעת מה הגודל
    של שאר ההודעה. ואז נוכל לקרוא בדיוק את כמות התווים שצריך!
    """
    try:
        # שלב 1: קוראים את 4 הבייטים של הקידומת, שמכילים את אורך ההודעה
        raw_msglen = recvall(sock, 4)
        if not raw_msglen:
            return None # אם אין כלום - הצד השני התנתק
            
        # הופכים את 4 הבייטים בחזרה למספר נורמלי (אורך ההודעה)
        msglen = struct.unpack('!I', raw_msglen)[0]
        
        # שלב 2: קוראים עכשיו את כל ההודעה, לפי הגודל שמצאנו!
        msg_bytes = recvall(sock, msglen)
        if not msg_bytes:
            return None
            
        # הופכים את הבייטים בחזרה לטקסט ואז למילון פייתון קריא
        return json.loads(msg_bytes.decode('utf-8'))
    except Exception as e:
        print(f"Recv error: {e}")
        return None

# פונקציית עזר קטנה שמבטיחה שלא נפספס שום דבר (האינטרנט לפעמים מפצל הודעות)
def recvall(sock, n):
    """מקבלת בדיוק N תווים/בייטים מהרשת - ומוודאת שלא חסר כלום."""
    data = bytearray() # רשימה ריקה לאסוף אליה את החלקים
    # כל עוד לא אספנו הכל:
    while len(data) < n:
        packet = sock.recv(n - len(data)) # מחכה לקבל את החלק החסר
        if not packet:
            return None # אם החיבור נסגר פתאום
        data.extend(packet) # מדביק לחבילה הכללית שלנו
    return bytes(data) # מחזיר את הכל שלם!

"""
English Summary:
This utility file defines the custom networking protocol used by both the client and server. 
It uses a 'length-prefix' strategy: before sending the actual JSON payload, it sends 4 bytes 
that specify the exact length of the incoming message. This ensures that the receiver reads 
the complete message without dropping or fragmenting packets over the TCP stream.

סיכום בעברית:
קובץ זה קובע את "חוקי הדיבור" בין הלקוח לשרת (ממש כמו שפת קוד או תמרורים).
בגלל שברשת האינטרנט הודעות יכולות להתפצל לכמה חלקים קטנים בדרך, הקובץ הזה משתמש 
בטריק חכם: לפני ששולחים את ההודעה עצמה, שולחים מספר שמציין בדיוק כמה אותיות יש בהודעה.
ככה הצד השני יודע בדיוק מתי הוא צריך להפסיק לחכות ומתי ההודעה הגיעה במלואה ללא בעיות!
"""
