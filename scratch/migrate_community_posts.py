import sqlite3 # ספרייה שמאפשרת לנו לדבר עם מסד הנתונים (הטבלאות שלנו)
import os # ספרייה שעוזרת לנו לעבוד עם קבצים ותיקיות במחשב

# 1. מתחברים למסד הנתונים (הקובץ שבו שמור כל המידע של האתר)
db_path = os.path.join('database', 'peakform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor() # ה"שליח" שלנו שלוקח פקודות ומריץ אותן

# 2. מכבים זמנית את ההגנות של מסד הנתונים
# למה? כי אנחנו הולכים להחליף טבלה מרכזית, ואם ההגנות פועלות הן לא יתנו לנו למחוק אותה
cursor.execute("PRAGMA foreign_keys = OFF;")
conn.commit() # שומרים את ההחלטה

# 3. יוצרים טבלה חדשה לגמרי ומשופרת בשביל הפוסטים בקהילה
# קוראים לה בינתיים "community_posts_new" (פוסטים_קהילה_חדש)
cursor.execute("""
CREATE TABLE IF NOT EXISTS community_posts_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- מספר מזהה לכל פוסט, עולה אוטומטית (1, 2, 3...)
    user_id INTEGER NOT NULL, -- מי כתב את הפוסט
    content TEXT NOT NULL, -- התוכן של הפוסט (המילים עצמן)
    post_type TEXT DEFAULT 'update' CHECK(post_type IN ( -- איזה סוג פוסט זה? (עדכון, שאלה, תמונה...)
        'update','achievement','progress_photo','question','tip','template'
    )),
    media_path TEXT, -- האם יש תמונה מצורפת? אם כן, כאן הכתובת שלה
    likes_count INTEGER NOT NULL DEFAULT 0, -- כמה לייקים קיבל הפוסט (מתחיל ב-0)
    is_deleted INTEGER NOT NULL DEFAULT 0, -- האם הפוסט נמחק? (0 אומר שלא, 1 אומר שכן)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- מתי הפוסט נכתב (השעה והתאריך בדיוק עכשיו)
    meta_data TEXT, -- מידע נוסף אם צריך (למשל תגיות)
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE -- אם מוחקים משתמש, ימחקו גם כל הפוסטים שלו
);
""")

# 4. מעתיקים את כל המידע מהטבלה הישנה (community_posts) לתוך הטבלה החדשה והריקה שבנינו עכשיו
cursor.execute("""
INSERT INTO community_posts_new (id, user_id, content, post_type, media_path, likes_count, is_deleted, created_at, meta_data)
SELECT id, user_id, content, post_type, media_path, likes_count, is_deleted, created_at, meta_data
FROM community_posts;
""")

# 5. קסם אחרון: זורקים את הטבלה הישנה לפח, ומשנים את השם של הטבלה החדשה להיות בדיוק כמו הישנה!
# ככה האתר בכלל לא ידע שהחלפנו לו את הטבלה מתחת לאף
cursor.execute("DROP TABLE community_posts;") # מחיקת הישנה
cursor.execute("ALTER TABLE community_posts_new RENAME TO community_posts;") # שינוי השם לחדשה

# 6. מחזירים את ההגנות שכיבינו בהתחלה
cursor.execute("PRAGMA foreign_keys = ON;")
conn.commit() # שומרים את כל השינויים

# סיימנו! מדפיסים הודעת הצלחה למסך
print("Successfully migrated community_posts table.")
