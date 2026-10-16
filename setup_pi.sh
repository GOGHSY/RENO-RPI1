#!/usr/bin/env bash
# One-time setup on a fresh Raspberry Pi OS 64-bit. Run from the repo root: ./setup_pi.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
ME="$(whoami)"

sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv python3-dev swig liblgpio-dev
sudo apt install -y victoria-metrics || echo "!! victoria-metrics not in apt: grab the linux-arm64 binary from github.com/VictoriaMetrics/VictoriaMetrics/releases"

# Zenoh router
echo "deb [trusted=yes] https://download.eclipse.org/zenoh/debian-repo/ /" | sudo tee /etc/apt/sources.list.d/zenoh.list
sudo apt update && sudo apt install -y zenoh
if ! systemctl cat zenohd >/dev/null 2>&1; then
  sudo tee /etc/systemd/system/zenohd.service >/dev/null <<EOF
[Unit]
Description=Zenoh router
After=network-online.target
[Service]
ExecStart=$(command -v zenohd)
Restart=always
[Install]
WantedBy=multi-user.target
EOF
fi

# Tailscale (prints a login URL — open it)
command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Python deps; zenoh python must match zenohd's version
python3 -m venv "$REPO/venv"
"$REPO/venv/bin/pip" install -r "$REPO/requirements.txt"
ZV="$(zenohd --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
"$REPO/venv/bin/pip" install "eclipse-zenoh==$ZV" || echo "!! no eclipse-zenoh==$ZV wheel, keeping latest"

sudo usermod -aG dialout,gpio "$ME"  # serial + GPIO without sudo

unit() {  # name, command
  sudo tee "/etc/systemd/system/$1.service" >/dev/null <<EOF
[Unit]
After=network-online.target zenohd.service victoria-metrics.service
[Service]
User=$ME
WorkingDirectory=$REPO
Environment=PYTHONUNBUFFERED=1
ExecStart=$2
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
}
unit reno-sensors "$REPO/venv/bin/python run.py"
unit reno-ui "$REPO/venv/bin/python -m uvicorn water_ui.ui.main:app --host 0.0.0.0 --port 8000"

sudo systemctl daemon-reload
sudo systemctl enable zenohd reno-sensors reno-ui
sudo systemctl enable victoria-metrics 2>/dev/null || true

echo
echo "Tailscale IP of this Pi (put it in RPI2's zenoh connect endpoint):"
tailscale ip -4
echo "USB serial adapters (put these in full_system_package/utils/config.py):"
ls -l /dev/serial/by-id/ 2>/dev/null || echo "  none plugged in"
echo "Now: sudo reboot"
