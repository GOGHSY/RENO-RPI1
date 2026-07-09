#!/usr/bin/env bash
# Sets up a second, independent RENO-RPI1 filtration unit on a fresh Raspberry Pi.
# Run this ON the new Pi (copy it over first: scp scripts/setup_new_pi.sh pi@newhost:~/).
set -euo pipefail

REPO_URL="git@github.com:GOGHSY/RENO-RPI1.git"
INSTALL_DIR="$HOME/RENO-RPI1"

echo "== RENO-RPI1: new Pi setup =="

if [ -d "$INSTALL_DIR" ]; then
    echo "Found existing $INSTALL_DIR, pulling latest instead of cloning."
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt

echo
echo "-- VictoriaMetrics / zenohd check --"
if [ ! -x "$HOME/victoria-metrics-prod" ]; then
    echo "MISSING: $HOME/victoria-metrics-prod"
    echo "  Download the Pi-arch build from https://victoriametrics.com/ and place it there (chmod +x)."
fi
command -v zenohd >/dev/null || echo "MISSING: zenohd not on PATH. Install from https://zenoh.io/download/"

echo
echo "-- Per-site config --"

echo "USB serial adapters currently visible on this Pi:"
ls /dev/serial/by-id/ 2>/dev/null || echo "  (none found — plug in the flow/turbidity adapters first)"
read -rp "Flow meter by-id filename (as shown above): " FLOW_ID
read -rp "Turbidity sensor by-id filename (as shown above): " TURB_ID

read -rp "This site's RPi2 Tailscale/LAN IP (chemical-treatment Pi): " RPI2_IP
read -rp "Site number/suffix for Zenoh keys, e.g. 011 (must differ from other sites): " SITE_ID

CONFIG=full_system_package/utils/config.py
RECEIVER=full_system_package/services/receiver.py
MAIN=full_system_package/main.py

sed -i.bak "s#^FLOW_PORT = .*#FLOW_PORT = '/dev/serial/by-id/${FLOW_ID}'#" "$CONFIG"
sed -i.bak "s#^TURBIDITY_PORT = .*#TURBIDITY_PORT = '/dev/serial/by-id/${TURB_ID}'#" "$CONFIG"
sed -i.bak "s#^ZENOH_ROUTER = .*#ZENOH_ROUTER = \"tcp/${RPI2_IP}:7447\"  # <-- your IP from zenohd#" "$RECEIVER"
sed -i.bak "s#^ZENOH_KEY = .*#ZENOH_KEY = \"reno/water/treatment/${SITE_ID}\"#" "$RECEIVER"
sed -i.bak "s#reno/water/alum/pump#reno/water/alum/pump/${SITE_ID}#" "$MAIN"
rm -f "$CONFIG.bak" "$RECEIVER.bak" "$MAIN.bak"

echo
echo "Set WTP_PASS env var if you want a non-default dashboard password (default: reno@123)."
echo
echo "Review the config diff:"
git diff -- "$CONFIG" "$RECEIVER" "$MAIN"

echo
read -rp "Install as a systemd service so it autostarts on boot? [y/N] " DO_SERVICE
if [[ "$DO_SERVICE" =~ ^[Yy]$ ]]; then
    sed -e "s#__USER__#$(whoami)#" -e "s#__INSTALL_DIR__#${INSTALL_DIR}#" \
        scripts/reno-rpi1.service.template | sudo tee /etc/systemd/system/reno-rpi1.service >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl enable --now reno-rpi1.service
    echo "Installed and started. Check with: sudo systemctl status reno-rpi1"
else
    echo "Skipped. Start manually with: source .venv/bin/activate && python run.py"
fi
