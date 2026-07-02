from flask import Blueprint, jsonify
from flask_login import login_required
from src.web.services.data_service import load_class, load_questions, invalidate_data_cache

data_bp = Blueprint('data', __name__)

@data_bp.route("/api/class", methods=["GET"])
def api_class():
    try:
        return jsonify(load_class())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_bp.route("/api/questions", methods=["GET"])
def api_questions():
    try:
        return jsonify(load_questions())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_bp.route("/api/reload_data", methods=["POST"])
@login_required
def api_reload_data():
    invalidate_data_cache()
    try:
        load_class()
        load_questions()
        return jsonify({"ok": True, "message": "Data reloaded successfully"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
