"""
Configuration constants for Plickers system.
Centralized configuration management for easy maintenance.
"""
import os

# ─── Project Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DATABASE_DIR = os.path.join(DATA_DIR, 'database')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
SAMPLES_DIR = os.path.join(DATA_DIR, 'samples')

# ─── Camera Settings ──────────────────────────────────────────────────────────
CAM_WIDTH = 800
CAM_HEIGHT = 600
CAM_FPS = 30
CAM_BACKEND = 'CAP_DSHOW'  # Windows DirectShow

# ─── Detection Settings ───────────────────────────────────────────────────────
GRID_SIZE = 5
CELL_INSET_RATIO = 0.15
BRIGHTNESS_THRESHOLD = 120
MIN_CONTOUR_POINTS = 50
MIN_APPROX_POINTS = 4
MIN_CARD_SIZE = 10
MIN_AVG_BRIGHTNESS = 100
MAX_AVG_BRIGHTNESS = 230

# Adaptive detection parameters
BLUR_SETTINGS = [3, 5, 7]
CANNY_SETTINGS = [(30, 150), (10, 100), (50, 200)]

# ─── Scanner Settings ─────────────────────────────────────────────────────────
COOLDOWN_TIME = 5.0  # seconds - prevent duplicate scans
HUD_MAX_ROWS = 10    # maximum cards displayed in HUD

# ─── Web App Settings ─────────────────────────────────────────────────────────
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = False
FLASK_SECRET_KEY = 'plickers-secret'

SSE_INTERVAL = 0.4   # seconds - Server-Sent Events update interval
FRAME_QUALITY = 75   # JPEG quality for video stream

# ─── File Paths ───────────────────────────────────────────────────────────────
CLASS_JSON = os.path.join(DATA_DIR, 'class.json')
QUESTIONS_JSON = os.path.join(DATA_DIR, 'questions.json')
CARD_DATA = os.path.join(DATABASE_DIR, 'card.data')
CARD_LIST = os.path.join(DATABASE_DIR, 'card.list')
SCANNER_CSV = os.path.join(OUTPUT_DIR, 'ket_qua.csv')

# ─── Logging Settings ─────────────────────────────────────────────────────────
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
