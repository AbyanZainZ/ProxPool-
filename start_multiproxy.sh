#!/usr/bin/env bash
set -e
python3 generate_multiproxy_compose.py || python generate_multiproxy_compose.py
if [ -f docker-compose.multiproxy.yml ]; then
    docker compose -f docker-compose.multiproxy.yml up -d --build
    sleep 5
    python3 check_status.py || python check_status.py
fi
