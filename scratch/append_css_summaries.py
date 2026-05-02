import os

workspace = r"d:\PeakForm\frontend\static\css"

summaries = {
    "charts.css": """
/*
English Summary:
This CSS file contains the specific styling rules for the dashboard charts and data visualizations. 
It ensures the charts scale properly on mobile devices and that tooltips and legends match the app's aesthetic.

סיכום בעברית:
קובץ עיצוב (CSS) זה אחראי במיוחד על המראה של הגרפים הסטטיסטיים.
הוא דואג שהגרפים לא יחתכו במסכים קטנים (כמו טלפונים ניידים), ושהצבעים של קווי ההתקדמות 
ישדרו מראה מודרני ונקי.
*/
""",
    "chat.css": """
/*
English Summary:
This CSS file is dedicated to the Community Chat interface. It styles the message bubbles, 
the sticky input area at the bottom of the screen, and manages the scrollable message container.

סיכום בעברית:
קובץ העיצוב של חדר הצ'אט! הוא צובע את הבועות של ההודעות (כמו בוואטסאפ), 
דואג שתיבת הטקסט תמיד תישאר צמודה לתחתית המסך, ומטפל בהסתרת פס הגלילה למראה נקי יותר.
*/
""",
    "components.css": """
/*
English Summary:
This CSS file is the UI component library. It defines reusable styles for cards, buttons, 
modals, inputs, and toast notifications, ensuring design consistency across all pages.

סיכום בעברית:
ספריית ה"לגו" של האתר! קובץ זה מגדיר את העיצוב לכל הכפתורים, החלונות הקופצים (Modals),
תיבות הטקסט והכרטיסיות. ככה מתכנתים לא צריכים לעצב מחדש כפתור בכל עמוד, אלא פשוט 
משתמשים בעיצוב המוכן שכאן כדי לשמור על אחידות מקצועית בכל האתר.
*/
""",
    "main.css": """
/*
English Summary:
This is the foundational CSS file. It defines the global CSS variables (colors, fonts, spacing), 
resets default browser margins, and establishes the overarching dark-mode aesthetic and layout grid.

סיכום בעברית:
הקובץ הראשי והבסיסי ביותר של העיצוב. כאן מוגדרת פלטת הצבעים הכללית (משתני CSS), הגופנים 
של האתר, והוא דואג לאפס את העיצוב המכוער שמגיע כברירת מחדל מהדפדפנים, כדי שהאתר שלנו
ייראה מודרני וחלק (Dark Mode).
*/
""",
    "workout.css": """
/*
English Summary:
This CSS file governs the styling of the Live Workout Logger. It handles complex flex/grid 
layouts for exercise sets, the floating stopwatch timer, and active visual states (e.g., completed sets).

סיכום בעברית:
קובץ עיצוב המוקדש בלעדית ליומן האימונים. הוא מסדר את השורות של הסטים בתוך טבלאות חכמות 
(Grid), צובע סט שהושלם בירוק זוהר (כדי לסמן הצלחה), ודואג שטיימר המנוחה ירחף בצורה יפה 
מעל שאר התוכן.
*/
"""
}

def apply_summaries():
    for filename, summary in summaries.items():
        filepath = os.path.join(workspace, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
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
