"""
PeakForm — Goals routes (fixed, complete, no crashes).
כאן מנהלים את ה"מטרות" שהמתאמנים מציבים לעצמם (כמו: להרים 100 קילו, לרדת 5 קילו).
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.goal import (
    create_goal, get_goals, get_goal,
    update_goal_progress, delete_goal, VALID_GOAL_TYPES,
    update_goal_photo, get_goal_with_details
)
import os
from werkzeug.utils import secure_filename

goals_bp = Blueprint("goals", __name__, url_prefix="/api/goals")


# מביא את רשימת כל המטרות שלי
@goals_bp.route("", methods=["GET"])
@require_auth
def list_goals():
    # האם להציג גם מטרות שכבר השלמתי?
    include_completed = request.args.get("include_completed", "true").lower() == "true"
    rows = get_goals(g.user_id, include_completed)
    return jsonify([dict(r) for r in rows]), 200


# יצירת מטרה חדשה לחלוטין! (כמו: יעד ירידה במשקל עד החופש הגדול)
@goals_bp.route("", methods=["POST"])
@require_auth
def create():
    data = request.get_json(silent=True) or {}
    goal_type = data.get("goal_type", "").strip()

    # בודקים שהמתאמן בחר סוג הגיוני של מטרה
    if goal_type not in VALID_GOAL_TYPES:
        return jsonify({"error": f"Invalid goal_type. Valid: {', '.join(VALID_GOAL_TYPES)}"}), 400

    if not data.get("title", "").strip():
        return jsonify({"error": "title is required"}), 400

    # מוודאים שמספר היעד גדול מאפס (למשל, לרוץ מרחק 0 ק"מ זה לא יעד)
    try:
        target = float(data.get("target_value", 0))
        if target <= 0:
            raise ValueError("target must be positive")
    except (ValueError, TypeError):
        return jsonify({"error": "target_value must be a positive number"}), 400

    try:
        goal_id = create_goal(g.user_id, data)
    except Exception as e:
        return jsonify({"error": f"Failed to create goal: {str(e)}"}), 500

    return jsonify({"id": goal_id, "message": "Goal created."}), 201


# מביא פרטים מפורטים במיוחד רק על מטרה אחת ספציפית
@goals_bp.route("/<int:goal_id>", methods=["GET"])
@require_auth
def get_one(goal_id):
    row = get_goal_with_details(goal_id)
    if not row or row["user_id"] != g.user_id: # בודקים שאנחנו לא גונבים מטרה של מישהו אחר
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row)), 200


# עדכון ההתקדמות במטרה (כמו למשל: אם המטרה היא להגיע ל-80 קילו, והיום הגעתי ל-85)
@goals_bp.route("/<int:goal_id>/progress", methods=["PATCH"])
@require_auth
def update_progress(goal_id):
    row = get_goal(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    try:
        current = float(data["current_value"]) if "current_value" in data else None
    except (ValueError, TypeError):
        return jsonify({"error": "current_value must be a number"}), 400
        
    # עדכון בבסיס הנתונים ובדיקה האם כבר הגענו אל 100% והשגנו את המטרה?
    completed = update_goal_progress(goal_id, current)

    # אם בזכות העדכון הזה סיימנו את המטרה לגמרי, המערכת תשלח לנו התראה עם ציור של גביע!
    if completed:
        try:
            from backend.routes.notifications import create_notification
            create_notification(
                g.user_id, "goal_completed",
                "🏆 Goal Completed!",
                f'You achieved your goal: "{row["title"]}"! Congratulations!',
                "/achievements.html"
            )
        except Exception:
            pass

    return jsonify({"message": "Progress updated.", "is_completed": completed}), 200


# מחיקת מטרה אם ויתרנו עליה
@goals_bp.route("/<int:goal_id>", methods=["DELETE"])
@require_auth
def remove(goal_id):
    row = get_goal(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    delete_goal(goal_id)
    return jsonify({"message": "Goal deleted."}), 200


# העלאת תמונה למטרה (למשל תמונה עם משקולת ענקית כששברנו שיא)
@goals_bp.route("/<int:goal_id>/photo", methods=["POST"])
@require_auth
def upload_photo(goal_id):
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400

    file = request.files["photo"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    row = get_goal(goal_id)
    if not row or row["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404

    # שומרים בתיקייה שנקראת 'achievements' (הישגים)
    upload_folder = os.path.join(os.getcwd(), "frontend", "static", "uploads", "achievements")
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(f"achievement_{goal_id}_{file.filename}")
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    photo_url = f"/static/uploads/achievements/{filename}"
    update_goal_photo(goal_id, photo_url)

    return jsonify({"message": "Photo uploaded.", "photo_url": photo_url}), 200

"""
English Summary:
This file handles the API routes for managing user goals. It provides operations to list, create, 
update, and delete fitness goals (such as weight lifting targets or body weight targets). It includes
logic to detect when a goal is completed in order to trigger a system notification. It also allows 
users to upload achievement photos linked to specific goals.

סיכום בעברית:
קובץ זה מנהל את הצבת היעדים של המתאמנים (כמו להגיע למשקל גוף מסוים או להרים משקל מסוים בתרגיל).
הוא מאפשר ליצור יעדים חדשים, לעדכן התקדמות ולמחוק יעדים ישנים. הקובץ גם יודע לזהות מתי מתאמן השלים
יעד ב-100%, ובאותו רגע הוא שולח לו התראה משמחת למערכת. בנוסף, הוא תומך בהעלאת "תמונות ניצחון" 
לכל יעד שהושלם.
"""
