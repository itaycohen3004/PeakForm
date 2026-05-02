import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

# טוענים את ההגדרות מהקבצים המיוחדים שלנו (כמו סיסמאות סודיות וכתובות)
load_dotenv('config.env')
load_dotenv('.env', override=True)

# מייבאים את החיבור למסד הנתונים (המקום שבו אנחנו שומרים את כל המידע)
from backend.models.db import init_db, close_db
from backend.services.setup_service import ensure_admin_exists
from backend.services.socket_service import register_socket_events

# ה"ראוטרים" - כל אחד מהם אחראי על חלק אחר באתר (כמו פקידים בקבלה של מלון שכל אחד מומחה במשהו אחר)
from backend.routes.auth import auth_bp # אחראי על התחברות והרשמה
from backend.routes.athletes import athletes_bp # אחראי על הפרופיל של המתאמן
from backend.routes.workouts import workouts_bp # אחראי על האימונים
from backend.routes.exercises import exercises_bp # אחראי על רשימת התרגילים
from backend.routes.templates import templates_bp # אחראי על תבניות אימון (תוכניות אימון)
from backend.routes.body_weight import body_weight_bp # אחראי על מעקב משקל
from backend.routes.goals import goals_bp # אחראי על יעדים ומטרות
from backend.routes.ai import ai_bp # אחראי על מאמן הבינה המלאכותית שלנו!
from backend.routes.notifications import notifications_bp # אחראי על התראות
from backend.routes.admin import admin_bp # אחראי על מסך המנהל
from backend.routes.community import community_bp # אחראי על הפיד של הקהילה (כמו פייסבוק קטן)
from backend.routes.chat import chat_bp # אחראי על הצ'אט

# פותחים חיבור מהיר (Socket) כדי שהצ'אט וההתראות יעבדו בזמן אמת, בלי לרענן את הדף
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    """
    הפונקציה הזו היא ה"בנאי" של האתר שלנו. היא יוצרת את האפליקציה ומגדירה אותה.
    """
    app = Flask(
        __name__,
        # אומרים לאתר איפה נמצאים כל הקבצים שמרכיבים את התצוגה (תמונות, צבעים, וקוד של הדפדפן)
        static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "static"),
        static_url_path="/static",
    )

    # המפתח הסודי של האפליקציה (כמו הקוד של הכספת שלנו, שומר על בטיחות הנתונים)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "peakform_dev_secret")
    
    # מגבילים את גודל הקבצים שאפשר להעלות כדי שלא יפוצצו לנו את השרת (עד 16 מגה-בייט)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    # הגדרות אבטחה של עוגיות (Cookies) - כדי שהאקרים לא יגנבו לנו מידע דרך הדפדפן
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    # מאפשרים לאתר לקבל בקשות בטוחות מכל מיני מקומות (CORS)
    CORS(app, supports_credentials=True)

    # כאן אנחנו "מחברים" את כל הפקידים (הראוטרים) שלנו לשרת הראשי כדי שידעו לענות לבקשות
    for bp in [
        auth_bp,
        athletes_bp,
        workouts_bp,
        exercises_bp,
        templates_bp,
        body_weight_bp,
        goals_bp,
        ai_bp,
        notifications_bp,
        admin_bp,
        community_bp,
        chat_bp,
    ]:
        app.register_blueprint(bp)

    # מפעילים את החיבור המהיר של הצ'אט (SocketIO)
    socketio.init_app(app)
    register_socket_events(socketio)

    # מגדירים תיקיות חשובות: אחת לשמירת קבצים שמעלים, ואחת שמכילה את הדפים (HTML) של האתר
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    pages_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "pages")

    # כשהמשתמש מבקש לראות תמונה או קובץ שהועלה, אנחנו שולחים לו את זה מהתיקייה
    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(uploads_dir, filename)

    # כשמשתמש נכנס לכתובת הראשית של האתר (רק /), שולחים לו את עמוד הבית
    @app.route("/")
    def index():
        return send_from_directory(pages_dir, "index.html")

    # כשמשתמש מבקש דף מסוים (למשל login.html) אנחנו מביאים לו את הדף מהתיקייה
    @app.route("/<path:filename>")
    def serve_page(filename):
        page_path = os.path.join(pages_dir, filename)
        if os.path.isfile(page_path):
            return send_from_directory(pages_dir, filename)
        # אם הוא ביקש דף שלא קיים, מחזירים לו שגיאה 404 (שגיאה מפורסמת באינטרנט שאומרת "לא מצאנו")
        return jsonify({"error": "Not found"}), 404

    # ברגע שמסיימים לטפל בבקשה, מנתקים את החיבור למסד הנתונים בצורה מסודרת
    app.teardown_appcontext(close_db)
    
    return app


def main():
    """
    הפונקציה המרכזית שמתחילה להפעיל את הכל! כמו ללחוץ על מתג ההפעלה של האתר.
    """
    app = create_app()

    # לפני שמדליקים את האתר, מוודאים שהכל תקין במסד הנתונים
    with app.app_context():
        init_db(app) # מכינים את מסד הנתונים
        print("[OK] Database initialized") # מדפיסים למתכנת שהכל בסדר

        ensure_admin_exists() # בודקים שיש מנהל ראשי למערכת (כדי שמישהו יוכל לנהל אותה!)
        print("[OK] Admin check complete")

        # מעדכנים את מסד הנתונים למבנה הכי חדש אם צריך (נקרא בשפה המקצועית "מיגרציה")
        try:
            from database.migrate import migrate
            migrate()
            print("[OK] Migrations complete")
        except Exception as e:
            # אם זה נכשל, נדפיס אזהרה למתכנת אבל לא נתרסק
            print(f"[Warning] Migration skipped or failed: {e}")

    # בודקים באיזה "פורט" (כמו ערוץ בטלוויזיה) השרת שלנו אמור לעבוד (בדרך כלל 5001 או 5000)
    port = int(os.getenv("FLASK_PORT", 5001))

    # מדפיסים למסך הודעה נחמדה שמסבירה לאן להיכנס כדי לראות את האתר
    print(f"[PeakForm] Server running on https://localhost:{port}")
    print("Demo login: admin@peakform.app / Admin@1234")

    # מפעילים את השרת עם אפשרות לחיבורים מאובטחים (https)
    socketio.run(
        app,
        host="0.0.0.0", # אומר שאפשר להתחבר אלינו מכל רשת
        port=port,
        debug=True, # במצב "בדיקת באגים" (למפתחים)
        ssl_context="adhoc", # מפעיל הצפנת תקשורת בסיסית וזמנית
        allow_unsafe_werkzeug=True,
    )

# השורות האלה אומרות "אם מפעילים את הקובץ הזה ישירות, תפעיל את הפונקציה המרכזית main()"
if __name__ == "__main__":
    main()

"""
English Summary:
This is the main entry point for the PeakForm backend application. It configures the Flask server,
registers all modular routing blueprints, and initializes the database and WebSocket connections.
It securely serves static assets and dynamically resolves page routes, while enforcing security 
measures like cookie protection and content length restrictions.

סיכום בעברית:
זהו הקובץ הראשי שמפעיל את כל השרת של המערכת. הוא מגדיר את השרת, מחבר את כל "הפקידים" (הראוטרים)
שאחראים על חלקים שונים באתר, ומכין את מסד הנתונים ואת הצ'אט לעבודה. בנוסף, הוא שומר על אבטחת
האתר על ידי הגבלות העלאת קבצים והצפנת תקשורת.
"""