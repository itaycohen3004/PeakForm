"""
Workout routes — sessions, exercises, sets CRUD + progression charts.
"""
from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.models.workout import (
    create_workout, get_workout, get_workouts, get_full_workout,
    update_workout, delete_workout,
    add_exercise_to_workout, get_workout_exercises, remove_exercise_from_workout,
    add_set, update_set, delete_set, get_sets_for_exercise,
    get_sets_for_exercise, get_weekly_volume, get_exercise_progression, 
    clone_from_template, get_workouts_for_month, finish_workout,
)
from backend.models.audit import log_action

workouts_bp = Blueprint("workouts", __name__, url_prefix="/api/workouts")


# ── Sessions ──

@workouts_bp.route("", methods=["GET"])
@require_auth
def list_workouts():
    limit  = int(request.args.get("limit", 30))
    offset = int(request.args.get("offset", 0))
    rows   = get_workouts(g.user_id, limit, offset)
    return jsonify([dict(r) for r in rows]), 200


@workouts_bp.route("", methods=["POST"])
@require_auth
def create():
    data = request.get_json(silent=True) or {}
    workout_id = create_workout(g.user_id, data)
    log_action(g.user_id, "workout_created", f"id={workout_id}", request.remote_addr)
    return jsonify({"id": workout_id, "message": "Workout created."}), 201


@workouts_bp.route("/from-template", methods=["POST"])
@require_auth
def from_template():
    data        = request.get_json(silent=True) or {}
    template_id = data.get("template_id")
    date        = data.get("workout_date")
    name        = data.get("name")
    if not template_id:
        return jsonify({"error": "template_id required"}), 400
        
    try:
        template_id = int(template_id)
    except ValueError:
        return jsonify({"error": "template_id must be an integer"}), 400
        
    workout_id = clone_from_template(g.user_id, template_id, date, name)
    if not workout_id:
        return jsonify({"error": "Template not found or access denied"}), 404
    return jsonify({"id": workout_id, "message": "Workout cloned from template."}), 201


@workouts_bp.route("/calendar", methods=["GET"])
@require_auth
def calendar():
    import datetime
    year  = int(request.args.get("year",  datetime.date.today().year))
    month = int(request.args.get("month", datetime.date.today().month))
    rows  = get_workouts_for_month(g.user_id, year, month)
    return jsonify([dict(r) for r in rows]), 200


@workouts_bp.route("/weekly-volume", methods=["GET"])
@require_auth
def weekly_volume():
    weeks = int(request.args.get("weeks", 8))
    rows  = get_weekly_volume(g.user_id, weeks)
    return jsonify([dict(r) for r in reversed(rows)]), 200


@workouts_bp.route("/<int:workout_id>", methods=["GET"])
@require_auth
def detail(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    full = get_full_workout(workout_id)
    return jsonify(full), 200


@workouts_bp.route("/<int:workout_id>", methods=["PATCH"])
@require_auth
def update(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    update_workout(workout_id, data)
    return jsonify({"message": "Workout updated."}), 200
 
 
@workouts_bp.route("/<int:workout_id>/finish", methods=["POST"])
@require_auth
def finish(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    duration = data.get("duration_minutes")
    notes = data.get("notes")
    
    try:
        result = finish_workout(workout_id, duration, notes)
        if result:
            log_action(g.user_id, "workout_finished", f"id={workout_id}", request.remote_addr)
            return jsonify({"message": "Workout finished and metrics calculated."}), 200
        return jsonify({"error": "Workout not found in database"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to finish workout: {str(e)}"}), 500


@workouts_bp.route("/<int:workout_id>", methods=["DELETE"])
@require_auth
def remove(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    delete_workout(workout_id)
    return jsonify({"message": "Workout deleted."}), 200


# ── Exercises within a workout ──

@workouts_bp.route("/<int:workout_id>/exercises", methods=["POST"])
@require_auth
def add_exercise(workout_id):
    w = get_workout(workout_id)
    if not w or w["user_id"] != g.user_id:
        return jsonify({"error": "Not found"}), 404
    data = request.get_json(silent=True) or {}
    exercise_id = data.get("exercise_id")
    if not exercise_id:
        return jsonify({"error": "exercise_id required"}), 400
    we_id = add_exercise_to_workout(workout_id, exercise_id,
                                     data.get("position", 0), data.get("notes", ""))
    return jsonify({"id": we_id, "message": "Exercise added."}), 201


@workouts_bp.route("/exercises/<int:we_id>", methods=["DELETE"])
@require_auth
def remove_exercise(we_id):
    remove_exercise_from_workout(we_id)
    return jsonify({"message": "Exercise removed."}), 200


# ── Sets ──

@workouts_bp.route("/exercises/<int:we_id>/sets", methods=["POST"])
@require_auth
def add_set_route(we_id):
    data = request.get_json(silent=True) or {}
    set_id = add_set(we_id, data)
    return jsonify({"id": set_id, "message": "Set added."}), 201


@workouts_bp.route("/sets/<int:set_id>", methods=["PATCH"])
@require_auth
def update_set_route(set_id):
    data = request.get_json(silent=True) or {}
    update_set(set_id, data)
    return jsonify({"message": "Set updated."}), 200


@workouts_bp.route("/sets/<int:set_id>", methods=["DELETE"])
@require_auth
def delete_set_route(set_id):
    delete_set(set_id)
    return jsonify({"message": "Set deleted."}), 200


# ── Progression Charts ──

@workouts_bp.route("/progression/<int:exercise_id>", methods=["GET"])
@require_auth
def progression(exercise_id):
    limit = int(request.args.get("limit", 30))
    rows  = get_exercise_progression(g.user_id, exercise_id, limit)
    return jsonify([dict(r) for r in reversed(rows)]), 200
