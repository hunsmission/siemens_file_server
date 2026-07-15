@echo off
chcp 437 >nul
setlocal

echo ============================================
echo  Siemens File Server - Start
echo ============================================
echo.

:: BASE_DIR = project root (parent of service folder)
set "BASE_DIR=%~dp0.."
pushd "%BASE_DIR%"
set "BASE_DIR=%CD%"
popd

:: Find Python
for /f "usebackq delims=" %%i in (`where python 2^>nul`) do (
    if not defined PYTHON_PATH set "PYTHON_PATH=%%i"
)
if not defined PYTHON_PATH (
    for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
    )
)
if not defined PYTHON_PATH (
    for /d %%d in ("C:\Python3*") do (
        if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
    )
)

if not defined PYTHON_PATH (
    echo [ERROR] Python not found. Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

if not exist "%BASE_DIR%\config.ini" (
    echo [ERROR] config.ini not found. Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

:: Read port from config.ini (display only)
for /f "tokens=1,* delims==" %%a in ('type "%BASE_DIR%\config.ini" ^| findstr /i "^port"') do (
    for /f "tokens=1 delims=#" %%x in ("%%b") do set "PORT=%%x"
)
set "PORT=%PORT: =%"
if not defined PORT set "PORT=8181"

echo  Config : %BASE_DIR%\config.ini
echo  Port   : %PORT%
echo.
echo  Access : http://localhost:%PORT%
echo.
echo  Press Ctrl+C to stop the server.
echo ============================================
echo.

cd /d "%BASE_DIR%"
"%PYTHON_PATH%" "%BASE_DIR%\file_server.py"

echo.
echo [INFO] Server stopped.
echo.
pause
endlocal
