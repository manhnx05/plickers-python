"""
Entry point -- Run Plickers Web App from project root.
Usage: python run_web.py
"""

import sys
import os

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web.app_web import app

if __name__ == "__main__":
    print("=" * 58)
    print("  Plickers Classroom Web App")
    print("  Teacher Dashboard : http://localhost:5000/")
    print("  Student Display   : http://localhost:5000/display")
    print("  Camera starts lazily when first client connects.")
    print("=" * 58)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
