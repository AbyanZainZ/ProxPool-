@echo off
title Stop All Passive Income Docker
echo Stopping all containers...
docker compose down
if exist docker-compose.multiproxy.yml (
    docker compose -f docker-compose.multiproxy.yml down
)
echo All containers stopped.
pause
