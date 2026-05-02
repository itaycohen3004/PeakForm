"""
Template Model — Handles creation, fetching, and weekly scheduling of Workout Templates.
קובץ "התבניות" של האימונים! תבנית היא אימון קבוע שמשתמשים יכולים להכין מראש.
למשל: תבנית שנקראת "אימון גב" ובה כתוב איזה תרגילים, כמה סטים וכמה משקל לעשות.
"""
from .db import get_db
from backend.services.encryption_service import encrypt_data, decrypt_data


# יוצר תבנית חדשה וריקה (בלי תרגילים בינתיים, רק עם שם כמו "אימון חזה")
def create_template(user_id: int, name: str, training_type: str = None, notes: str = None) -> int:
    db = get_db()
    # הערות האימון נשמרות בצורה מוצפנת כדי שאף אחד לא יקרא אותן!
    cur = db.execute(
        "INSERT INTO workout_templates (user_id, name, training_type, notes) VALUES (?, ?, ?, ?)",
        (user_id, name, training_type, encrypt_data(notes)),
    )
    db.commit()
    return cur.lastrowid # מחזיר את המספר של התבנית החדשה


# מביא את כל התבניות שיש למשתמש
def get_templates(user_id: int):
    db = get_db()
    # מבקשים את התבניות, וגם סופרים כמה תרגילים יש בתוך כל תבנית!
    rows = db.execute(
        """SELECT wt.*, COUNT(te.id) as exercise_count
           FROM workout_templates wt
           LEFT JOIN template_exercises te ON te.template_id = wt.id
           WHERE wt.user_id = ?
           GROUP BY wt.id
           ORDER BY wt.updated_at DESC""",
        (user_id,),
    ).fetchall()
    
    results = []
    for r in rows:
        d = dict(r)
        # פותחים את ההצפנה של ההערות
        d["notes"] = decrypt_data(d["notes"])
        results.append(d)
    return results


# מביא תבנית אחת ספציפית לפי המספר המזהה שלה
def get_template(template_id: int):
    db = get_db()
    return db.execute(
        "SELECT * FROM workout_templates WHERE id = ?", (template_id,)
    ).fetchone()


# מאפשר לעדכן פרטים של התבנית (כמו השם או ההערות שלה)
def update_template(template_id: int, data: dict):
    db = get_db()
    # אלו הדברים שמותר לעדכן:
    allowed = ["name","training_type","notes"]
    updates = {k: v for k, v in data.items() if k in allowed}
    
    if updates:
        if "notes" in updates: 
            updates["notes"] = encrypt_data(updates["notes"]) # מצפינים בחזרה את ההערות!
            
        # רושמים מתי זה עודכן לאחרונה
        updates["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()
        
        # בונים את פקודת העדכון למסד הנתונים
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        db.execute(f"UPDATE workout_templates SET {set_clause} WHERE id = ?",
                   list(updates.values()) + [template_id])
        db.commit()


# מוחק תבנית לחלוטין (אם למשל התוכנית הזו כבר לא רלוונטית לך)
def delete_template(template_id: int):
    db = get_db()
    db.execute("DELETE FROM workout_templates WHERE id = ?", (template_id,))
    db.commit()


# מביא את "החבילה המלאה" - גם את התבנית, גם את התרגילים שלה וגם את הסטים שבתוך התרגילים
def get_full_template(template_id: int) -> dict:
    db = get_db()
    tpl = db.execute("SELECT * FROM workout_templates WHERE id = ?", (template_id,)).fetchone()
    if not tpl:
        return None
        
    # מביאים את התרגילים (עם הפרטים שלהם מספריית התרגילים כמו "חזה", "רגליים" וכו')
    te_rows = db.execute(
        """SELECT te.*, e.name as exercise_name, e.category, e.set_type, e.muscles
           FROM template_exercises te
           JOIN exercises e ON te.exercise_id = e.id
           WHERE te.template_id = ?
           ORDER BY te.position""",
        (template_id,),
    ).fetchall()
    
    exercises = []
    # עבור כל תרגיל, נביא גם את הסטים שלו
    for te in te_rows:
        sets = db.execute(
            "SELECT * FROM template_exercise_sets WHERE template_exercise_id = ? ORDER BY set_number",
            (te["id"],),
        ).fetchall()
        ex_dict = dict(te)
        ex_dict["sets"] = [dict(s) for s in sets] # מכניסים את הסטים לתרגיל
        exercises.append(ex_dict)
        
    result = dict(tpl)
    result["notes"] = decrypt_data(result["notes"]) # פותחים את ההצפנה
    result["exercises"] = exercises # מכניסים הכל לתוך התבנית
    return result


# מוסיף תרגיל חדש לתוך התבנית
def add_exercise_to_template(template_id: int, exercise_id: int,
                              position: int = 0, default_sets: int = 3, notes: str = "") -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO template_exercises (template_id, exercise_id, position, default_sets, notes) VALUES (?,?,?,?,?)",
        (template_id, exercise_id, position, default_sets, encrypt_data(notes)),
    )
    db.commit()
    return cur.lastrowid


# מוחק תרגיל מתוך התבנית
def remove_exercise_from_template(template_exercise_id: int):
    db = get_db()
    db.execute("DELETE FROM template_exercises WHERE id = ?", (template_exercise_id,))
    db.commit()


# מגדיר מראש סט מתוכנן לתרגיל בתבנית (כמה חזרות וכמה משקל אתה "אמור" לעשות)
def add_template_set(template_exercise_id: int, data: dict) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO template_exercise_sets
           (template_exercise_id, set_number, target_reps, target_weight, target_seconds)
           VALUES (?, ?, ?, ?, ?)""",
        (
            template_exercise_id,
            data.get("set_number", 1),
            data.get("target_reps"),
            data.get("target_weight"),
            data.get("target_seconds"),
        ),
    )
    db.commit()
    return cur.lastrowid


# מוחק סט מהתבנית
def delete_template_set(set_id: int):
    db = get_db()
    db.execute("DELETE FROM template_exercise_sets WHERE id = ?", (set_id,))
    db.commit()


# ============================================================
# Weekly Schedule - סידור האימונים לפי ימים בשבוע!
# ============================================================

# משבץ תבנית אימון ליום מסוים בשבוע (למשל: ביום ראשון עושים "חזה יד אחורית")
def set_schedule(user_id: int, weekday: int, template_id: int):
    db = get_db()
    # משתמשים בטריק שמכניס רשומה, ואם היא כבר קיימת - מעדכן אותה
    db.execute(
        """INSERT INTO weekly_schedule (user_id, weekday, template_id)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, weekday) DO UPDATE SET template_id = excluded.template_id""",
        (user_id, weekday, template_id),
    )
    db.commit()


# מוחק את האימון שנקבע ליום מסוים (למשל: אני רוצה שביום שני יהיה יום מנוחה)
def clear_schedule(user_id: int, weekday: int):
    db = get_db()
    db.execute("DELETE FROM weekly_schedule WHERE user_id = ? AND weekday = ?", (user_id, weekday))
    db.commit()


# מביא את לו"ז האימונים השבועי של המשתמש
def get_schedule(user_id: int):
    db = get_db()
    return db.execute(
        """SELECT ws.weekday, ws.template_id, wt.name as template_name
           FROM weekly_schedule ws
           JOIN workout_templates wt ON ws.template_id = wt.id
           WHERE ws.user_id = ?
           ORDER BY ws.weekday""",
        (user_id,),
    ).fetchall()


# בודק איזה אימון המשתמש "אמור" לעשות היום לפי הלו"ז שהוא קבע
def get_today_template(user_id: int):
    """Return the scheduled template for today's weekday (0=Mon)."""
    import datetime
    # מברר איזה יום היום (0 = יום שני, 1 = יום שלישי וכו')
    weekday = datetime.date.today().weekday()  # 0 = Monday
    db = get_db()
    return db.execute(
        """SELECT ws.template_id, wt.name as template_name
           FROM weekly_schedule ws
           JOIN workout_templates wt ON ws.template_id = wt.id
           WHERE ws.user_id = ? AND ws.weekday = ?""",
        (user_id, weekday),
    ).fetchone()

"""
English Summary:
This file handles the logic for reusable Workout Templates. Users can construct predefined 
routines consisting of exercises and target sets. The module also includes a powerful Weekly 
Scheduler feature, allowing users to map specific templates to specific days of the week, 
making it easier to follow a structured strength training program.
"""
