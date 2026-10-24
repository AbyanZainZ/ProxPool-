@echo off
title PROXPOOL Web Command Center (Port 8899)
cd /d "%~dp0"
echo ===================================================
echo   PROXPOOL - Multi-Proxy Docker Command Center
echo   Dashboard URL: http://127.0.0.1:8899
echo ===================================================
pip install -r requirements.txt
start "" http://127.0.0.1:8899
python -m uvicorn app:app --host 0.0.0.0 --port 8899
pause
