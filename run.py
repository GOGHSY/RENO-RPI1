import subprocess
import threading
import time
import sys
import os
import uvicorn
from full_system_package import start
from full_system_package.services.receiver import start_receiver

# ── Binary paths (adjust if yours differ) ────────────────────────────────────
VICTORIA_METRICS_BIN  = "/home/suprabha/victoria-metrics-prod"
VICTORIA_METRICS_DATA = "/home/suprabha/victoria-metrics-data"
ZENOHD_BIN            = "/usr/local/bin/zenohd"
# ─────────────────────────────────────────────────────────────────────────────

_procs = []


def port_open(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def launch(name, cmd):
    print(f"Starting {name}...")
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1)
    if p.poll() is not None:
        err = p.stderr.read().decode(errors="replace")
        print(f"[ERROR] {name} exited immediately: {err[:200]}")
    else:
        print(f"{name} running (pid {p.pid})")
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
        if port_open(8428):
            print("VictoriaMetrics already running, skipping launch")
        else:
            launch("VictoriaMetrics", [
                VICTORIA_METRICS_BIN,
                "-httpListenAddr=:8428",
                f"-storageDataPath={VICTORIA_METRICS_DATA}",
            ])

        if port_open(7447):
            print("Zenoh router already running, skipping launch")
        else:
            launch("Zenoh router", [ZENOHD_BIN])

        # Give infrastructure a moment to come up
        time.sleep(2)

        receiver_thread = threading.Thread(target=start_receiver, daemon=True)
        receiver_thread.start()
        print("Zenoh receiver started")

        ui_thread = threading.Thread(target=run_ui, daemon=True)
        ui_thread.start()
        print("Web UI      → http://0.0.0.0:8000")

        start()  # blocks (sensor loop)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_all()
        print("All services stopped.")
