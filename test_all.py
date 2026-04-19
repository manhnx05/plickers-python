import sys
import os
import json
import threading
import importlib.metadata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"

results = []

def check(name, fn):
    try:
        out = fn()
        print(f"{PASS} {name}{(' — ' + str(out)) if out else ''}")
        results.append((True, name))
        return True
    except Exception as e:
        print(f"{FAIL} {name} — {e}")
        results.append((False, name, str(e)))
        return False


# ─── TEST 1: IMPORTS ──────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 1: MODULE IMPORTS")
print("="*60)

check("import cv2",          lambda: __import__('cv2').__version__)
check("import numpy",        lambda: __import__('numpy').__version__)
check("import flask",        lambda: importlib.metadata.version('flask'))
check("import scipy",        lambda: __import__('scipy').__version__)

check("src.core.detector",   lambda: __import__('src.core.detector', fromlist=['PlickersDetector']))
check("src.core.utils",      lambda: __import__('src.core.utils',    fromlist=['Math']))
check("src.web.app_web",     lambda: __import__('src.web.app_web',   fromlist=['app']))
check("src.app (scanner)",   lambda: __import__('src.app',           fromlist=['main']))
check("src.scripts.evaluate",lambda: __import__('src.scripts.evaluate', fromlist=['main']))
check("src.scripts.generate_db", lambda: __import__('src.scripts.generate_db', fromlist=['cv_card_read']))


# ─── TEST 2: DETECTOR & DATABASE ─────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 2: DETECTOR + DATABASE")
print("="*60)

from src.core.detector import PlickersDetector

detector = None
def init_detector():
    global detector
    detector = PlickersDetector()
    return f"{len(detector.card_data)} matrices, {len(detector.card_list)} IDs"

check("PlickersDetector init", init_detector)

def check_db_integrity():
    assert len(detector.card_data) == len(detector.card_list), "card_data / card_list length mismatch"
    assert len(detector.card_data) > 0, "Database is empty"
    return f"integrity OK — {len(detector.card_data)} entries"

if detector:
    check("Database integrity",  check_db_integrity)
    check("card_list sample IDs", lambda: str(detector.card_list[:4]))


# ─── TEST 3: DATA FILES ───────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 3: DATA FILES")
print("="*60)

from src.web.app_web import load_class, load_questions, get_student_name, invalidate_data_cache

invalidate_data_cache()

def test_class():
    cls = load_class()
    assert 'class_name' in cls
    assert 'students' in cls
    assert len(cls['students']) == 34
    return f"class='{cls['class_name']}', {len(cls['students'])} students"

def test_questions():
    qs = load_questions()
    assert len(qs) > 0
    for q in qs:
        assert 'id' in q and 'text' in q and 'options' in q and 'correct' in q
        assert q['correct'] in ('A','B','C','D')
    return f"{len(qs)} questions, all valid"

def test_student_lookup_hit():
    name = get_student_name(1)
    assert name != "HS #01", f"Expected real name, got: {name}"
    return f"card_no=1 → '{name}'"

def test_student_lookup_miss():
    name = get_student_name(99)
    assert "99" in name or "#" in name
    return f"card_no=99 (miss) → '{name}'"

check("class.json load",        test_class)
check("questions.json load",    test_questions)
check("Student lookup hit",     test_student_lookup_hit)
check("Student lookup miss",    test_student_lookup_miss)


# ─── TEST 4: STATE MANAGEMENT ─────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 4: STATE MANAGEMENT (Thread-safe)")
print("="*60)

from src.web.app_web import state, state_lock

def test_state_initial():
    with state_lock:
        assert state['scanning'] == False
        assert state['question'] is None
        assert state['results']  == {}
        assert state['revealed'] == False
    return "initial state OK"

def test_state_concurrent_write():
    errors = []
    def writer(i):
        try:
            with state_lock:
                state['results'][str(i)] = 'A'
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()
    with state_lock:
        assert len(state['results']) == 50, f"Expected 50, got {len(state['results'])}"
        state['results'] = {}  # reset
    assert not errors, f"Thread errors: {errors}"
    return "50 concurrent writes, no race conditions"

check("Initial state",           test_state_initial)
check("Concurrent writes",       test_state_concurrent_write)


# ─── TEST 5: FLASK API ────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 5: FLASK API ENDPOINTS")
print("="*60)

from src.web.app_web import app

client = app.test_client()

def test_api_class():
    r = client.get('/api/class')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert 'students' in d
    return f"200 OK, {len(d['students'])} students"

def test_api_questions():
    r = client.get('/api/questions')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert isinstance(d, list) and len(d) > 0
    return f"200 OK, {len(d)} questions"

def test_api_state():
    r = client.get('/api/state')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert 'scanning' in d and 'results' in d
    return "200 OK, state fields present"

def test_api_start():
    q = {"id": 1, "text": "Test?", "options": {"A": "o1", "B": "o2", "C": "o3", "D": "o4"}, "correct": "A"}
    r = client.post('/api/start', json={"question": q})
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d.get('ok') == True
    with state_lock:
        assert state['scanning'] == True
        assert state['question']['id'] == 1
    return "scanning=True, question set"

def test_api_stop():
    r = client.post('/api/stop')
    assert r.status_code == 200
    with state_lock:
        assert state['scanning'] == False
    return "scanning=False"

def test_api_reveal():
    # Set some results first
    with state_lock:
        state['results'] = {'1': 'A', '2': 'B'}
        state['question'] = {"id": 1, "text": "Test?", "options": {}, "correct": "A"}
    r = client.post('/api/reveal')
    assert r.status_code == 200
    with state_lock:
        assert state['revealed'] == True
    return "revealed=True, CSV saved attempt"

def test_api_reset():
    r = client.post('/api/reset')
    assert r.status_code == 200
    with state_lock:
        assert state['scanning'] == False
        assert state['results'] == {}
        assert state['revealed'] == False
        assert state['question'] is None
    return "state fully reset"

def test_api_reload_data():
    r = client.post('/api/reload_data')
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d.get('ok') == True
    return "cache invalidated + reloaded"

def test_route_teacher():
    r = client.get('/')
    assert r.status_code == 200
    assert b'Plickers' in r.data
    return "200 OK, teacher.html rendered"

def test_route_display():
    r = client.get('/display')
    assert r.status_code == 200
    assert b'Plickers' in r.data
    return "200 OK, display.html rendered"

check("GET /api/class",        test_api_class)
check("GET /api/questions",    test_api_questions)
check("GET /api/state",        test_api_state)
check("POST /api/start",       test_api_start)
check("POST /api/stop",        test_api_stop)
check("POST /api/reveal",      test_api_reveal)
check("POST /api/reset",       test_api_reset)
check("POST /api/reload_data", test_api_reload_data)
check("GET / (teacher.html)",  test_route_teacher)
check("GET /display",          test_route_display)


# ─── TEST 6: DETECTOR ON SAMPLE IMAGES ────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 6: CARD DETECTION ON SAMPLE IMAGES")
print("="*60)

import cv2

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'data', 'samples')
sample_files = sorted([f for f in os.listdir(SAMPLES_DIR) if f.endswith('.jpg')])
print(f"  {INFO} Found {len(sample_files)} sample images")

correct_count = 0
wrong_count   = 0
miss_count    = 0

for fname in sample_files:
    img = cv2.imread(os.path.join(SAMPLES_DIR, fname))
    if img is None:
        print(f"  {FAIL} Cannot read: {fname}")
        miss_count += 1
        continue
    expected = fname.split('.')[0]   # e.g. "003-A"
    found = detector.process_image(img)
    found_ids = [str(c[0]) for c in found]
    if expected in found_ids:
        correct_count += 1
    elif found_ids:
        wrong_count += 1
        print(f"  WRONG  {fname:14} expected={expected} got={found_ids}")
    else:
        miss_count += 1
        print(f"  MISS   {fname:14} expected={expected}")

total = len(sample_files)
accuracy = correct_count / total * 100 if total > 0 else 0
print(f"\n  BINGO  : {correct_count}/{total} ({accuracy:.1f}%)")
print(f"  WRONG  : {wrong_count}")
print(f"  MISSED : {miss_count}")
results.append((accuracy >= 70, f"Card detection accuracy {accuracy:.1f}%"))


# ─── TEST 7: FILE STRUCTURE ────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TEST 7: FILE STRUCTURE")
print("="*60)

ROOT = os.path.dirname(__file__)
EXPECTED_FILES = [
    "run_web.py",
    "run_scanner.py",
    "requirements.txt",
    "README.md",
    "data/class.json",
    "data/questions.json",
    "data/database/card.data",
    "data/database/card.list",
    "src/__init__.py",
    "src/app.py",
    "src/core/__init__.py",
    "src/core/detector.py",
    "src/core/utils.py",
    "src/web/__init__.py",
    "src/web/app_web.py",
    "src/web/templates/teacher.html",
    "src/web/templates/display.html",
    "src/scripts/__init__.py",
    "src/scripts/evaluate.py",
    "src/scripts/generate_db.py",
    "src/scripts/generate_pdf.py",
    "src/scripts/generate_plickers_pdf.py",
]

for fpath in EXPECTED_FILES:
    full = os.path.join(ROOT, fpath.replace('/', os.sep))
    exists = os.path.isfile(full)
    status = PASS if exists else FAIL
    print(f"  {status} {fpath}")
    results.append((exists, f"File: {fpath}"))


# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  TỔNG KẾT")
print("="*60)
passed = sum(1 for r in results if r[0])
failed = len(results) - passed
print(f"  PASSED : {passed}/{len(results)}")
if failed:
    print(f"  FAILED : {failed}")
    for r in results:
        if not r[0]:
            print(f"    - {r[1]}: {r[2] if len(r)>2 else 'missing'}")

print()
if failed == 0:
    print("  ✅ TẤT CẢ TESTS ĐẠT — SẴN SÀNG ĐƯA VÀO THỰC TẾ!")
else:
    print(f"  ⚠️  {failed} TEST THẤT BẠI — CẦN XEM LẠI!")
