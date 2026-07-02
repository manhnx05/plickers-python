from src.infrastructure.repositories.class_repository import ClassRepository
from src.infrastructure.repositories.question_repository import QuestionRepository
from src.infrastructure.repositories.student_repository import StudentRepository
from typing import Dict, List, Any

class DataService:
    @staticmethod
    def get_class_data(teacher_id: int) -> Dict[str, Any]:
        classes = ClassRepository.get_by_teacher(teacher_id)
        if not classes:
            return {"class_name": "No Class Found", "students": []}
            
        cls = classes[0]  # Just return the first class for now
        students = StudentRepository.get_by_class(cls.id)
        return {
            "class_name": cls.name,
            "students": [{"card_no": s.card_number, "name": s.name} for s in students]
        }

    @staticmethod
    def get_questions_data(teacher_id: int) -> List[Dict[str, Any]]:
        questions = QuestionRepository.get_by_teacher(teacher_id)
        return [{
            "id": q.id,
            "text": q.text,
            "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
            "correct": q.correct_option
        } for q in questions]
