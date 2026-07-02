from src.domain.models import Question, db
from typing import List, Optional

class QuestionRepository:
    @staticmethod
    def get_by_teacher(teacher_id: int) -> List[Question]:
        return Question.query.filter_by(teacher_id=teacher_id).all()

    @staticmethod
    def get_by_id(question_id: int) -> Optional[Question]:
        return db.session.get(Question, question_id)
        
    @staticmethod
    def save(question: Question) -> None:
        db.session.add(question)
        db.session.commit()
