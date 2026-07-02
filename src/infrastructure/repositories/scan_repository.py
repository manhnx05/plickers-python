from src.domain.models import ScanSession, ScanResult, db
from typing import List, Optional

class ScanRepository:
    @staticmethod
    def save_session(session: ScanSession) -> None:
        db.session.add(session)
        db.session.commit()
        
    @staticmethod
    def save_results(results: List[ScanResult]) -> None:
        for result in results:
            db.session.add(result)
        db.session.commit()
