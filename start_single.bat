@echo off
title ProxPool - Single Host Mode
echo =======================================================
echo  Starting ProxPool Docker Matrix (Single Host Mode)
echo =======================================================
docker compose up -d --build
echo.
echo Waiting 5 seconds for EarnApp node initialization...
timeout /t 5 /nobreak >nul
python check_status.py
echo.
pause
