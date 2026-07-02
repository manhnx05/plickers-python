"""
Database helper for Plickers system using SQLAlchemy.
Handles database initialization and operations.
"""

import os
import sys
from typing import List, Tuple, Optional
import numpy as np
from datetime import datetime, timedelta, timezone
import secrets

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import DATABASE_DIR, DATABASE_URL
from src.domain.models import db, Card, User, Class, Student, Question, ScanSession, ScanResult, PasswordResetToken


def init_db(app) -> None:
    """
    Initialize SQLAlchemy database and create all tables.
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    # Ensure we use PostgreSQL URL
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Only initialize if not already initialized
    if 'sqlalchemy' not in app.extensions:
        db.init_app(app)
    
    with app.app_context():
        db.create_all()


def save_card(card_id: str, card_number: int, option: str, matrix: np.ndarray) -> None:
    """
    Save a single card to the database.
    """
    matrix_blob = matrix.tobytes()
    
    existing_card = Card.query.filter_by(card_id=card_id).first()
    if existing_card:
        existing_card.card_number = card_number
        existing_card.option = option
        existing_card.matrix = matrix_blob
    else:
        new_card = Card(
            card_id=card_id,
            card_number=card_number,
            option=option,
            matrix=matrix_blob
        )
        db.session.add(new_card)
    
    db.session.commit()


def load_all_cards() -> Tuple[List[np.ndarray], List[str]]:
    """
    Load all cards from the database.
    Returns (card_data, card_list) where card_data is list of matrices and card_list is list of card IDs.
    """
    cards = Card.query.order_by(Card.id).all()
    card_data = []
    card_list = []
    
    for card in cards:
        matrix = np.frombuffer(card.matrix, dtype=np.float64).reshape(5, 5)
        card_data.append(matrix)
        card_list.append(card.card_id)
    
    return card_data, card_list


def clear_cards() -> None:
    """
    Clear all cards from the database.
    """
    Card.query.delete()
    db.session.commit()


def create_password_reset_token(user_id: int) -> str:
    """
    Create a password reset token for a user.
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    
    reset_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.session.add(reset_token)
    db.session.commit()
    
    return token


def get_user_by_token(token: str) -> Optional[User]:
    """
    Get a user by a valid password reset token.
    """
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if reset_token and reset_token.expires_at > datetime.now(timezone.utc):
        return User.query.get(reset_token.user_id)
    return None


def mark_token_as_used(token: str) -> None:
    """
    Mark a password reset token as used.
    """
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    if reset_token:
        reset_token.used = True
        db.session.commit()


if __name__ == "__main__":
    from src.web.app_web import app
    print("Initializing SQLAlchemy database...")
    init_db(app)
    print("Database initialized successfully!")
