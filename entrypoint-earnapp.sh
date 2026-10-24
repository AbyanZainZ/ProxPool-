#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "⚡ EARNAPP DOCKER CONTAINER INITIALIZING..."
echo "=========================================================="

mkdir -p /etc/earnapp

if ! command -v earnapp &> /dev/null; then
    echo "[EarnApp] Installing EarnApp via official Bright Data installer..."
    wget -qO- https://brightdata.com/static/earnapp/install.sh > /tmp/earnapp.sh
    echo "y" | bash /tmp/earnapp.sh || true
    rm -f /tmp/earnapp.sh
fi

echo "[EarnApp] Starting EarnApp engine..."
earnapp start || true

sleep 3

NODE_ID=""
if [ -f /etc/earnapp/status.json ]; then
    NODE_ID=$(grep -o '"node_id": *"[^"]*"' /etc/earnapp/status.json | cut -d'"' -f4 || true)
fi

if [ -z "$NODE_ID" ]; then
    NODE_ID=$(earnapp show-node-id 2>/dev/null || true)
fi

echo "=========================================================="
if [ -n "$NODE_ID" ]; then
    CLAIM_URL="https://earnapp.com/r/$NODE_ID"
    echo "🎉 EARNAPP NODE SUCCESSFULLY ACTIVATED!"
    echo "📌 Node ID : $NODE_ID"
    echo "👉 CLICK THIS URL TO LINK THIS NODE TO YOUR ACCOUNT:"
    echo "   $CLAIM_URL"
    echo "$CLAIM_URL" > /etc/earnapp/claim_url.txt
else
    echo "⚠️ Generating Node ID... Check again shortly using: python check_status.py"
fi
echo "=========================================================="

echo "[EarnApp] Running 24/7 background daemon..."
while true; do
    earnapp status || true
    sleep 300
done
