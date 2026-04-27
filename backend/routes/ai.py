"""
AI coaching routes — conversational coaching and progression analysis.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.services.ai_service import (
    run_coaching_chat, analyze_workout_progression,
    save_ai_message, get_ai_history, build_athlete_context,
    suggest_achievement_deadline
)

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

def _build_context(user_id: int) -> str:
    from backend.models.athlete import get_athlete_profile
    from backend.models.workout import get_full_workout, get_workouts
    from backend.models.goal import get_goals

    profile = get_athlete_profile(user_id)
    recent_ids = get_workouts(user_id, limit=4)
    recent_workouts = [get_full_workout(w["id"]) for w in recent_ids]
    goals = get_goals(user_id, include_completed=False)
    return build_athlete_context(
        dict(profile) if profile else {},
        [w for w in recent_workouts if w],
        [dict(g2) for g2 in goals],
    )


@ai_bp.route("/status", methods=["GET"])
def ai_status():
    """Public endpoint to check if the AI key is configured."""
    import os
    key = os.getenv("GEMINI_API_KEY", "")
    configured = bool(key and key != "your_gemini_api_key_here")
    return jsonify({"configured": configured}), 200


@ai_bp.route("/chat", methods=["POST"])
@require_auth
def chat():
    data    = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message required"}), 400

    history = get_ai_history(g.user_id, limit=12)
    context = _build_context(g.user_id)

    reply = run_coaching_chat(message, context, history)

    save_ai_message(g.user_id, "user", message, context)
    save_ai_message(g.user_id, "assistant", reply)

    return jsonify({"reply": reply}), 200


@ai_bp.route("/history", methods=["GET"])
@require_auth
def history():
    rows = get_ai_history(g.user_id, limit=50)
    return jsonify(rows), 200


@ai_bp.route("/history", methods=["DELETE"])
@require_auth
def clear_history():
    from backend.models.db import get_db
    db = get_db()
    db.execute("DELETE FROM ai_sessions WHERE user_id = ?", (g.user_id,))
    db.commit()
    return jsonify({"message": "History cleared."}), 200


@ai_bp.route("/analyze/<int:exercise_id>", methods=["POST"])
@require_auth
def analyze_exercise(exercise_id):
    from backend.models.exercise import get_exercise_by_id
    ex = get_exercise_by_id(exercise_id)
    if not ex:
        return jsonify({"error": "Exercise not found"}), 404
    context = _build_context(g.user_id)
    result  = analyze_workout_progression(context, ex["name"])
    return jsonify({**result, "exercise_name": ex["name"]}), 200


@ai_bp.route("/suggest-next-workout", methods=["GET"])
@require_auth
def suggest_next():
    context = _build_context(g.user_id)
    reply = run_coaching_chat(
        "Based on my recent workouts and goals, what should my next workout look like? "
        "Give me a specific plan with exercises, sets, and targets.",
        context,
        [],
    )
    return jsonify({"suggestion": reply}), 200

@ai_bp.route("/suggest-deadline", methods=["POST"])
@require_auth
def suggest_deadline():
    data = request.get_json(silent=True) or {}
    context = _build_context(g.user_id)
    result = suggest_achievement_deadline(context, data)
    return jsonify(result), 200

@ai_bp.route("/analyze-workout/<int:workout_id>", methods=["POST"])
@require_auth
def analyze_workout_route(workout_id):
    from backend.models.workout import get_full_workout
    w_data = get_full_workout(workout_id)
    if not w_data:
        return jsonify({"error": "Workout not found"}), 404
        
    # Find previous workout for the same template if available
    from backend.models.db import get_db
    db = get_db()
    prev_summary = None
    if w_data.get("template_id"):
        prev = db.execute('''
            SELECT * FROM workouts 
            WHERE user_id = ? AND template_id = ? AND id < ?
            ORDER BY workout_date DESC LIMIT 1
        ''', (g.user_id, w_data["template_id"], workout_id)).fetchone()
        if prev:
            prev_data = get_full_workout(prev["id"])
            prev_sum = sum(s["weight_kg"] * s["reps"] 
                           for e in prev_data.get("exercises", []) 
                           for s in e.get("sets", []) 
                           if s.get("weight_kg") and s.get("reps"))
            prev_summary = f"Previous Session total volume: {prev_sum} kg"
            
    cur_sum = sum(s["weight_kg"] * s["reps"] 
                  for e in w_data.get("exercises", []) 
                  for s in e.get("sets", []) 
                  if s.get("weight_kg") and s.get("reps"))
    
    from backend.services.ai_service import analyze_workout_recap
    recap = analyze_workout_recap(w_data, cur_sum, prev_summary)
    
    return jsonify({"analysis": recap}), 200


@ai_bp.route("/save-template", methods=["POST"])
@require_auth
def save_template():
    """
    Save an AI-generated template JSON to the user's workout templates.
    Called from ai-coach.html when the AI generates a full program.
    """
    data = request.get_json(silent=True) or {}
    tpl  = data.get("template", {})
    if not tpl or not tpl.get("name"):
        return jsonify({"error": "Template name required"}), 400

    from backend.models.template import create_template, add_exercise_to_template
    from backend.models.exercise import find_exercise_by_name
    from backend.models.db import get_db

    tpl_id = create_template(
        g.user_id,
        tpl["name"],
        training_type=tpl.get("training_type", "gym"),
        notes=tpl.get("notes", "Created by AI Coach"),
    )

    saved_exercises = 0
    for pos, ex_data in enumerate(tpl.get("exercises", [])):
        ex_name = ex_data.get("exercise_name", "")
        ex = find_exercise_by_name(ex_name)
        if not ex:
            continue
        add_exercise_to_template(
            tpl_id, ex["id"],
            position=pos,
            default_sets=ex_data.get("default_sets", 3),
            notes=ex_data.get("notes", ""),
        )
        saved_exercises += 1

    return jsonify({
        "message":         f"Template '{tpl['name']}' saved!",
        "template_id":     tpl_id,
        "exercises_saved": saved_exercises,
    }), 201
