import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.web.app import create_app
from src.config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG

app = create_app()

if __name__ == "__main__":
    print("=" * 58)
    print("  Plickers Classroom API Server")
    print(f"  API Endpoint      : http://localhost:{FLASK_PORT}/api")
    print(f"  Video Stream      : http://localhost:{FLASK_PORT}/video_feed")
    print("=" * 58)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)
