from src.domain.models import Class, db
from typing import List, Optional

class ClassRepository:
    @staticmethod
    def get_all() -> List[Class]:
        return Class.query.all()

    @staticmethod
    def get_by_id(class_id: int) -> Optional[Class]:
        return db.session.get(Class, class_id)
        
    @staticmethod
    def get_by_teacher(teacher_id: int) -> List[Class]:
        return Class.query.filter_by(teacher_id=teacher_id).all()

    @staticmethod
    def save(cls: Class) -> None:
        db.session.add(cls)
        db.session.commit()
