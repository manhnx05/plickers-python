"""
Plickers Web App — Flask server
Teacher dashboard + Student display with real-time card scanning.
"""
import sys
import os
import json
import time
import csv
import threading
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, render_template, Response, jsonify, request, stream_with_context

# ─── Path setup ──────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
from core.detector import PlickersDetector

# ─── Flask init ───────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'plickers-secret'

DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

# ─── Detector ─────────────────────────────────────────────────────────────────
detector = PlickersDetector()

# ─── Shared state (thread-safe) ───────────────────────────────────────────────
state_lock = threading.Lock()
state = {
    'scanning': False,
    'question': None,    # current question dict
    'results': {},       # {card_no_int: 'A'|'B'|'C'|'D'}
    'revealed': False,
    'session_ts': None,
}

frame_lock = threading.Lock()
output_frame = None      # latest JPEG bytes


# ─── Data helpers ─────────────────────────────────────────────────────────────
def load_class():
    path = os.path.join(DATA_DIR, 'class.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def load_questions():
    path = os.path.join(DATA_DIR, 'questions.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def get_student_name(card_no: int) -> str:
    try:
        cls = load_class()
        for s in cls['students']:
            if s['card_no'] == card_no:
                return s['name']
    except Exception:
        pass
    return f'HS #{card_no:02d}'


# ─── Camera / Detector thread ─────────────────────────────────────────────────
def camera_worker():
    global output_frame
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
    cap.set(cv2.CAP_PROP_FPS, 30)

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        display = frame.copy()

        with state_lock:
            scanning = state['scanning']

        if scanning:
            found = detector.process_image(frame)
            for card_id, cnt in found:
                parts = str(card_id).split('-')
                try:
                    card_no = int(parts[0])
                    answer  = parts[1] if len(parts) > 1 else '?'
                except Exception:
                    continue

                # Store result (first scan wins — no overwrite)
                with state_lock:
                    if card_no not in state['results']:
                        state['results'][card_no] = answer

                # Draw smooth bounding box
                try:
                    rect = cv2.minAreaRect(cnt)
                    box  = np.int32(cv2.boxPoints(rect))
                    cv2.drawContours(display, [box], 0, (0, 255, 100), 2)
                except Exception:
                    pass

                # Centroid answer stamp
                try:
                    M = cv2.moments(cnt)
                    if M['m00'] != 0:
                        cx = int(M['m10'] / M['m00'])
                        cy = int(M['m01'] / M['m00'])
                        cv2.putText(display, answer, (cx - 15, cy + 15),
                                    cv2.FONT_HERSHEY_DUPLEX, 1.5, (0, 0, 255), 3)
                except Exception:
                    pass

                # Student name tag
                try:
                    x, y, w, h = cv2.boundingRect(cnt)
                    name = get_student_name(card_no)
                    cv2.putText(display, name, (x, max(y - 8, 20)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)
                except Exception:
                    pass

        # HUD status bar
        with state_lock:
            result_count = len(state['results'])
            scan = state['scanning']

        cv2.rectangle(display, (0, 0), (220, 38), (0, 0, 0), -1)
        status_txt = f'DANG QUET ({result_count} the)' if scan else 'TAM DUNG'
        color = (0, 220, 80) if scan else (60, 140, 255)
        cv2.putText(display, status_txt, (8, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        _, buf = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 75])
        with frame_lock:
            output_frame = buf.tobytes()

        time.sleep(0.033)

    cap.release()


# Start background camera thread
threading.Thread(target=camera_worker, daemon=True).start()


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('teacher.html')


@app.route('/display')
def display():
    return render_template('display.html')


@app.route('/video_feed')
def video_feed():
    def gen():
        while True:
            with frame_lock:
                frame = output_frame
            if frame:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/events')
def api_events():
    """SSE stream — push state snapshot every 400ms."""
    def stream():
        while True:
            with state_lock:
                data = json.dumps({
                    'scanning':  state['scanning'],
                    'question':  state['question'],
                    'results':   state['results'],
                    'revealed':  state['revealed'],
                })
            yield f'data: {data}\n\n'
            time.sleep(0.4)
    return Response(
        stream_with_context(stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/state')
def api_state():
    with state_lock:
        return jsonify({
            'scanning': state['scanning'],
            'question': state['question'],
            'results':  state['results'],
            'revealed': state['revealed'],
        })


@app.route('/api/class')
def api_class():
    try:
        return jsonify(load_class())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/questions')
def api_questions():
    try:
        return jsonify(load_questions())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start', methods=['POST'])
def api_start():
    data = request.json or {}
    with state_lock:
        state['scanning']   = True
        state['question']   = data.get('question')
        state['results']    = {}
        state['revealed']   = False
        state['session_ts'] = datetime.now().isoformat()
    return jsonify({'ok': True})


@app.route('/api/stop', methods=['POST'])
def api_stop():
    with state_lock:
        state['scanning'] = False
    return jsonify({'ok': True})


@app.route('/api/reveal', methods=['POST'])
def api_reveal():
    with state_lock:
        state['revealed']  = True
        state['scanning']  = False
    _save_results()
    return jsonify({'ok': True})


@app.route('/api/reset', methods=['POST'])
def api_reset():
    with state_lock:
        state['scanning']  = False
        state['question']  = None
        state['results']   = {}
        state['revealed']  = False
    return jsonify({'ok': True})


def _save_results():
    try:
        with state_lock:
            results  = dict(state['results'])
            question = state['question']

        cls = load_class()
        out_dir = os.path.join(DATA_DIR, 'output')
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(out_dir, f'session_{ts}.csv')

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['So the', 'Ten hoc sinh', 'Cau hoi', 'Dap an', 'Dap an dung', 'Ket qua'])
            for s in cls['students']:
                cn  = s['card_no']
                ans = results.get(cn, '-')
                correct = question['correct'] if question else '-'
                result  = 'Dung' if ans == correct else ('Sai' if ans != '-' else 'Chua tra loi')
                q_text  = question['text'] if question else ''
                w.writerow([cn, s['name'], q_text, ans, correct, result])

        print(f'[OK] Saved session: {filename}')
    except Exception as e:
        print(f'[ERR] Save failed: {e}')


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('=' * 55)
    print('  Plickers Classroom Web App')
    print('  Teacher Dashboard : http://localhost:5000/')
    print('  Student Display   : http://localhost:5000/display')
    print('=' * 55)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
