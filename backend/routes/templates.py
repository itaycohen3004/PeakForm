"""
Template routes — named workout templates and weekly scheduling.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.template import (
    create_template, get_templates, get_template, get_full_template,
    update_template, delete_template,
    add_exercise_to_template, remove_exercise_from_template,
    add_template_set, delete_template_set,
    set_schedule, clear_schedule, get_schedule,
)

templates_bp = Blueprint("templates", __name__, url_prefix="/api/templates")


@templates_bp.route("", methods=["GET"])
@require_auth
def list_templates():
    rows = get_templates(g.user_id)
    return jsonify([dict(r) for r in rows]), 200


@templates_bp.route("", methods=["POST"])
@require_auth
def create():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    tpl_id = create_template(g.user_id, name, data.get("training_type"), data.get("notes"))
    
    # Process AI-generated or custom exercises array
    exercises = data.get("exercises", [])
    if exercises:
        from backend.models.db import get_db
        db = get_db()
        for idx, ex_data in enumerate(exercises):
            ex_name = ex_data.get("name")
            if not ex_name: continue
            
            # Find the exercise ID by name - MUST be approved OR created by this user
            ex_row = db.execute("""
                SELECT id FROM exercises 
                WHERE name = ? COLLATE NOCASE 
                AND (status = 'approved' OR (status IS NULL AND is_custom = 0) OR created_by = ?)
            """, (ex_name, g.user_id)).fetchone()
            if ex_row:
                ex_id = ex_row["id"]
                add_exercise_to_template(
                    tpl_id, ex_id, 
                    position=idx,
                    default_sets=ex_data.get("default_sets", 3),
                    notes=ex_data.get("notes", "")
                )

    return jsonify({"id": tpl_id, "message": "Template created."}), 201


@templates_bp.route("/<int:tpl_id>", methods=["GET"])
@require_auth
def detail(tpl_id):
    tpl = get_template(tpl_id)
    if not tpl or tpl["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    return jsonify(get_full_template(tpl_id)), 200


@templates_bp.route("/<int:tpl_id>", methods=["PATCH"])
@require_auth
def update(tpl_id):
    tpl = get_template(tpl_id)
    if not tpl or tpl["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    update_template(tpl_id, data)
    return jsonify({"message": "Template updated."}), 200


@templates_bp.route("/<int:tpl_id>", methods=["DELETE"])
@require_auth
def remove(tpl_id):
    tpl = get_template(tpl_id)
    if not tpl or tpl["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    delete_template(tpl_id)
    return jsonify({"message": "Template deleted."}), 200


@templates_bp.route("/<int:tpl_id>/exercises", methods=["POST"])
@require_auth
def add_exercise(tpl_id):
    tpl = get_template(tpl_id)
    if not tpl or tpl["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    if not data.get("exercise_id"):
        return jsonify({"error": "exercise_id required"}), 400
    te_id = add_exercise_to_template(tpl_id, data["exercise_id"],
                                      data.get("position", 0), data.get("default_sets", 3), data.get("notes", ""))
    return jsonify({"id": te_id, "message": "Exercise added to template."}), 201


@templates_bp.route("/exercises/<int:te_id>", methods=["DELETE"])
@require_auth
def remove_exercise(te_id):
    remove_exercise_from_template(te_id)
    return jsonify({"message": "Removed from template."}), 200


@templates_bp.route("/exercises/<int:te_id>/sets", methods=["POST"])
@require_auth
def add_set(te_id):
    data = request.get_json(silent=True) or {}
    s_id = add_template_set(te_id, data)
    return jsonify({"id": s_id, "message": "Target set added."}), 201


@templates_bp.route("/exercises/sets/<int:set_id>", methods=["DELETE"])
@require_auth
def remove_set(set_id):
    delete_template_set(set_id)
    return jsonify({"message": "Set removed."}), 200


# ── Weekly Schedule ──

@templates_bp.route("/schedule", methods=["GET"])
@require_auth
def get_sched():
    rows = get_schedule(g.user_id)
    return jsonify([dict(r) for r in rows]), 200


@templates_bp.route("/schedule", methods=["POST"])
@require_auth
def set_sched():
    data = request.get_json(silent=True) or {}
    weekday     = data.get("weekday")
    template_id = data.get("template_id")
    if weekday is None or template_id is None:
        return jsonify({"error": "weekday and template_id required"}), 400
    if int(weekday) not in range(7):
        return jsonify({"error": "weekday must be 0–6 (Mon–Sun)"}), 400
    set_schedule(g.user_id, int(weekday), int(template_id))
    return jsonify({"message": "Schedule set."}), 200


@templates_bp.route("/schedule/<int:weekday>", methods=["DELETE"])
@require_auth
def clear_sched(weekday):
    clear_schedule(g.user_id, weekday)
    return jsonify({"message": "Schedule cleared."}), 200
