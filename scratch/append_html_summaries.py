import os

workspace = r"d:\PeakForm\frontend\pages"

summaries = {
    "achievements.html": """
<!-- 
English Summary:
This HTML file represents the user's Achievements and Goals page. It contains the structural layout 
for displaying goal cards, progress bars, and the modal for creating new personal records or 
milestone targets.

סיכום בעברית:
קובץ זה הוא התבנית (HTML) של מסך ה"הישגים ומטרות". הוא מגדיר היכן ימוקמו הכותרות, 
איפה יופיעו כרטיסיות ההתקדמות (Progress Bars), ואיך ייראה החלון הקופץ שמאפשר למתאמן 
להוסיף מטרה חדשה (כמו "להרים 100 קילו" או "לרדת 5 קילו"). 
-->
""",
    "admin.html": """
<!-- 
English Summary:
This HTML file is the Administrator Dashboard. It provides the layout for high-level system 
statistics, user management controls, and pending exercise approvals, accessible only to admins.

סיכום בעברית:
קובץ זה מציג את לוח הבקרה הסודי של מנהל האתר! הוא מכיל את המבנה של טבלאות המשתמשים, 
כפתורי מחיקת חשבון, ואזור מיוחד לאישור תרגילים חדשים שמשתמשים הוסיפו. הוא חסום למשתמשים רגילים.
-->
""",
    "ai-coach.html": """
<!-- 
English Summary:
This HTML file constructs the UI for the AI Coach interface. It includes the layout for 
selecting AI analysis types and the container where Gemini's dynamic feedback is rendered.

סיכום בעברית:
קובץ זה מרכיב את ממשק "המאמן האישי החכם" באתר. כאן נמצאים הכפתורים שמאפשרים 
לבקש ניתוח אימונים מהבינה המלאכותית, והאזור המעוצב שאליו התשובות החכמות (והטיפים) יוזרקו לאחר קבלת התשובה מהשרת.
-->
""",
    "body-weight.html": """
<!-- 
English Summary:
This HTML file represents the Body Weight Tracking page. It structures the chart display 
area, weight input form, and progress photo gallery.

סיכום בעברית:
מסך "מעקב משקל הגוף" שבו מתאמנים רושמים את המשקל שלהם כדי לראות התקדמות.
הקובץ בונה את תיבת ההזנה של המשקל, את המקום בו יופיע הגרף החזותי, ואת גלריית תמונות "לפני ואחרי".
-->
""",
    "community-chat.html": """
<!-- 
English Summary:
This HTML file builds the Real-time Community Chat interface. It contains the message 
container, user input field, and visual cues for online presence, supporting WebSocket integration.

סיכום בעברית:
זהו קובץ התצוגה של חדר הצ'אט! הוא בונה את חלון ההודעות עצמו (איפה שרואים את כל 
מה שמשתמשים מקלידים), את שורת ההקלדה למטה, ואת כפתור השליחה. הוא מעוצב בצורה 
שמאפשרת הזרקה של הודעות בזמן אמת ללא רענון עמוד.
-->
""",
    "community.html": """
<!-- 
English Summary:
This HTML file is the Community Feed layout. It structures the post creation area, 
the infinite-scrolling feed of user updates, likes, and comments.

סיכום בעברית:
קיר הקהילה (הפיד החברתי) של האתר, בדומה לאינסטגרם או פייסבוק.
קובץ זה בונה את המקום לכתוב פוסט חדש, ואת המסגרת הכללית לכל הפוסטים (תמונות, תבניות 
אימון לייקים ותגובות) שמשתמשים אחרים מעלים.
-->
""",
    "dashboard.html": """
<!-- 
English Summary:
This HTML file is the primary authenticated user Dashboard. It provides quick access 
widgets to recent workouts, current weight trends, and active goals.

סיכום בעברית:
קובץ ה"מסך הראשי" (דשבורד) אליו המתאמן מגיע מיד לאחר ההתחברות.
הוא מכיל קיצורי דרך מהירים להתחלת אימון, תצוגה תמציתית של גרף המשקל שלו, 
והצצה למטרות הקרובות ביותר שלו. זהו עמוד הבית של המשתמש הרשום!
-->
""",
    "exercise-library.html": """
<!-- 
English Summary:
This HTML file structures the Exercise Library database view. It includes the search bar, 
category filters, and the modal form for proposing custom exercises.

סיכום בעברית:
ספריית התרגילים של האתר. הקובץ בונה את שורת החיפוש, את כפתורי הסינון (לפי שרירים
או קטגוריות), ואת המבנה הכללי שמציג את כל עשרות התרגילים המובנים במערכת עם התמונות וההסברים.
-->
""",
    "index.html": """
<!-- 
English Summary:
This HTML file is the public landing page of the PeakForm application. It features 
the hero section, feature highlights, and call-to-action buttons for registration.

סיכום בעברית:
זהו חלון הראווה של האתר! (דף הנחיתה).
העמוד הראשון שכל בן אדם רואה כשהוא נכנס לכתובת האתר לפני שהוא מתחבר.
הוא כולל עיצוב מזמין, הסבר קצר על יכולות הבינה המלאכותית באתר, וכפתורי "הירשם עכשיו".
-->
""",
    "log-workout.html": """
<!-- 
English Summary:
This HTML file structures the live Workout Logger. It contains the stopwatch timer, 
exercise set tables (reps/weight), and the dynamic "add exercise" search modal.

סיכום בעברית:
קובץ זה בונה את התצוגה של יומן האימונים החי. 
כאן תמצאו את טיימר המנוחה שרץ בזמן אמת, את טבלאות הסטים (הכנסת משקל וחזרות), 
וכפתור ענק של "סיום אימון" ששומר את כל ההישגים למסד הנתונים!
-->
""",
    "login.html": """
<!-- 
English Summary:
This HTML file defines the structure for the User Login form. It includes fields for 
email and password, integrated with password visibility toggles.

סיכום בעברית:
טופס ההתחברות לאתר. קובץ קליל ופשוט שמכיל את שדות ה"אימייל" וה"סיסמה", 
וכפתור שמאפשר לבדוק את הסיסמה (העין הקטנה) כדי לא לטעות בהקלדה.
-->
""",
    "onboarding.html": """
<!-- 
English Summary:
This HTML file represents the initial Onboarding flow. It captures a new user's 
physical metrics (height, weight, age) and overarching fitness goals to tailor the AI experience.

סיכום בעברית:
מסך "קבלת הפנים" (אונבורדינג) שקופץ רק פעם אחת לאחר ההרשמה הראשונית.
הוא מאפשר לאסוף נתונים פיזיים חשובים (גובה, משקל, סוג אימונים) שיעזרו 
לבינה המלאכותית להכיר את המתאמן ולתת לו הצעות מותאמות אישית.
-->
""",
    "profile.html": """
<!-- 
English Summary:
This HTML file structures the user's Profile settings. It allows users to update 
their bio, training preferences, and view their personalized details.

סיכום בעברית:
קובץ "הפרופיל האישי". כאן המשתמש יכול לשנות את הפרטים שלו, לעדכן תמונה, 
ולשנות את הגדרות האימונים המועדפות עליו.
-->
""",
    "register.html": """
<!-- 
English Summary:
This HTML file defines the Registration form for new users, including client-side 
password strength validation and role assignment capabilities.

סיכום בעברית:
טופס ההרשמה למשתמשים חדשים. בנוסף לשדות הרגילים, הוא מכיל גם "מד חוזק סיסמה"
(חלש/בינוני/חזק) שמשתנה בזמן אמת כשהמשתמש מקליד, כדי להבטיח אבטחה מקסימלית לחשבונות.
-->
""",
    "templates.html": """
<!-- 
English Summary:
This HTML file builds the Workout Templates manager. It displays saved routines and 
includes the dynamic modal for building a new multi-exercise template.

סיכום בעברית:
תצוגת ניהול תבניות האימון השמורות של המשתמש. קובץ זה בונה את המסגרת המאפשרת 
לראות אימונים קבועים (כמו "חזה-יד אחורית" או "פול באדי") ולייצר מהם אימונים מהירים.
-->
""",
    "verify-2fa.html": """
<!-- 
English Summary:
This HTML file provides the interface for Two-Factor Authentication (2FA). It contains 
the input field for entering the security code sent via email.

סיכום בעברית:
מסך אבטחה מתקדם! (אימות דו-שלבי). כאשר המערכת מזהה פעילות חשודה, או כשהאדמין 
מבקש שכבת הגנה נוספת, עמוד זה יבקש מהמשתמש להזין קוד סודי בן 6 ספרות כהגנה.
-->
""",
    "workout-detail.html": """
<!-- 
English Summary:
This HTML file structures the retrospective view of a completed workout. It displays 
a read-only summary of the exercises performed, total volume, and overall duration.

סיכום בעברית:
סיכום של אימון שכבר בוצע (היסטוריה). הקובץ מציג יומן אירועים קריא בלבד - כמה חזרות 
בוצעו, מה היה המשקל המקסימלי, ומה היה סך משקל העבודה באותו היום (נפח האימון).
-->
""",
    "workout-history.html": """
<!-- 
English Summary:
This HTML file provides the layout for the global Workout History log. It renders a 
searchable, filterable list of all past workouts completed by the user.

סיכום בעברית:
ארכיון האימונים הראשי של המתאמן. קובץ זה בונה את התצוגה של עשרות האימונים האחרונים 
ככרטסיות מסודרות לפי תאריך, כך שהמתאמן תמיד יוכל לגלול אחורה ולראות איך הוא השתפר.
-->
"""
}

def apply_summaries():
    for filename, summary in summaries.items():
        filepath = os.path.join(workspace, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Avoid duplicate appends
            if "English Summary:" not in content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content + "\n" + summary.strip() + "\n")
                print(f"Updated {filename}")
            else:
                print(f"Skipped {filename} (already documented)")
        else:
            print(f"File not found: {filename}")

if __name__ == "__main__":
    apply_summaries()
