import logging
import os
import re
import subprocess
import threading
import time
import uvicorn
from full_system_package import start
from full_system_package.services.receiver import start_receiver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger(__name__)

_HOME = os.path.expanduser("~")
VICTORIA_METRICS_BIN  = os.path.join(_HOME, "victoria-metrics-prod")
VICTORIA_METRICS_DATA = os.path.join(_HOME, "victoria-metrics-data")
ZENOHD_BIN            = "/usr/local/bin/zenohd"

_procs = []


def port_open(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def launch(name: str, cmd: list) -> subprocess.Popen:
    _log.info("Starting %s...", name)
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1)
    if p.poll() is not None:
        err = p.stderr.read().decode(errors="replace")
        _log.error("%s exited immediately: %s", name, err[:200])
    else:
        _log.info("%s running (pid %d)", name, p.pid)
    _procs.append(p)
    return p


def stop_all() -> None:
    for p in _procs:
        p.terminate()
    for p in _procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def run_ui() -> None:
    uvicorn.run(
        "water_ui.ui.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
    )


def _resolve_public_url() -> str | None:
    try:
        subprocess.run(
            ["tailscale", "serve", "reset"],
            capture_output=True, text=True, timeout=10,
        )
        r = subprocess.run(
            ["tailscale", "funnel", "--bg", "8000"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            st = subprocess.run(
                ["tailscale", "funnel", "status"],
                capture_output=True, text=True, timeout=5,
            )
            m = re.search(r"https://\S+\.ts\.net\S*", st.stdout)
            return m.group(0) if m else None
        _log.warning("Tailscale Funnel: %s", r.stderr.strip()[:120])
    except FileNotFoundError:
        pass
    except Exception as e:
        _log.warning("Tailscale Funnel error: %s", e)

    return None


if __name__ == "__main__":
    try:
        if port_open(8428):
            _log.info("VictoriaMetrics already running")
        else:
            launch("VictoriaMetrics", [
                VICTORIA_METRICS_BIN,
                "-httpListenAddr=:8428",
                f"-storageDataPath={VICTORIA_METRICS_DATA}",
                "-retentionPeriod=3",  # months; VM drops older data automatically
            ])

        if port_open(7447):
            _log.info("Zenoh router already running")
        else:
            launch("Zenoh router", [ZENOHD_BIN])

        time.sleep(2)

        threading.Thread(target=start_receiver, daemon=True).start()
        _log.info("Zenoh receiver started")

        threading.Thread(target=run_ui, daemon=True).start()
        _log.info("Web UI → http://0.0.0.0:8000")

        public_url = _resolve_public_url()
        if public_url:
            _log.info("Web UI (public) → %s", public_url)
        else:
            _log.info("No public URL available (configure Tailscale)")

        start()

    except KeyboardInterrupt:
        _log.info("Shutting down...")
    finally:
        stop_all()
        _log.info("All services stopped.")
