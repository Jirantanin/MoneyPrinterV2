@echo off
setlocal

set "PORT=8899"
set "ROOT=%~dp0"

echo [restart] Killing any process on port %PORT%...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":%PORT% "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [restart] Starting Studio...
cd /d "%ROOT%"
call venv\Scripts\activate.bat
py -c "from src.podcast_server import launch_podcast_server; launch_podcast_server()"
