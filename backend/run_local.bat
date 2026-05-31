@echo off
REM ---- PMO Dashboard backend (local dev) ----
cd /d "%~dp0"
where py >nul 2>&1 && set PY=py -3 || set PY=python
%PY% -c "import flask" >nul 2>&1 || ( echo Installing dependencies... & %PY% -m pip install -r requirements.txt )
echo Starting backend at http://localhost:8000  (Ctrl+C to stop)
%PY% app.py
pause
