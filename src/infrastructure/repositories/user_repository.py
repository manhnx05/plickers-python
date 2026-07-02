from src.domain.models import User, db
from typing import Optional

class UserRepository:
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        return db.session.get(User, user_id)

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        return User.query.filter_by(email=email).first()

    @staticmethod
    def save(user: User) -> None:
        db.session.add(user)
        db.session.commit()
