import subprocess
import threading
import time
import sys
import os
import uvicorn
from full_system_package import start

# ── Binary paths (adjust if yours differ) ────────────────────────────────────
VICTORIA_METRICS_BIN  = os.path.expanduser("~/victoria-metrics")
VICTORIA_METRICS_DATA = os.path.expanduser("~/vm-data")
ZENOHD_BIN            = os.path.expanduser("~/zenohd")
# ─────────────────────────────────────────────────────────────────────────────

_procs = []


def launch(name, cmd):
    print(f"Starting {name}...")
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _procs.append(p)
    return p


def stop_all():
    for p in _procs:
        p.terminate()
    for p in _procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def run_ui():
    uvicorn.run(
        "water_ui.ui.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
    )


if __name__ == "__main__":
    try:
        launch("VictoriaMetrics", [
            VICTORIA_METRICS_BIN,
            "-httpListenAddr=:8428",
            f"-storageDataPath={VICTORIA_METRICS_DATA}",
        ])

        launch("Zenoh router", [ZENOHD_BIN])

        # Give infrastructure a moment to come up
        time.sleep(2)

        ui_thread = threading.Thread(target=run_ui, daemon=True)
        ui_thread.start()
        print("Web UI      → http://0.0.0.0:8000")

        start()  # blocks (sensor loop + zenoh receiver thread inside)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_all()
        print("All services stopped.")
