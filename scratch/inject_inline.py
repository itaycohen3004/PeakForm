import os

# הוספת הערות ל-CSS
css_comments = {
    "main.css": [
        ("body {", "/* הגדרות של כל העמוד (רקע שחור, פונטים) */\nbody {"),
        (":root {", "/* משתנים (Variables) - כאן נשמור צבעים כמו ירוק ניאון כדי להשתמש בהם בכל האתר */\n:root {")
    ],
    "components.css": [
        (".btn {", "/* עיצוב כפתורים גלובלי - עושה שהכפתור ייראה כמו כפתור אמיתי שאפשר ללחוץ עליו */\n.btn {"),
        (".card {", "/* עיצוב 'כרטיסייה' - הקופסאות האפורות היפות שעוטפות את התוכן בכל עמוד */\n.card {")
    ],
    "workout.css": [
        (".workout-timer {", "/* השעון שמרחף על המסך בזמן מנוחה בין הסטים */\n.workout-timer {"),
        (".set-row.completed {", "/* צובע את הסט בירוק ברגע שהמתאמן סיים אותו! */\n.set-row.completed {")
    ]
}

# הוספת הערות ל-HTML
html_comments = {
    "index.html": [
        ("<header", "<!-- החלק העליון של דף הבית (ההידר) - כולל לוגו וכפתורי התחברות -->\n<header"),
        ("<section id=\"features\"", "<!-- אזור ה'פיצ'רים' שמסביר מה האפליקציה שלנו יודעת לעשות -->\n<section id=\"features\"")
    ],
    "dashboard.html": [
        ("<div class=\"quick-actions\">", "<!-- אזור 'פעולות מהירות' - מאפשר התחלת אימון בקליק אחד -->\n<div class=\"quick-actions\">"),
        ("<div class=\"recent-workouts\">", "<!-- מציג את רשימת האימונים האחרונים שהמשתמש ביצע -->\n<div class=\"recent-workouts\">")
    ]
}

def inject_inline_comments():
    # CSS
    css_dir = r"d:\PeakForm\frontend\static\css"
    for filename, replacements in css_comments.items():
        filepath = os.path.join(css_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            for old, new in replacements:
                if new not in content:
                    content = content.replace(old, new)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    # HTML
    html_dir = r"d:\PeakForm\frontend\pages"
    for filename, replacements in html_comments.items():
        filepath = os.path.join(html_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            for old, new in replacements:
                if new not in content:
                    content = content.replace(old, new)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    inject_inline_comments()
    print("Injected inline HTML/CSS comments successfully.")
