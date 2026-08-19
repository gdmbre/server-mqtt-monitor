#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/server-monitor"
CONFIG_DIR="/etc/server-monitor"
SERVICE_FILE="/etc/systemd/system/server-monitor.service"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this installer as root: sudo ./install.sh"
    exit 1
fi

apt-get update
apt-get install -y python3 python3-venv smartmontools

mkdir -p "${APP_DIR}" "${CONFIG_DIR}"

python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip
"${APP_DIR}/venv/bin/pip" install .

if [[ ! -f "${CONFIG_DIR}/config.toml" ]]; then
    cp config.example.toml "${CONFIG_DIR}/config.toml"
    chmod 600 "${CONFIG_DIR}/config.toml"
    echo "Created ${CONFIG_DIR}/config.toml - edit MQTT and host settings before starting."
fi

cp server-monitor.service "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable server-monitor

echo
echo "Installation complete."
echo "Edit: sudo nano ${CONFIG_DIR}/config.toml"
echo "Then start: sudo systemctl start server-monitor"
echo "Logs: sudo journalctl -u server-monitor -f"
