from flask import Flask
from dotenv import load_dotenv
import os
from . import models

from .extensions import db, migrate, jwt, cors
from .scheduler import init_scheduler

def create_app():
    load_dotenv()

    app = Flask(__name__)

    # ЖЕЛЕЗНЫЙ фикс:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["UPLOAD_FOLDER"] = os.getenv(
        "UPLOAD_FOLDER",
        os.path.abspath(os.path.join(app.root_path, "..", "uploads")),
    )
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "20"))
    app.config["MAX_CONTENT_LENGTH"] = max(1, max_upload_mb) * 1024 * 1024

    cors.init_app(
        app,
        resources={
            r"/*": {
                "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # Планировщик фоновых задач (начисление баллов за оценки и финализация месяцев)
    init_scheduler(app)

    return app
