from src.domain.models import Student, db
from typing import List, Optional

class StudentRepository:
    @staticmethod
    def get_by_class(class_id: int) -> List[Student]:
        return Student.query.filter_by(class_id=class_id).all()

    @staticmethod
    def get_by_card_number(card_number: int) -> Optional[Student]:
        return Student.query.filter_by(card_number=card_number).first()
        
    @staticmethod
    def save(student: Student) -> None:
        db.session.add(student)
        db.session.commit()
