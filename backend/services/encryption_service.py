"""
שירות הצפנה (Encryption Service)
הקובץ הזה הוא ה"כספת" שלנו. הוא אחראי לקחת מידע אישי וסודי (כמו אימייל או הערות לאימון), 
לנעול אותו עם "מפתח" מיוחד, כדי שאף אחד לא יוכל לקרוא אותו בלי רשות.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

# אנחנו טוענים קבצי הגדרות (קודם config.env ואז .env) כדי למצוא את המפתח הסודי שלנו
load_dotenv('config.env')
load_dotenv('.env', override=True)

# המפתח הסודי שלנו! זה כמו קוד של כספת. חשוב מאוד לשמור עליו בסוד מוחלט!
SECRET_KEY = os.getenv("SECRET_KEY", "peakform_dev_secret_must_be_long")

def _get_fernet():
    """
    פונקציה שמייצרת בשבילנו "מנעול חכם" (קראפים קוראים לזה Fernet) שמבוסס על המפתח הסודי שלנו.
    בגלל שהמפתח חייב להיות באורך מסוים וצורה מסוימת, הפונקציה הזו "לשה" ומשנה אותו כדי שיתאים בדיוק למנעול.
    """
    salt = b'peakform_stable_salt' # "מלח" (Salt) - מוסיפים קצת אקראיות להצפנה כדי שתהיה חזקה יותר
    
    # משתמשים באלגוריתם מתמטי שמערבב את המפתח הסודי שלנו המון המון פעמים (100,000 פעמים!) 
    # כדי שאף האקר לא יוכל לנחש אותו גם אם הוא ישתמש במחשב על.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    # יוצרים את המפתח הסופי ומוכנים לנעול ולפתוח איתו מנעולים
    key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY.encode()))
    return Fernet(key)

# כאן אנחנו שומרים את ה"מנעול החכם" שלנו שמוכן לשימוש
_cipher = _get_fernet()

def encrypt_data(data: str) -> str:
    """
    הפונקציה שנועלת את המידע (מצפינה אותו).
    מקבלת מילים רגילות, ומחזירה "ג'יבריש" בלתי קריא שרק המערכת יודעת לתרגם חזרה.
    """
    if not data: return data # אם לא נתנו לה כלום להצפין, היא תחזיר כלום
    if not isinstance(data, str): data = str(data) # מוודאים שמה שמקבלים זה באמת טקסט
    # פקודת ההצפנה! נועלים את הטקסט ומחזירים את הג'יבריש
    return _cipher.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    """
    הפונקציה שפותחת את המידע (מפענחת אותו).
    היא לוקחת את ה"ג'יבריש", פותחת אותו עם המנעול שלנו, ומחזירה לנו חזרה את הטקסט הקריא שהיה שם בהתחלה.
    """
    if not token: return token
    try:
        # פקודת הפענוח! פותחים את המנעול
        return _cipher.decrypt(token.encode()).decode()
    except Exception:
        # אם יש בעיה לפענח (אולי המידע בכלל לא היה מוצפן מראש),
        # פשוט נחזיר אותו כמו שהוא בתקווה שזה טקסט רגיל.
        return token

def blind_index(data: str) -> str:
    """
    אינדקס עיוור - טריק מגניב למתכנתים:
    איך נחפש משתמש לפי האימייל שלו אם האימייל מוצפן במערכת וכל פעם נראה אחרת?
    התשובה: אנחנו מפעילים עליו מתמטיקה שמייצרת "טביעת אצבע" (hash) ייחודית שתמיד נראית אותו הדבר עבור אותו אימייל.
    ככה אפשר לחפש במערכת בלי באמת לדעת את האימייל האמיתי!
    """
    if not data: return data
    import hashlib
    salt = b'peakform_blind_index_salt' # מלח מיוחד רק לזה
    # מחשבים את תביעת האצבע המיוחדת
    return hashlib.sha256(salt + data.lower().strip().encode()).hexdigest()

"""
English Summary:
This file implements the encryption mechanisms for the PeakForm platform, acting as its security vault.
It uses symmetric encryption (Fernet) to securely encrypt and decrypt sensitive user data before it is 
saved to the database. It also provides a 'blind index' function, which hashes encrypted values (like emails)
so they can be queried securely without decrypting the entire database.

סיכום בעברית:
קובץ זה מתפקד בתור "הכספת" של האפליקציה. הוא אחראי לקחת מידע אישי של מתאמנים, לנעול אותו עם
מפתח הצפנה מיוחד, ורק אז לשמור אותו בבסיס הנתונים. בנוסף, הוא מאפשר לעשות חיפוש של מידע 
(כמו חיפוש מתאמן לפי אימייל) גם כשהמידע מוצפן לחלוטין, באמצעות טריק אבטחה שנקרא "אינדקס עיוור".
"""
