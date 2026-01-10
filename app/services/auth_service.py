from ..models.user import User
from ..extensions import db
from ..utils.security import verify_password

def authenticate(email: str, password: str) -> User | None:
    user = db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar_one_or_none()

    if not user or not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user
