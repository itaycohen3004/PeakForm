"""
PeakForm — Database connection and initialization module.
הקובץ הזה הוא "הכבל" שמחבר בין האתר שלנו לבין מסד הנתונים (המקום שבו נשמר כל המידע כמו משתמשים, אימונים והודעות).
"""

import sqlite3
import os
from flask import g
from dotenv import load_dotenv

load_dotenv()

# המיקום שבו נשמר קובץ הנתונים (כמו קובץ אקסל ענק ששומר הכל)
DATABASE_PATH = os.getenv("DATABASE_PATH", "database/peakform.db")


# פונקציה שנותנת לנו "חיבור" למסד הנתונים עבור בקשה ספציפית מהאתר
def get_db():
    """Return a database connection scoped to the current Flask request."""
    # אם עדיין אין לנו חיבור בזיכרון (g), ניצור אחד חדש!
    if "db" not in g:
        # קודם כל, מוודאים שהתיקייה של מסד הנתונים בכלל קיימת, ואם לא - יוצרים אותה
        os.makedirs(os.path.dirname(os.path.abspath(DATABASE_PATH)), exist_ok=True)
        # מתחברים לקובץ
        g.db = sqlite3.connect(
            DATABASE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            check_same_thread=False,
        )
        # אומרים לחיבור להחזיר לנו את התוצאות כמו מילון שאפשר לקרוא בו לפי שמות של עמודות
        g.db.row_factory = sqlite3.Row
        # מדליקים הגדרות שעוזרות למסד הנתונים לעבוד מהר יותר ובטוח יותר
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


# פונקציה שסוגרת את החיבור כשאנחנו מסיימים, כדי לא לבזבז זיכרון למחשב
def close_db(e=None):
    """Close the database connection at the end of a request."""
    db = g.pop("db", None) # לוקחים את החיבור
    if db is not None:
        db.close() # וסוגרים אותו!


# פונקציה שמכינה את מסד הנתונים בפעם הראשונה (בונה את כל הטבלאות)
def init_db(app):
    """Initialize the database with schema.sql if tables don't exist."""
    with app.app_context():
        db = get_db()
        # מחפשת את קובץ ההוראות (schema.sql) שמסביר אילו טבלאות צריך לבנות
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "database",
            "schema.sql",
        )
        # אם היא מוצאת את הקובץ, היא מריצה אותו כדי לבנות את הכל
        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                db.executescript(f.read())
            db.commit() # שומרים את השינויים
        close_db()


# פונקציה מיוחדת לחיבור ישיר למסד הנתונים בלי קשר לאתר הרגיל (למשל עבור תהליכי רקע מיוחדים)
def get_db_direct():
    """
    Return a standalone database connection (outside Flask request context).
    Used by background services (TCP server, scheduler).
    """
    os.makedirs(os.path.dirname(os.path.abspath(DATABASE_PATH)), exist_ok=True)
    conn = sqlite3.connect(
        DATABASE_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

"""
English Summary:
This module manages the SQLite database connection lifecycle for the application. 
It utilizes Flask's `g` object to ensure only one connection is opened per request 
and automatically closes it upon teardown. It also configures SQLite pragmas (like WAL mode 
and foreign keys) for optimal performance, provides a method to initialize the database schema, 
and exposes a direct connection method for asynchronous background services.
"""
