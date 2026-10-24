#!/usr/bin/env bash
set -e
echo "Starting Single Mode Passive Income Docker..."
docker compose up -d --build
sleep 5
python3 check_status.py || python check_status.py
