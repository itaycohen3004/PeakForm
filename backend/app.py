import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv()

from backend.models.db import init_db, close_db
from backend.services.setup_service import ensure_admin_exists
from backend.services.socket_service import register_socket_events

from backend.routes.auth import auth_bp
from backend.routes.athletes import athletes_bp
from backend.routes.workouts import workouts_bp
from backend.routes.exercises import exercises_bp
from backend.routes.templates import templates_bp
from backend.routes.body_weight import body_weight_bp
from backend.routes.goals import goals_bp
from backend.routes.ai import ai_bp
from backend.routes.notifications import notifications_bp
from backend.routes.admin import admin_bp
from backend.routes.community import community_bp
from backend.routes.chat import chat_bp


socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend", "static"),
        static_url_path="/static",
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "peakform_dev_secret")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    CORS(app, supports_credentials=True)

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

    socketio.init_app(app)
    register_socket_events(socketio)

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    pages_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "pages")

    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        return send_from_directory(uploads_dir, filename)

    @app.route("/")
    def index():
        return send_from_directory(pages_dir, "index.html")

    @app.route("/<path:filename>")
    def serve_page(filename):
        page_path = os.path.join(pages_dir, filename)
        if os.path.isfile(page_path):
            return send_from_directory(pages_dir, filename)
        return jsonify({"error": "Not found"}), 404

    app.teardown_appcontext(close_db)
    return app


def main():
    app = create_app()

    with app.app_context():
        init_db(app)
        print("[OK] Database initialized")

        ensure_admin_exists()
        print("[OK] Admin check complete")

        try:
            from database.migrate import migrate
            migrate()
            print("[OK] Migrations complete")
        except Exception as e:
            print(f"[Warning] Migration skipped or failed: {e}")

    port = int(os.getenv("FLASK_PORT", 5001))

    print(f"[PeakForm] Server running on https://localhost:{port}")
    print("Demo login: admin@peakform.app / Admin@1234")

    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=True,
        ssl_context="adhoc",
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()