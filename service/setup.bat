@echo off
chcp 437 >nul
setlocal enabledelayedexpansion

echo ============================================
echo  Siemens File Server - Setup
echo ============================================
echo.

:: BASE_DIR = project root (parent of service folder)
set "BASE_DIR=%~dp0.."
pushd "%BASE_DIR%"
set "BASE_DIR=%CD%"
popd

:: SERVICE_DIR = service folder
set "SERVICE_DIR=%~dp0"
set "SERVICE_DIR=%SERVICE_DIR:~0,-1%"
set "OFFLINE_DIR=%SERVICE_DIR%\offline"

:: --------------------------------------------------
:: STEP 1: Find or install Python
:: --------------------------------------------------
echo [1/3] Checking Python...

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
    for /d %%d in ("C:\Program Files\Python3*") do (
        if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
    )
)

if defined PYTHON_PATH goto :check_ver

:: Python not found - try offline installer
echo        Python not found. Trying offline installer...

set "PY_INSTALLER="
for %%f in ("%OFFLINE_DIR%\python-*-amd64.exe") do (
    if not defined PY_INSTALLER set "PY_INSTALLER=%%f"
)

if not defined PY_INSTALLER (
    echo.
    echo [ERROR] Python is not installed and no offline installer was found.
    echo.
    echo  Option 1: Install Python from the internet, then re-run this script.
    echo    https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    echo.
    echo  Option 2: Copy the installer to the offline folder and re-run.
    echo    %OFFLINE_DIR%\python-3.11.9-amd64.exe
    echo.
    goto :error
)

echo        Installer found: %PY_INSTALLER%
echo        Installing Python silently... (please wait)
"%PY_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
if %errorLevel% neq 0 (
    echo [ERROR] Python installation failed. (exit code: %errorLevel%)
    goto :error
)

:: Re-scan after install
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
)
if not defined PYTHON_PATH (
    for /d %%d in ("C:\Python3*") do (
        if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
    )
)

if not defined PYTHON_PATH (
    echo [ERROR] Python installed but path could not be found.
    echo        Please open a new command prompt and run setup.bat again.
    goto :error
)
echo        [OK] Python installed successfully.

:check_ver
for /f "tokens=2 delims= " %%v in ('"%PYTHON_PATH%" --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=1 delims=." %%m in ("%PY_VER%") do set PY_MAJOR=%%m

if %PY_MAJOR% LSS 3 (
    echo [ERROR] Python 3.7 or higher is required. Found: %PY_VER%
    goto :error
)
echo        [OK] Python %PY_VER% found: %PYTHON_PATH%

:: --------------------------------------------------
:: STEP 2: Install packages
:: --------------------------------------------------
echo.
echo [2/3] Checking packages...

"%PYTHON_PATH%" -c "import flask" >nul 2>&1
if %errorLevel% equ 0 (
    echo        [SKIP] Packages are already installed.
    goto :packages_done
)

if exist "%OFFLINE_DIR%\wheels\" (
    echo        [OFFLINE] Installing from wheels folder...
    echo.
    "%PYTHON_PATH%" -m pip install --no-index --find-links="%OFFLINE_DIR%\wheels" -r "%BASE_DIR%\requirements.txt"
) else (
    echo        [ONLINE] Installing via pip...
    echo.
    "%PYTHON_PATH%" -m pip install -r "%BASE_DIR%\requirements.txt"
)

if %errorLevel% neq 0 (
    echo.
    echo [ERROR] Package installation failed.
    echo.
    echo  For offline environments, prepare the wheels folder:
    echo    Run on an internet-connected PC:
    echo      pip download flask==3.0.0 -d wheels --platform win_amd64 --python-version 311 --only-binary=:all:
    echo    Copy the wheels\ folder to: %OFFLINE_DIR%\
    echo.
    goto :error
)
echo.
echo        [OK] Packages installed.

:packages_done

:: --------------------------------------------------
:: STEP 3: config.ini
:: --------------------------------------------------
echo.
echo [3/3] Checking config.ini...

if exist "%BASE_DIR%\config.ini" (
    echo        [SKIP] config.ini already exists.
) else (
    if not exist "%BASE_DIR%\config.ini.sample" (
        echo [ERROR] config.ini.sample not found.
        goto :error
    )
    copy "%BASE_DIR%\config.ini.sample" "%BASE_DIR%\config.ini" >nul
    echo        [CREATED] config.ini has been created.
    echo.
    echo  *** Please edit config.ini and set root_directory and port ***
    echo      Location: %BASE_DIR%\config.ini
    echo.
    notepad "%BASE_DIR%\config.ini"
)

echo.
echo ============================================
echo  [DONE] Setup completed successfully.
echo ============================================
echo.
echo  To run the server:
echo    Direct  : service\start_server.bat
echo    Service : service\install_service.bat  (run as Administrator)
echo.
endlocal
exit /b 0

:error
echo.
pause
endlocal
exit /b 1
