"""
SQLite database helper for Plickers system.
Handles database connection, schema creation, and data operations.
"""

import sqlite3
import os
import sys
import json
from typing import List, Tuple, Optional
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.config import SQLITE_DB, DATABASE_DIR


def init_db() -> None:
    """
    Initialize SQLite database and create tables if they don't exist.
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # Create cards table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL UNIQUE,  -- e.g., "001-A"
            card_number INTEGER NOT NULL,  -- e.g., 1
            option TEXT NOT NULL,  -- e.g., "A"
            matrix BLOB NOT NULL,  -- 5x5 matrix as binary
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create scan_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER,
            question_text TEXT,
            correct_answer TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create scan_results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            card_number INTEGER NOT NULL,
            student_name TEXT,
            answer TEXT NOT NULL,
            is_correct BOOLEAN,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES scan_sessions (id)
        )
    """)
    
    conn.commit()
    conn.close()


def save_card(card_id: str, card_number: int, option: str, matrix: np.ndarray) -> None:
    """
    Save a single card to the database.
    """
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    # Convert numpy matrix to binary
    matrix_blob = matrix.tobytes()
    
    cursor.execute("""
        INSERT OR REPLACE INTO cards (card_id, card_number, option, matrix)
        VALUES (?, ?, ?, ?)
    """, (card_id, card_number, option, matrix_blob))
    
    conn.commit()
    conn.close()


def load_all_cards() -> Tuple[List[np.ndarray], List[str]]:
    """
    Load all cards from the database.
    Returns (card_data, card_list) where card_data is list of matrices and card_list is list of card IDs.
    """
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT card_id, matrix FROM cards ORDER BY id")
    rows = cursor.fetchall()
    
    card_data = []
    card_list = []
    
    for card_id, matrix_blob in rows:
        # Convert binary back to numpy matrix (5x5, float)
        matrix = np.frombuffer(matrix_blob, dtype=np.float64).reshape(5, 5)
        card_data.append(matrix)
        card_list.append(card_id)
    
    conn.close()
    return card_data, card_list


def clear_cards() -> None:
    """
    Clear all cards from the database.
    """
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards")
    conn.commit()
    conn.close()


def create_scan_session(question_id: Optional[int] = None, 
                        question_text: Optional[str] = None, 
                        correct_answer: Optional[str] = None) -> int:
    """
    Create a new scan session and return its ID.
    """
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO scan_sessions (question_id, question_text, correct_answer)
        VALUES (?, ?, ?)
    """, (question_id, question_text, correct_answer))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_scan_session(session_id: int) -> None:
    """
    Mark a scan session as ended.
    """
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE scan_sessions
        SET ended_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (session_id,))
    
    conn.commit()
    conn.close()


def save_scan_result(session_id: int, card_number: int, student_name: Optional[str], 
                     answer: str, is_correct: Optional[bool] = None) -> None:
    """
    Save a single scan result to the database.
    """
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO scan_results (session_id, card_number, student_name, answer, is_correct)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, card_number, student_name, answer, is_correct))
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("Initializing SQLite database...")
    init_db()
    print(f"Database initialized at: {SQLITE_DB}")
