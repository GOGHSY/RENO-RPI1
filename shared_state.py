import json
import threading
from pathlib import Path

_lock = threading.Lock()
_THRESHOLD_FILE = Path(__file__).resolve().parent / "threshold_state.json"
_DEFAULT_THRESHOLD = 10.0


def _read_from_file() -> float:
    try:
        return float(json.loads(_THRESHOLD_FILE.read_text())["turbidity_threshold"])
    except Exception:
        return _DEFAULT_THRESHOLD


def get_threshold() -> float:
    with _lock:
        return _read_from_file()


def set_threshold(val: float) -> None:
    if val < 0:
        raise ValueError("Threshold must be >= 0")
    with _lock:
        _THRESHOLD_FILE.write_text(json.dumps({"turbidity_threshold": float(val)}))
