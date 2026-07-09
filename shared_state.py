import json
import threading
from pathlib import Path

_lock = threading.Lock()
_BASE_DIR = Path(__file__).resolve().parent
_THRESHOLD_FILE = _BASE_DIR / "threshold_state.json"
DOSE_STATE_FILE  = _BASE_DIR / "dose_state.json"
RELAY_STATE_FILE = _BASE_DIR / "relay_state.json"
_DEFAULT_THRESHOLD = 10.0

_relay_on = False


def read_json(path: Path, defaults: dict) -> dict:
    try:
        data = json.loads(path.read_text())
        for key, val in defaults.items():
            data.setdefault(key, val)
        return data
    except Exception:
        return dict(defaults)


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data))


def get_relay_on() -> bool:
    with _lock:
        return _relay_on


def set_relay_on(val: bool) -> None:
    global _relay_on
    with _lock:
        _relay_on = val


def get_threshold() -> float:
    with _lock:
        return float(read_json(_THRESHOLD_FILE, {"turbidity_threshold": _DEFAULT_THRESHOLD})["turbidity_threshold"])


def set_threshold(val: float) -> None:
    if val < 0:
        raise ValueError("Threshold must be >= 0")
    with _lock:
        write_json(_THRESHOLD_FILE, {"turbidity_threshold": float(val)})
