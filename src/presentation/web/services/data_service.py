import os
import json
import threading
from src.config import DATA_DIR

_class_data = None
_questions_data = None
_student_lookup = {}
_data_lock = threading.Lock()

def load_class() -> dict:
    global _class_data, _student_lookup
    if _class_data is None:
        with _data_lock:
            if _class_data is None:
                path = os.path.join(DATA_DIR, "class.json")
                with open(path, encoding="utf-8") as f:
                    _class_data = json.load(f)
                _student_lookup = {str(s["card_no"]): s["name"] for s in _class_data.get("students", [])}
    return _class_data

def load_questions() -> list:
    global _questions_data
    if _questions_data is None:
        with _data_lock:
            if _questions_data is None:
                path = os.path.join(DATA_DIR, "questions.json")
                with open(path, encoding="utf-8") as f:
                    _questions_data = json.load(f)
    return _questions_data

def get_student_name(card_no: int | str) -> str:
    try:
        load_class()
        name = _student_lookup.get(str(card_no))
        return name if name else f"HS #{int(card_no):02d}"
    except Exception:
        return f"HS #{card_no}"

def invalidate_data_cache() -> None:
    global _class_data, _questions_data, _student_lookup
    with _data_lock:
        _class_data = None
        _questions_data = None
        _student_lookup = {}
