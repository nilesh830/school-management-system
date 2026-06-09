import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger
from config import config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
limiter = Limiter(key_func=get_remote_address, default_limits=["500/day", "100/hour"])

_SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/",
}


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure school DBs directory exists before any DB operations
    os.makedirs(app.config['SCHOOLS_DB_DIR'], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    limiter.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'])

    _init_swagger(app)
    _register_jwt_handlers(jwt)

    @app.route('/api/v1/health')
    def health():
        return jsonify({"success": True, "message": "SMS API is running", "version": "1.0.0"}), 200

    from app.routes.auth import auth_bp
    from app.routes.users import users_bp
    from app.routes.students import students_bp
    from app.routes.teachers import teachers_bp
    from app.routes.parent_portal import parent_portal_bp, leave_bp, notifications_bp
    from app.routes.superadmin_auth import superadmin_auth_bp
    from app.routes.superadmin_schools import superadmin_schools_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(parent_portal_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(superadmin_auth_bp)
    app.register_blueprint(superadmin_schools_bp)

    # Ensure master models are imported so SQLAlchemy includes them in metadata,
    # then create their tables (no Flask-Migrate for the simple master schema).
    from app.models.master.school import School  # noqa: F401
    from app.models.master.super_admin import SuperAdmin  # noqa: F401
    from app.models.master.super_admin_revoked_token import SuperAdminRevokedToken  # noqa: F401
    with app.app_context():
        db.create_all(bind_key=['master'])

    return app


def _init_swagger(app):
    swagger_yaml = os.path.join(os.path.dirname(__file__), 'swagger.yaml')
    Swagger(app, config=_SWAGGER_CONFIG, template_file=swagger_yaml)


def _register_jwt_handlers(jwt_manager):

    @jwt_manager.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from app.models.revoked_token import RevokedToken
        from app.models.master.super_admin_revoked_token import SuperAdminRevokedToken
        jti = jwt_payload['jti']
        # Fast path: super admin tokens are stored in the master DB blocklist
        if jwt_payload.get('role') == 'super_admin':
            return SuperAdminRevokedToken.is_jti_blocklisted(jti)
        return RevokedToken.is_jti_blocklisted(jti)

    @jwt_manager.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "data": None, "message": "Token has expired", "errors": None}), 401

    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"success": False, "data": None, "message": "Invalid token", "errors": None}), 401

    @jwt_manager.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"success": False, "data": None, "message": "Authorization token required", "errors": None}), 401

    @jwt_manager.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "data": None, "message": "Token has been revoked. Please log in again.", "errors": None}), 401
