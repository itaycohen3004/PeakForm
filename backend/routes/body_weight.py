"""
Body weight routes — logging and chart data.
זהו הקובץ שאחראי על משקל הגוף! פה אנחנו שומרים מעקב משקלים ואפילו
תמונות התקדמות מול המראה שמתאמנים יכולים להעלות.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.body_weight import (
    log_body_weight, get_body_weight_logs,
    delete_body_weight_log, get_latest_body_weight,
)
import os

# הכתובת של אזור משקל הגוף תמיד תתחיל ב /api/body-weight
body_weight_bp = Blueprint("body_weight", __name__, url_prefix="/api/body-weight")

# תיקייה מיוחדת לשמור בה את התמונות!
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "progress_photos")


# מביא לנו את היסטוריית השקילות של המתאמן כדי לצייר לו גרף יפה באפליקציה
@body_weight_bp.route("", methods=["GET"])
@require_auth
def list_logs():
    limit = int(request.args.get("limit", 90)) # מביא 90 מדידות אחרונות
    rows  = get_body_weight_logs(g.user_id, limit)
    return jsonify([dict(r) for r in rows]), 200


# המתאמן נשקל ורוצה לשמור את התוצאה למערכת
@body_weight_bp.route("", methods=["POST"])
@require_auth
def add_log():
    data = request.get_json(silent=True) or {}
    weight = data.get("weight_kg") # כמה הוא שוקל עכשיו בק"ג
    if not weight:
        return jsonify({"error": "weight_kg required"}), 400
    log_id = log_body_weight(
        g.user_id, float(weight),
        notes=data.get("notes"),
        logged_at=data.get("logged_at"),
    )
    return jsonify({"id": log_id, "message": "Weight logged."}), 201


# במקרה שהמתאמן גם רוצה להעלות תמונה כדי לראות את השינוי בעיניים
@body_weight_bp.route("/photo", methods=["POST"])
@require_auth
def upload_photo():
    """Upload a progress photo alongside a weight entry."""
    weight = request.form.get("weight_kg")
    notes  = request.form.get("notes", "")
    date   = request.form.get("logged_at")
    file   = request.files.get("photo") # לוקחים את הקובץ של התמונה מהדפדפן

    if not weight:
        return jsonify({"error": "weight_kg required"}), 400

    photo_path = None
    if file and file.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        # נותנים לתמונה שם ארוך וייחודי כדי שלא תדרוס תמונה של מישהו אחר
        filename = f"user{g.user_id}_{__import__('datetime').datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        photo_path = os.path.join(UPLOAD_DIR, filename)
        file.save(photo_path) # שומרים בכונן
        photo_path = f"/uploads/progress_photos/{filename}" # שומרים רק את הקישור למסד הנתונים

    log_id = log_body_weight(g.user_id, float(weight), notes=notes, photo_path=photo_path, logged_at=date)
    return jsonify({"id": log_id, "message": "Weight logged with photo."}), 201


# מחיקה של רישום משקל (אם לחצתי בטעות "100" במקום "80")
@body_weight_bp.route("/<int:log_id>", methods=["DELETE"])
@require_auth
def delete_log(log_id):
    delete_body_weight_log(log_id)
    return jsonify({"message": "Log deleted."}), 200


# מביא את השקילה הכי חדשה של המתאמן (משקל עדכני להיום)
@body_weight_bp.route("/latest", methods=["GET"])
@require_auth
def latest():
    row = get_latest_body_weight(g.user_id)
    return jsonify(dict(row) if row else {}), 200

"""
English Summary:
This file handles the body weight tracking routes. It allows an athlete to record their 
daily/weekly weight, upload a progress photo along with a weight log, retrieve a historical list 
of weight measurements (used for charts), and fetch their latest weight metric. 

סיכום בעברית:
קובץ זה מנהל את כל תחום מעקב המשקל של המתאמן. הוא מאפשר להזין שקילה חדשה (ואפילו לצרף
תמונת "לפני ואחרי" שתישמר בתיקייה מאובטחת), למחוק שקילה אם הייתה טעות בהקלדה, 
ולשלוף היסטוריה מלאה של המשקלים כדי שהאפליקציה תוכל לצייר גרף התקדמות מרשים במסך הבית.
"""
