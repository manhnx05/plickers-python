from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, login_required, current_user
from src.application.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return jsonify({"ok": True, "message": "Already logged in", "user": {"id": current_user.id, "name": current_user.name, "role": current_user.role}})
    
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"ok": False, "error": "Missing email or password"}), 400
        
    success, user, message = AuthService.login(email, password)
    if success and user:
        login_user(user)
        return jsonify({"ok": True, "user": {"id": user.id, "name": user.name, "role": user.role}})
    return jsonify({"ok": False, "error": message}), 401

@auth_bp.route("/register", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return jsonify({"ok": False, "error": "Already logged in"}), 400
    
    data = request.json or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not name or not email or not password:
        return jsonify({"ok": False, "error": "Missing required fields"}), 400
        
    success, message = AuthService.register(name, email, password)
    if success:
        return jsonify({"ok": True, "message": message})
    return jsonify({"ok": False, "error": message}), 400

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"ok": True})

@auth_bp.route("/api/me", methods=["GET"])
def api_me():
    if current_user.is_authenticated:
        return jsonify({"ok": True, "user": {"id": current_user.id, "name": current_user.name, "email": current_user.email, "role": current_user.role}})
    return jsonify({"ok": False, "error": "Not authenticated"}), 401
