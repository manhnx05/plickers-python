import os
from flask import Flask
from src.config import FLASK_SECRET_KEY
from src.infrastructure.database import init_db
from src.presentation.web.extensions import bcrypt, login_manager

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = FLASK_SECRET_KEY
    
    # Extensions
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    
    # Initialize Database
    with app.app_context():
        init_db(app)
        
    # Register Blueprints
    from src.presentation.web.routes.auth_routes import auth_bp
    from src.presentation.web.routes.scanner_routes import scanner_bp
    from src.presentation.web.routes.data_routes import data_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(data_bp)
    
    return app
