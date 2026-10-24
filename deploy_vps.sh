#!/usr/bin/env bash
# ==============================================================================
# PROXPOOL - 1-Command VPS Automated Installer (Ubuntu / Debian)
# Usage:
#   curl -sSL https://raw.githubusercontent.com/AbyanZainZ/ProxPool-/main/deploy_vps.sh | sudo bash
# ==============================================================================
set -e

REPO_URL="https://github.com/AbyanZainZ/ProxPool-.git"
INSTALL_DIR="/opt/ProxPool"
PORT=8899

echo "=================================================================="
echo "  PROXPOOL // 1-Command VPS Installer & TUN2SOCKS Orchestrator"
echo "=================================================================="

if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run this installer as root (sudo bash deploy_vps.sh)"
  exit 1
fi

echo "[1/6] Updating system packages and installing core dependencies..."
apt-get update -y
apt-get install -y curl git ca-certificates gnupg lsb-release python3 python3-pip python3-venv iptables iproute2

echo "[2/6] Checking Docker Engine & Docker Compose V2..."
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
else
  echo "      Docker is already installed."
fi

echo "[3/6] Enabling TUN/TAP kernel module and network sysctl tuning..."
modprobe tun || true
if ! grep -q "^tun$" /etc/modules 2>/dev/null; then
  echo "tun" >> /etc/modules
fi
cat <<EOF >/etc/sysctl.d/99-proxpool.conf
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 0
net.ipv4.conf.default.rp_filter = 0
fs.file-max = 2097152
EOF
sysctl --system >/dev/null 2>&1 || true

echo "[4/6] Cloning / Updating ProxPool repository in ${INSTALL_DIR}..."
if [ -d "${INSTALL_DIR}/.git" ]; then
  cd "${INSTALL_DIR}"
  git pull origin main || true
else
  rm -rf "${INSTALL_DIR}"
  git clone "${REPO_URL}" "${INSTALL_DIR}"
  cd "${INSTALL_DIR}"
fi

chmod +x *.sh || true
[ ! -f .env ] && cp .env.example .env
[ ! -f proxies.txt ] && cp proxies.txt.example proxies.txt

echo "[5/6] Setting up Python Virtual Environment & FastAPI Web Dashboard..."
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

echo "[6/6] Registering systemd service (proxpool.service on port ${PORT})..."
cat <<EOF >/etc/systemd/system/proxpool.service
[Unit]
Description=ProxPool Multi-Proxy Docker Command Center
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn app:app --host 0.0.0.0 --port ${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now proxpool.service

VPS_IP=$(curl -s4 ifconfig.me || hostname -I | awk '{print $1}')
echo "=================================================================="
echo "  PROXPOOL INSTALLATION COMPLETE!"
echo "  Web Command Center : http://${VPS_IP}:${PORT}"
echo "  Install Directory  : ${INSTALL_DIR}"
echo "  Service Status     : systemctl status proxpool"
echo "=================================================================="
