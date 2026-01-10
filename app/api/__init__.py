from flask import Blueprint

api_bp = Blueprint("api", __name__)

@api_bp.get("/health")
def health():
    return {"status": "ok"}

from .auth import auth_bp  # noqa: E402
api_bp.register_blueprint(auth_bp)

from .student import students_bp  # noqa: E402
api_bp.register_blueprint(students_bp)

from .interests import interests_bp  # noqa: E402
api_bp.register_blueprint(interests_bp)

from .skills import skills_bp  # noqa: E402
api_bp.register_blueprint(skills_bp)

from .roles import roles_bp  # noqa: E402
api_bp.register_blueprint(roles_bp)

from .admin import admins_bp  # noqa: E402
api_bp.register_blueprint(admins_bp)

from .forum import forum_bp  # noqa: E402
api_bp.register_blueprint(forum_bp)