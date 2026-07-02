import threading

state_lock = threading.Lock()
app_state = {
    "scanning": False,
    "question": None,
    "results": {},
    "revealed": False,
    "session_ts": None,
}

frame_lock = threading.Lock()
output_frame: bytes | None = None
