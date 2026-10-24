@echo off
title ProxPool - Multi-Proxy Mode
echo =======================================================
echo  Generating & Starting Multi-Proxy Docker Matrix
echo =======================================================
python generate_multiproxy_compose.py
if exist docker-compose.multiproxy.yml (
    docker compose -f docker-compose.multiproxy.yml up -d --build
    echo.
    echo Waiting 5 seconds for proxy nodes to come online...
    timeout /t 5 /nobreak >nul
    python check_status.py
)
echo.
pause
