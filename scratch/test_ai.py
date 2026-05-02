import os # ספרייה שנותנת לנו לדבר עם המחשב ולבקש ממנו מידע (כמו סיסמאות)
from dotenv import load_dotenv # קורא הגדרות וסיסמאות מקובץ סודי כדי שלא יהיו גלויות בקוד
import google.generativeai as genai # הספרייה של גוגל שמאפשרת לנו להשתמש בבינה המלאכותית (Gemini)

# 1. מפעילים את קורא הסיסמאות
load_dotenv()

# 2. מושכים את המפתח הסודי של גוגל מתוך ההגדרות שלנו
key = os.getenv("GEMINI_API_KEY")
# מדפיסים רק את ההתחלה של המפתח כדי שנדע שהוא קיים, אבל לא חושפים את כולו כדי שלא יגנבו לנו!
print(f"Key found: {key[:10]}...")

# 3. בודקים אם בכלל מצאנו מפתח
if not key:
    print("Error: No key in environment.") # אם אין מפתח - מדפיסים שגיאה
else:
    # אם יש מפתח, ננסה להתחבר לגוגל
    try:
        # מגדירים את הגישה שלנו לגוגל בעזרת המפתח
        genai.configure(api_key=key)
        print("Listing models:")
        
        # עוברים על כל "המוחות" (המודלים) השונים שגוגל מציעה לנו
        for m in genai.list_models():
            # מחפשים מודלים שיודעים לייצר תוכן (לענות על שאלות, לכתוב טקסטים)
            if 'generateContent' in m.supported_generation_methods:
                print(m.name) # מדפיסים את השם של כל מודל שמצאנו כדי לדעת במה אפשר להשתמש
                
    except Exception as e:
        # אם יש תקלה מול גוגל (למשל אין אינטרנט או המפתח שגוי), נדפיס את השגיאה
        print(f"Error listing models: {e}")
