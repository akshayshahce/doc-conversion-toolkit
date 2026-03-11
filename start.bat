@echo off
setlocal enabledelayedexpansion

cd /d %~dp0
set "ROOT_DIR=%cd%"
set "URL=http://127.0.0.1:8000"

call :log Checking system requirements.
call :ensure_python
if errorlevel 1 exit /b 1

call :ensure_node
if errorlevel 1 exit /b 1

if not exist .venv (
  call :log Creating Python virtual environment.
  py -3.11 -m venv .venv || py -3 -m venv .venv || python -m venv .venv
  if errorlevel 1 call :fail Failed to create Python virtual environment.& exit /b 1
)

call .venv\Scripts\activate
if errorlevel 1 call :fail Failed to activate virtual environment.& exit /b 1

call :log Installing backend dependencies.
python -m pip install --upgrade pip
if errorlevel 1 call :fail Failed to upgrade pip.& exit /b 1
pip install -r backend\requirements.txt
if errorlevel 1 call :fail Failed to install backend dependencies.& exit /b 1

call :log Installing frontend dependencies.
cd frontend
call npm install
if errorlevel 1 call :fail Failed to install frontend dependencies.& exit /b 1

call :log Building frontend.
call npm run build
if errorlevel 1 call :fail Failed to build frontend.& exit /b 1
cd ..

start "" "%URL%"
call :log Starting local server at %URL%
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
exit /b %errorlevel%

:ensure_python
set "PY_OK=0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
  if !errorlevel!==0 set "PY_OK=1"
)
if "!PY_OK!"=="0" (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if !errorlevel!==0 set "PY_OK=1"
  )
)
if "!PY_OK!"=="1" exit /b 0

call :log Python 3.11+ not found. Trying to install with winget.
where winget >nul 2>nul
if not %errorlevel%==0 call :fail Python is missing and winget is not available. Install Python 3.11+ and run start.bat again.& exit /b 1

winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
if errorlevel 1 call :fail Python installation failed. Install Python 3.11+ manually and run start.bat again.& exit /b 1
exit /b 0

:ensure_node
set "NEED_NODE=0"
where node >nul 2>nul
if not %errorlevel%==0 (
  set "NEED_NODE=1"
) else (
  for /f "tokens=1 delims=." %%v in ('node -v 2^>nul') do set "NODE_MAJOR=%%v"
  set "NODE_MAJOR=!NODE_MAJOR:v=!"
  if "!NODE_MAJOR!"=="" set "NEED_NODE=1"
  if !NODE_MAJOR! LSS 20 set "NEED_NODE=1"
)

where npm >nul 2>nul
if not %errorlevel%==0 set "NEED_NODE=1"

if "!NEED_NODE!"=="0" exit /b 0

call :log Node.js 22 not found. Trying to install with winget.
where winget >nul 2>nul
if not %errorlevel%==0 call :fail Node.js is missing and winget is not available. Install Node.js 22+ and run start.bat again.& exit /b 1

winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
if errorlevel 1 call :fail Node.js installation failed. Install Node.js 22+ manually and run start.bat again.& exit /b 1
exit /b 0

:log
echo.
echo [doc-toolkit] %*
exit /b 0

:fail
echo.
echo [doc-toolkit] %*
exit /b 1
