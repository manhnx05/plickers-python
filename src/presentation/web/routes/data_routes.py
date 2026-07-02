from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from src.application.services.data_service import DataService

data_bp = Blueprint('data', __name__)

@data_bp.route("/api/class", methods=["GET"])
@login_required
def api_class():
    try:
        class_data = DataService.get_class_data(current_user.id)
        return jsonify(class_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_bp.route("/api/questions", methods=["GET"])
@login_required
def api_questions():
    try:
        questions = DataService.get_questions_data(current_user.id)
        return jsonify(questions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_bp.route("/api/reload_data", methods=["POST"])
@login_required
def api_reload_data():
    # Cache invalidation is no longer needed since we query the DB
    return jsonify({"ok": True, "message": "Data reloaded successfully"})
