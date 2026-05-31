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
        print("Web UI (local)  → http://0.0.0.0:8000")

        # ── Public URL (Tailscale Funnel → ngrok fallback) ───────────────
        public_url = None

        try:
            r = subprocess.run(
                ["tailscale", "funnel", "--bg", "8000"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                st = subprocess.run(
                    ["tailscale", "funnel", "status"],
                    capture_output=True, text=True, timeout=5,
                )
                url_line = next(
                    (l for l in st.stdout.splitlines() if "https://" in l), None
                )
                public_url = url_line.strip().split()[0] if url_line else None
            else:
                print(f"Tailscale Funnel not started: {r.stderr.strip()[:120]}")
        except FileNotFoundError:
            pass  # tailscale not installed, try ngrok below
        except Exception as e:
            print(f"Tailscale Funnel error: {e}")

        if not public_url:
            try:
                from pyngrok import ngrok
                authtoken = os.getenv("NGROK_AUTHTOKEN")
                if authtoken:
                    ngrok.set_auth_token(authtoken)
                tunnel = ngrok.connect(8000, "http")
                public_url = tunnel.public_url
            except ImportError:
                pass  # pyngrok not installed
            except Exception as e:
                print(f"ngrok error: {e}")

        if public_url:
            print(f"Web UI (public) → {public_url}")
        else:
            print("Web UI (public) → not available (install tailscale or set NGROK_AUTHTOKEN)")
        # ─────────────────────────────────────────────────────────────────

        start()  # blocks (sensor loop)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stop_all()
        print("All services stopped.")
