"""Script to append suggest-all-sets endpoint to ai.py"""
import os

endpoint = r'''

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
'''

ai_py_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'routes', 'ai.py')
ai_py_path = os.path.normpath(ai_py_path)

with open(ai_py_path, 'a', encoding='utf-8') as f:
    f.write(endpoint)

print(f"Appended suggest-all-sets to {ai_py_path}")

"""
English Summary:
A utility script used during development to patch the 'ai.py' route file with a new, optimized 
endpoint ('/suggest-all-sets'). This endpoint was designed to reduce API latency by generating 
recommendations for an entire multi-set exercise in a single Gemini API call rather than sequentially.

סיכום בעברית:
זהו סקריפט (קובץ עזר) של מתכנתים שנועד להוסיף באופן אוטומטי פונקציה חדשה לשרת. 
הפונקציה הזו מייעלת מאוד את העבודה מול הבינה המלאכותית: במקום לבקש ממנה ייעוץ 
לכל סט של תרגיל בנפרד (מה שלוקח הרבה זמן ותוקע את האפליקציה), הפונקציה מבקשת
ממנה לתכנן את כל הסטים של התרגיל מראש, בשאילתה אחת בודדת!
"""
