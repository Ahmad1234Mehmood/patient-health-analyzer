@echo off
REM One-command setup + launch (Windows).  Double-click or run in a terminal.
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set "PYCMD=py -3") else (set "PYCMD=python")
%PYCMD% --version >nul 2>nul || (echo Python 3 not found. Install Python 3.10+ from python.org and tick "Add to PATH". & pause & exit /b 1)
where npm >nul 2>nul || (echo Node.js not found. Install Node 18+ from nodejs.org. & pause & exit /b 1)

echo ==^> Backend: virtual environment + dependencies
if not exist backend\.venv (%PYCMD% -m venv backend\.venv)
backend\.venv\Scripts\python -m pip install --quiet --upgrade pip
backend\.venv\Scripts\python -m pip install --quiet -r backend\requirements.txt
if not exist backend\.env copy backend\.env.example backend\.env >nul

echo ==^> Frontend: npm install
if not exist frontend\node_modules (pushd frontend & call npm install --no-audit --no-fund & popd)

echo ==^> Starting servers in two new windows...
start "PHA Backend  (http://localhost:5000)" cmd /k "cd /d %~dp0backend && ..\backend\.venv\Scripts\python run.py"
start "PHA Frontend (http://localhost:5173)" cmd /k "cd /d %~dp0frontend && npm run dev -- --host 127.0.0.1"
timeout /t 8 >nul
start http://localhost:5173
echo Done. Close the two server windows to stop the app.
endlocal


