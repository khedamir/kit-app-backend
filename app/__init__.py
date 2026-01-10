from flask import Flask
from dotenv import load_dotenv
import os
from . import models

from .extensions import db, migrate, jwt, cors

def create_app():
    load_dotenv()

    app = Flask(__name__)

    # ЖЕЛЕЗНЫЙ фикс:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")

    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from .api import api_bp
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    return app
