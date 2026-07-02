from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.web.extensions import bcrypt
from src.domain.models import User
from typing import Optional, Tuple

class AuthService:
    @staticmethod
    def login(email: str, password: str) -> Tuple[bool, Optional[User], str]:
        user = UserRepository.get_by_email(email)
        if user and bcrypt.check_password_hash(user.password_hash, password):
            return True, user, "Login successful"
        return False, None, "Invalid email or password"

    @staticmethod
    def register(name: str, email: str, password: str) -> Tuple[bool, str]:
        existing_user = UserRepository.get_by_email(email)
        if existing_user:
            return False, "Email already registered"
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            name=name,
            email=email,
            password_hash=hashed_password,
            role='teacher'
        )
        UserRepository.save(new_user)
        return True, "Registration successful"
