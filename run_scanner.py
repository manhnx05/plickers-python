"""
Entry point — Chạy Standalone Camera Scanner từ thư mục gốc.
Usage: python run_scanner.py
"""
import sys
import os

# Đảm bảo project root trong sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import main

if __name__ == '__main__':
    main()
