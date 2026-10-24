#!/usr/bin/env bash
docker compose down
if [ -f docker-compose.multiproxy.yml ]; then
    docker compose -f docker-compose.multiproxy.yml down
fi
echo "All containers stopped."
