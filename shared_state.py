import threading

_lock = threading.Lock()
_turbidity_threshold = 10.0


def get_threshold() -> float:
    with _lock:
        return _turbidity_threshold


def set_threshold(val: float) -> None:
    if val < 0:
        raise ValueError("Threshold must be >= 0")
    with _lock:
        global _turbidity_threshold
        _turbidity_threshold = float(val)
