from datetime import datetime, timezone
from src.infrastructure.repositories.scan_repository import ScanRepository
from src.infrastructure.repositories.student_repository import StudentRepository
from src.infrastructure.repositories.question_repository import QuestionRepository
from src.domain.models import ScanSession, ScanResult
from typing import Dict, Any

class ScannerService:
    @staticmethod
    def save_session(teacher_id: int, question_data: Dict[str, Any], results: Dict[str, str], started_at_str: str) -> None:
        try:
            started_at = datetime.fromisoformat(started_at_str)
        except (ValueError, TypeError):
            started_at = datetime.now(timezone.utc)
            
        question_id = question_data.get("id") if question_data else None
        
        session = ScanSession(
            teacher_id=teacher_id,
            question_id=question_id,
            started_at=started_at,
            ended_at=datetime.now(timezone.utc)
        )
        ScanRepository.save_session(session)
        
        question = QuestionRepository.get_by_id(question_id) if question_id else None
        correct_ans = question.correct_option if question else None
        
        scan_results = []
        for card_no_str, answer in results.items():
            card_no = int(card_no_str)
            student = StudentRepository.get_by_card_number(card_no)
            if student:
                is_correct = None
                if correct_ans:
                    is_correct = (answer == correct_ans)
                    
                result = ScanResult(
                    session_id=session.id,
                    student_id=student.id,
                    answer=answer,
                    is_correct=is_correct
                )
                scan_results.append(result)
                
        ScanRepository.save_results(scan_results)
