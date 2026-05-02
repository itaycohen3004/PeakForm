"""
AI coaching routes — conversational coaching and progression analysis.
זהו המוח של האפליקציה! כאן אנחנו מחברים את המערכת שלנו לבינה המלאכותית (AI) 
כדי שתשמש כמאמן כושר אישי למשתמש, תבנה לו אימונים ותייעץ לו בזמן אמת.
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


# הפונקציה שאחראית על חדר הצ'אט האישי עם המאמן הווירטואלי (AI)
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


# מבקש מהמאמן החכם לנתח את ההתקדמות שלנו בתרגיל מסוים לאורך זמן
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


# פונקציה חכמה שממליצה לנו כמה משקל להרים וכמה חזרות לעשות *בסט הבא* שלנו בזמן אימון!
@ai_bp.route("/suggest-next-set", methods=["POST"])
@require_auth
def suggest_next_set():
    """
    Recommend weight/reps for the NEXT set during an active workout.

    Request body:
        exercise_id       (int, required)
        current_sets      (list of {weight_kg, reps, duration_seconds, is_warmup})
        workout_id        (int, optional — current workout being logged)

    Returns:
        {
          "source": "ai" | "rule_based" | "no_history",
          "weight_kg": float | null,
          "reps": int | null,
          "seconds": int | null,
          "rpe": str | null,
          "note": str
        }
    """
    from backend.models.exercise import get_exercise_by_id, get_exercise_history
    from backend.models.db import get_db

    data        = request.get_json(silent=True) or {}
    exercise_id = data.get("exercise_id")
    current_sets = data.get("current_sets", [])   # sets already logged in THIS workout
    workout_id  = data.get("workout_id")           # optional, for context

    if not exercise_id:
        return jsonify({"error": "exercise_id required"}), 400

    ex = get_exercise_by_id(exercise_id)
    if not ex:
        return jsonify({"error": "Exercise not found"}), 404

    set_type = ex["set_type"] or "reps_weight"

    # ── Check if the user has ANY prior history for this exercise ──────────
    history_rows = get_exercise_history(g.user_id, exercise_id, limit=30)
    if not history_rows:
        # First time ever — no AI call, just a friendly local message
        return jsonify({
            "source":   "no_history",
            "weight_kg": None,
            "reps":     None,
            "seconds":  None,
            "rpe":      None,
            "note": (
                "This is your first time doing this exercise. "
                "Give it your best effort and record your result. "
                "Future recommendations will be based on your data."
            ),
        }), 200

    # ── Build history summary (only THIS user's data) ──────────────────────
    history_lines = []
    for row in history_rows[:20]:
        parts = []
        if row["weight_kg"] is not None:
            parts.append(f"{row['weight_kg']}kg")
        if row["reps"] is not None:
            parts.append(f"{row['reps']} reps")
        if row["duration_seconds"] is not None:
            parts.append(f"{row['duration_seconds']}s")
        warmup_tag = " (warmup)" if row["is_warmup"] else ""
        history_lines.append(
            f"  [{row['workout_date']}] Set {row['set_number']}{warmup_tag}: {', '.join(parts)}"
        )

    # ── Build current-session sets description ────────────────────────────
    working_done = [s for s in current_sets if not s.get("is_warmup")]
    next_set_num = len(working_done) + 1

    current_lines = []
    for i, s in enumerate(working_done, 1):
        parts = []
        if s.get("weight_kg") is not None:
            parts.append(f"{s['weight_kg']}kg")
        if s.get("reps") is not None:
            parts.append(f"{s['reps']} reps")
        if s.get("duration_seconds") is not None:
            parts.append(f"{s['duration_seconds']}s")
        current_lines.append(f"  Set {i}: {', '.join(parts) or 'no data'}")

    # ── Rule-based fallback (always computed, used if AI fails) ────────────
    recent_working = [r for r in history_rows[:10] if not r["is_warmup"]]
    rule_rec = {}
    if recent_working:
        best_weight = max((r["weight_kg"] or 0 for r in recent_working), default=0)
        best_reps   = max((r["reps"] or 0 for r in recent_working), default=0)
        best_secs   = max((r["duration_seconds"] or 0 for r in recent_working), default=0)

        # Also factor in the current session: use what was just done as baseline
        if working_done:
            last_done = working_done[-1]
            cur_weight = last_done.get("weight_kg") or best_weight
            cur_reps   = last_done.get("reps") or best_reps
        else:
            cur_weight, cur_reps = best_weight, best_reps

        if set_type == "reps_weight":
            if cur_reps and cur_reps >= best_reps and cur_weight:
                rule_rec = {
                    "weight_kg": round(cur_weight + 2.5, 1),
                    "reps":      int(best_reps),
                    "note":      f"Great work! Try +2.5 kg for Set {next_set_num}.",
                }
            else:
                rule_rec = {
                    "weight_kg": float(cur_weight),
                    "reps":      min(int(cur_reps or best_reps) + 1, 15),
                    "note":      f"Keep the same weight and aim for one more rep on Set {next_set_num}.",
                }
        elif set_type == "reps_only":
            rule_rec = {
                "reps": int(best_reps) + 1,
                "note": f"Try for {int(best_reps) + 1} reps on Set {next_set_num}.",
            }
        elif set_type in ("time_only", "time_weight"):
            rule_rec = {
                "seconds": int(best_secs) + 5,
                "note":    f"Try to hold for {int(best_secs) + 5}s on Set {next_set_num}.",
            }

    rule_rec.setdefault("source", "rule_based")

    # ── Try AI enhancement ─────────────────────────────────────────────────
    if _coach.is_ready:
        try:
            context = _build_context(g.user_id)
            history_block   = "\n".join(history_lines) or "  (no previous sets recorded)"
            current_block   = "\n".join(current_lines) or "  (this is the first set)"

            prompt = f"""{SYSTEM_PROMPT}

{context}

The athlete is currently logging a workout and needs a recommendation for Set {next_set_num} of:
Exercise: {ex['name']} (set_type: {set_type})

--- Recent history for this exercise (newest sessions first) ---
{history_block}

--- Current workout — working sets already completed TODAY ---
{current_block}

Your task: Recommend EXACTLY what the athlete should do for Set {next_set_num}.

=== STRICT PROGRESSIVE OVERLOAD RULES (follow all of these) ===

1. SMALL INCREMENTS ONLY — the maximum weight increase vs the athlete's recent best is +2.5 kg.
   For beginners or if recent performance was shaky, limit increases to +1.25 kg.
   NEVER suggest more than +5 kg in a single session. Weight jumps like +10 kg, +20 kg are FORBIDDEN.

2. FATIGUE AWARENESS — as set number increases, performance naturally drops:
   - Set 1 or 2: the athlete may match or slightly beat their recent best weight/reps.
   - Set 3+: suggest the SAME weight as the previous set in this workout (not history).
   - Set 4+: it is completely normal and encouraged to suggest a slight DECREASE in weight (e.g. -2.5 kg)
     or a reduction of 1-2 reps. Do NOT push the athlete to maintain a weight they are clearly fatiguing on.

3. CURRENT SESSION BASELINE — the most important reference is what the athlete just did in Sets 1–{next_set_num - 1}
   of THIS workout (shown above). Use these numbers as the primary baseline, not old history.
   Old history is secondary context only.

4. REPS TARGET — aim for the same rep range as recent sets. If the athlete hit their target reps,
   suggest the same reps at the same or slightly higher weight. If they fell short, keep weight and
   suggest aiming for 1 more rep — do NOT increase weight.

5. SET TYPE RULES:
   - reps_weight: always provide weight_kg and reps; set seconds to null.
   - reps_only: weight_kg must be null; provide only reps.
   - time_only: weight_kg and reps must be null; provide only seconds (add 5–10s to recent best if early sets, or match if late sets).
   - time_weight: provide both weight_kg and seconds; reps is null.

6. TONE: Be brief (1 sentence max for the note), specific, grounded, and encouraging.
   Example good notes: "Match Set 1 — you had great form." / "Slight drop to 70 kg, you'll still get a great stimulus."
   Avoid vague or generic phrases like "push yourself" or "give it your all".

Respond ONLY with valid JSON (no markdown, no explanation outside the JSON):
{{
  "weight_kg": <float or null>,
  "reps": <int or null>,
  "seconds": <int or null>,
  "rpe": "<e.g. '7-8' or null>",
  "note": "<1 concise coaching sentence>"
}}"""
            resp = _coach._client.generate_content(prompt)
            text = resp.text.strip()
            if "```" in text:
                text = text[text.find("{"):text.rfind("}")+1]
            ai_data = json.loads(text)
            ai_data["source"] = "ai"
            print(f"[AI suggest-next-set] exercise_id={exercise_id} set={next_set_num} → {ai_data}")
            return jsonify(ai_data), 200

        except Exception as e:
            print(f"[AI suggest-next-set] AI failed, using rule-based fallback: {e}")
            # Fall through to rule-based

    # Return rule-based recommendation
    return jsonify(rule_rec), 200



@ai_bp.route("/suggest-all-sets", methods=["POST"])
@require_auth
def suggest_all_sets():
    """
    Generate recommendations for ALL sets of one exercise in a single AI call.

    Request body:
        exercise_id   (int, required)
        num_sets      (int, required)   -- total sets planned for this exercise
        current_sets  (list, optional)  -- sets already entered (may be partial)
        workout_id    (int, optional)

    Returns:
        {
          "source": "ai" | "rule_based" | "no_history",
          "sets": [
            {"set_number": 1, "weight_kg": ..., "reps": ..., "seconds": ..., "rpe": ..., "note": "..."},
            ...
          ],
          "overall_note": str
        }
    """
    from backend.models.exercise import get_exercise_by_id, get_exercise_history

    data         = request.get_json(silent=True) or {}
    exercise_id  = data.get("exercise_id")
    num_sets     = int(data.get("num_sets", 3))
    current_sets = data.get("current_sets", [])

    if not exercise_id:
        return jsonify({"error": "exercise_id required"}), 400

    ex = get_exercise_by_id(exercise_id)
    if not ex:
        return jsonify({"error": "Exercise not found"}), 404

    set_type = ex["set_type"] or "reps_weight"
    num_sets = max(1, min(num_sets, 10))

    # No history -> first-time message, skip AI
    history_rows = get_exercise_history(g.user_id, exercise_id, limit=30)
    if not history_rows:
        return jsonify({
            "source": "no_history",
            "sets":   [],
            "overall_note": (
                "This is your first time doing this exercise. "
                "Give it your best effort and record your results — "
                "future AI recommendations will be based on your data."
            ),
        }), 200

    # Build history summary lines
    history_lines = []
    for row in history_rows[:20]:
        parts = []
        if row["weight_kg"]        is not None: parts.append(f"{row['weight_kg']}kg")
        if row["reps"]             is not None: parts.append(f"{row['reps']} reps")
        if row["duration_seconds"] is not None: parts.append(f"{row['duration_seconds']}s")
        tag = " (warmup)" if row["is_warmup"] else ""
        history_lines.append(
            f"  [{row['workout_date']}] Set {row['set_number']}{tag}: {', '.join(parts)}"
        )

    recent_w    = [r for r in history_rows[:10] if not r["is_warmup"]]
    best_weight = max((r["weight_kg"] or 0 for r in recent_w), default=0) if recent_w else 0
    best_reps   = max((r["reps"] or 0 for r in recent_w), default=0)      if recent_w else 0
    best_secs   = max((r["duration_seconds"] or 0 for r in recent_w), default=0) if recent_w else 0

    # Rule-based per-set generator with fatigue factor
    def make_rule_set(set_num):
        fatigue = (set_num - 1) * 0.025   # 2.5% reduction per subsequent set
        rec = {"set_number": set_num, "weight_kg": None, "reps": None, "seconds": None, "rpe": None}
        if set_type == "reps_weight":
            w = round(best_weight * (1 - fatigue) * 2) / 2 if best_weight else None
            r = max(1, int(best_reps * (1 - fatigue * 0.5))) if best_reps else None
            rec.update(weight_kg=w, reps=r)
            if set_num == 1:   rec["note"] = f"Start at {w}kg x {r} reps - match your recent best."
            elif set_num == 2: rec["note"] = f"Hold {w}kg - you should still have plenty left."
            else:              rec["note"] = f"Natural fatigue drop - {w}kg x {r} reps is solid."
        elif set_type == "reps_only":
            r = max(1, int(best_reps * (1 - fatigue * 0.5))) if best_reps else None
            rec.update(reps=r)
            rec["note"] = f"Target {r} reps." if r else "Give it your best."
        elif set_type in ("time_only", "time_weight"):
            s = max(5, int(best_secs * (1 - fatigue * 0.5))) if best_secs else None
            rec.update(seconds=s)
            if set_type == "time_weight":
                w = round(best_weight * (1 - fatigue) * 2) / 2 if best_weight else None
                rec["weight_kg"] = w
            rec["note"] = f"Hold for {s}s." if s else "Do your best."
        return rec

    rule_sets = [make_rule_set(i + 1) for i in range(num_sets)]
    rule_result = {
        "source":       "rule_based",
        "sets":         rule_sets,
        "overall_note": "Conservative fatigue-adjusted plan based on your recent performance.",
    }

    if not _coach.is_ready:
        return jsonify(rule_result), 200

    try:
        context       = _build_context(g.user_id)
        history_block = "\n".join(history_lines) or "  (no previous sets recorded)"

        current_block = ""
        if current_sets:
            lines = []
            for i, s in enumerate(current_sets, 1):
                parts = []
                if s.get("weight_kg")        is not None: parts.append(f"{s['weight_kg']}kg")
                if s.get("reps")             is not None: parts.append(f"{s['reps']} reps")
                if s.get("duration_seconds") is not None: parts.append(f"{s['duration_seconds']}s")
                lines.append(f"  Set {i}: {', '.join(parts) or 'empty'}")
            current_block = "\n--- Sets already entered this session ---\n" + "\n".join(lines)

        # Build the JSON template rows for the prompt
        set_rows = "\n".join(
            f'    {{"set_number":{i+1},"weight_kg":<float|null>,"reps":<int|null>,"seconds":<int|null>,"rpe":"<str|null>","note":"<str>"}},'
            for i in range(num_sets)
        )

        prompt = (
            f"{SYSTEM_PROMPT}\n\n{context}\n\n"
            f"Provide recommendations for ALL {num_sets} sets of:\n"
            f"Exercise: {ex['name']} (set_type: {set_type})\n\n"
            f"--- Recent history (newest first) ---\n{history_block}{current_block}\n\n"
            f"STRICT RULES:\n"
            f"1. Return exactly {num_sets} sets.\n"
            f"2. FATIGUE: weight/reps must stay the same or DECREASE across sets - never increase.\n"
            f"3. Set 1 = realistic best (max +2.5kg above recent). Set 2 = same weight. "
            f"Set 3+ = -0 to -2.5kg. Set 4+ = -2.5 to -5kg.\n"
            f"4. Reps stay within 2 of historical best.\n"
            f"5. set_type rules: reps_weight=weight_kg+reps; reps_only=reps (weight_kg=null); "
            f"time_only=seconds; time_weight=weight_kg+seconds.\n"
            f"6. Note = 1 specific sentence per set. Overall note = 1-2 sentences.\n\n"
            f"Valid JSON only (no markdown):\n"
            f'{{\n  "overall_note": "<summary>",\n  "sets": [\n{set_rows}\n  ]\n}}'
        )

        resp = _coach._client.generate_content(prompt)
        text = resp.text.strip()
        if "```" in text:
            text = text[text.find("{"):text.rfind("}")+1]
        ai_data = json.loads(text)
        for i, s in enumerate(ai_data.get("sets", []), 1):
            s.setdefault("set_number", i)
        ai_data["source"] = "ai"
        print(f"[AI suggest-all-sets] exercise_id={exercise_id} num_sets={num_sets} ok")
        return jsonify(ai_data), 200

    except Exception as e:
        print(f"[AI suggest-all-sets] AI failed, rule-based fallback: {e}")
        return jsonify(rule_result), 200

"""
English Summary:
This large module connects the PeakForm application to Google's Gemini AI service. 
It facilitates dynamic conversation with a virtual AI Coach, analyzes workout history to 
suggest progressive overload per exercise (for both single next-sets and full workout predictions), 
and translates AI responses into structured JSON templates that can be saved directly to the database.

סיכום בעברית:
קובץ זה מחבר בין האפליקציה שלנו לבין המוח החכם של גוגל (Gemini AI). הוא מאפשר למתאמן להתכתב עם
מאמן כושר וירטואלי שמכיר את ההיסטוריה שלו. הקובץ יודע לקחת את ההיסטוריה של המתאמן (משקלים וחזרות),
לשלוח אותה לבינה המלאכותית ולהחזיר המלצות מדויקות - כמה משקל להרים בסט הבא, או אפילו לבנות 
תוכנית אימון שלמה לחודש הקרוב ולשמור אותה אוטומטית במסד הנתונים!
"""
