"""
AI coaching routes — conversational coaching and progression analysis.
"""
import json
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.services.ai_service import (
    run_coaching_chat, analyze_workout_progression,
    save_ai_message, get_ai_history, build_athlete_context,
    suggest_achievement_deadline, _coach, SYSTEM_PROMPT,
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
    print(f"[AI Route] /api/ai/chat called: user={g.user_id} msg_len={len(message)}")

    if not message:
        return jsonify({"error": "message required"}), 400

    history = get_ai_history(g.user_id, limit=12)
    context = _build_context(g.user_id)
    print(f"[AI Route] Context built ({len(context)} chars), history={len(history)} msgs")

    reply = run_coaching_chat(message, context, history)
    print(f"[AI Route] Reply generated ({len(reply)} chars)")

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

@ai_bp.route("/next-session/<int:workout_id>", methods=["POST"])
@require_auth
def next_session_plan(workout_id):
    """
    Recommend the next workout session: per-exercise weight + rep targets
    based on the athlete's last performance on this workout.
    """
    from backend.models.workout import get_full_workout
    from backend.models.db import get_db

    w_data = get_full_workout(workout_id)
    if not w_data:
        return jsonify({"error": "Workout not found"}), 404

    db = get_db()

    # ── Build previous session summary ─────────────────────────
    exercises = w_data.get("exercises", [])
    ex_summaries = []
    for ex in exercises:
        work_sets = [s for s in ex.get("sets", []) if not s.get("is_warmup")]
        if not work_sets:
            continue
        best_weight = max((s.get("weight_kg") or 0 for s in work_sets), default=0)
        best_reps   = max((s.get("reps") or 0 for s in work_sets), default=0)
        avg_reps    = (
            sum(s.get("reps") or 0 for s in work_sets) / len(work_sets)
            if work_sets else 0
        )
        total_sets  = len(work_sets)
        set_type    = ex.get("set_type", "reps_weight")
        ex_summaries.append({
            "name":        ex.get("exercise_name", "Unknown"),
            "set_type":    set_type,
            "total_sets":  total_sets,
            "best_weight": best_weight,
            "best_reps":   best_reps,
            "avg_reps":    round(avg_reps, 1),
            "all_sets":    work_sets,
        })

    # ── Rule-based progression (works without AI) ───────────────
    rule_based = []
    for ex in ex_summaries:
        st = ex["set_type"]
        rec = {"exercise": ex["name"], "sets": ex["total_sets"]}
        if st == "reps_weight":
            # If all sets hit >= target reps, add 2.5 kg; else same weight, add 1 rep
            reps_hit_target = ex["avg_reps"] >= ex["best_reps"]
            if reps_hit_target and ex["best_weight"] > 0:
                rec["weight_kg"] = round(ex["best_weight"] + 2.5, 1)
                rec["reps"]      = ex["best_reps"]
                rec["note"]      = "Progressive overload: +2.5 kg from last session"
            elif ex["best_weight"] > 0:
                rec["weight_kg"] = ex["best_weight"]
                rec["reps"]      = min(ex["best_reps"] + 1, 12)
                rec["note"]      = f"Same weight — aim for {rec['reps']} reps this time"
            else:
                rec["reps"]  = ex["best_reps"]
                rec["note"]  = "Bodyweight — try to beat your rep count"
        elif st == "reps_only":
            rec["reps"] = ex["best_reps"] + 1
            rec["note"] = f"Beat last session: target {rec['reps']} reps per set"
        elif st in ("time_only", "time_weight"):
            best_secs = max((s.get("duration_seconds") or 0 for s in ex["all_sets"]), default=0)
            rec["seconds"] = best_secs + 5
            rec["note"]    = f"Hold for {rec['seconds']}s — 5s longer than last time"
        rule_based.append(rec)

    # ── Try AI enhancement ──────────────────────────────────────
    ai_analysis = None
    if _coach.is_ready and ex_summaries:
        try:
            context = _build_context(g.user_id)
            ex_block = "\n".join(
                f"- {e['name']}: {e['total_sets']} sets, best {e['best_weight']}kg x {e['best_reps']} reps"
                for e in ex_summaries
            )
            prompt = f"""{SYSTEM_PROMPT}

{context}

The athlete just completed this workout on {w_data.get('workout_date')}:
{ex_block}

For their NEXT session of this exact workout, give specific targets per exercise.
Respond ONLY with valid JSON (no markdown), using this structure:
{{
  "overall_note": "<1-2 sentence overall advice>",
  "exercises": [
    {{
      "exercise": "<name>",
      "sets": <int>,
      "weight_kg": <float or null>,
      "reps": <int or null>,
      "seconds": <int or null>,
      "note": "<short coaching note>"
    }}
  ]
}}"""
            resp = _coach._client.generate_content(prompt)
            text = resp.text.strip()
            if "```" in text:
                text = text[text.find("{"):text.rfind("}")+1]
            ai_analysis = json.loads(text)
        except Exception as e:
            print(f"[AI next-session] Error: {e}")
            ai_analysis = None

    # ── Compose final response ──────────────────────────────────
    if ai_analysis and ai_analysis.get("exercises"):
        return jsonify({
            "source":       "ai",
            "workout_name": w_data.get("name", "Session"),
            "workout_date": w_data.get("workout_date"),
            "overall_note": ai_analysis.get("overall_note", ""),
            "exercises":    ai_analysis["exercises"],
        }), 200
    else:
        return jsonify({
            "source":       "rule_based",
            "workout_name": w_data.get("name", "Session"),
            "workout_date": w_data.get("workout_date"),
            "overall_note": "Progressive overload plan based on your last session.",
            "exercises":    rule_based,
        }), 200


# Keep the old route as an alias so existing links don't break
@ai_bp.route("/analyze-workout/<int:workout_id>", methods=["POST"])
@require_auth
def analyze_workout_route(workout_id):
    return next_session_plan(workout_id)


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
