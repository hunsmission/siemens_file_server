@echo off
chcp 437 >nul
setlocal enabledelayedexpansion

echo ============================================
echo  Siemens File Server - Install Service
echo ============================================
echo.

:: Check administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Administrator privileges required.
    echo        Right-click this file and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: BASE_DIR = project root (parent of service folder)
set "BASE_DIR=%~dp0.."
pushd "%BASE_DIR%"
set "BASE_DIR=%CD%"
popd

:: SERVICE_DIR = service folder (nssm.exe stored here)
set "SERVICE_DIR=%~dp0"
set "SERVICE_DIR=%SERVICE_DIR:~0,-1%"
set "NSSM=%SERVICE_DIR%\nssm.exe"
set "OFFLINE_DIR=%SERVICE_DIR%\offline"

:: Find Python (prefer system-wide install for service context)
for /d %%d in ("C:\Python3*") do (
    if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
)
if not defined PYTHON_PATH (
    for /d %%d in ("C:\Program Files\Python3*") do (
        if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
    )
)
if not defined PYTHON_PATH (
    for /f "usebackq delims=" %%i in (`where python 2^>nul`) do (
        if not defined PYTHON_PATH set "PYTHON_PATH=%%i"
    )
)
if not defined PYTHON_PATH (
    for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%d\python.exe" if not defined PYTHON_PATH set "PYTHON_PATH=%%d\python.exe"
    )
)

if not defined PYTHON_PATH (
    echo [ERROR] Python not found. Please run setup.bat first.
    goto :error
)

:: Check config.ini
if not exist "%BASE_DIR%\config.ini" (
    echo [ERROR] config.ini not found. Please run setup.bat first.
    goto :error
)

:: Read port from config.ini
for /f "tokens=1,* delims==" %%a in ('type "%BASE_DIR%\config.ini" ^| findstr /i "^port"') do (
    for /f "tokens=1 delims=#" %%x in ("%%b") do set "PORT=%%x"
)
set "PORT=%PORT: =%"
if not defined PORT set "PORT=8181"

:: --------------------------------------------------
:: STEP 1: Get nssm.exe
::   Priority: service\nssm.exe -> offline\nssm.exe -> online download
:: --------------------------------------------------
echo [1/4] Checking NSSM...

if exist "%NSSM%" (
    echo        [SKIP] nssm.exe already exists.
    goto :nssm_ready
)

:: Try offline copy first (no PowerShell needed)
if exist "%OFFLINE_DIR%\nssm.exe" (
    echo        [OFFLINE] Copying nssm.exe from offline folder...
    copy "%OFFLINE_DIR%\nssm.exe" "%NSSM%" >nul
    if exist "%NSSM%" (
        echo        [OK] nssm.exe copied.
        goto :nssm_ready
    )
    echo [ERROR] Failed to copy nssm.exe.
    goto :error
)

:: Online download
echo        nssm.exe not found.
echo.
echo        Option 1: Auto download  (requires PowerShell + internet)
echo        Option 2: Manual install
echo          Download: https://nssm.cc/download  (nssm-2.24.zip)
echo          Extract win64\nssm.exe and place it at one of:
echo            %NSSM%
echo            %OFFLINE_DIR%\nssm.exe
echo.
choice /c 12 /n /m "        Choose (1=Auto download, 2=Manual): "

if errorlevel 2 (
    echo.
    echo        Manual selected. Place nssm.exe and re-run this script.
    echo.
    pause
    exit /b 0
)

:: Check PowerShell availability
where powershell >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [ERROR] PowerShell not found. Cannot auto-download.
    echo        Place nssm.exe manually at: %NSSM%
    echo.
    goto :error
)

echo.
echo        Downloading NSSM...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%SERVICE_DIR%\nssm.zip'"

if not exist "%SERVICE_DIR%\nssm.zip" (
    echo [ERROR] Download failed. Check internet connection or firewall.
    goto :error
)

echo        Extracting...
powershell -NoProfile -Command "Expand-Archive -Path '%SERVICE_DIR%\nssm.zip' -DestinationPath '%SERVICE_DIR%\nssm_tmp' -Force"

copy "%SERVICE_DIR%\nssm_tmp\nssm-2.24\win64\nssm.exe" "%NSSM%" >nul
rmdir /s /q "%SERVICE_DIR%\nssm_tmp" >nul 2>&1
del "%SERVICE_DIR%\nssm.zip" >nul 2>&1

if not exist "%NSSM%" (
    echo [ERROR] Failed to extract nssm.exe.
    goto :error
)
echo        [OK] NSSM downloaded.

:nssm_ready

:: --------------------------------------------------
:: STEP 2: Remove existing service if present
:: --------------------------------------------------
echo.
echo [2/4] Checking existing service...

sc query SiemensFileServer >nul 2>&1
if %errorLevel% equ 0 (
    echo        Existing service found. Reinstalling...
    echo        Stopping service...
    "%NSSM%" stop SiemensFileServer >nul 2>&1
    timeout /t 3 /nobreak >nul
    echo        Removing old service...
    "%NSSM%" remove SiemensFileServer confirm >nul 2>&1
    timeout /t 2 /nobreak >nul
    echo        [OK] Old service removed.
) else (
    echo        [SKIP] No existing service found.
)

:: --------------------------------------------------
:: STEP 3: Install service
:: --------------------------------------------------
echo.
echo [3/4] Installing service...

if not exist "%BASE_DIR%\logs" mkdir "%BASE_DIR%\logs"

"%NSSM%" install SiemensFileServer "%PYTHON_PATH%" "%BASE_DIR%\file_server.py"
"%NSSM%" set SiemensFileServer AppDirectory    "%BASE_DIR%"
"%NSSM%" set SiemensFileServer AppEnvironmentExtra "PYTHONIOENCODING=utf-8" "PYTHONUTF8=1"
"%NSSM%" set SiemensFileServer DisplayName     "Siemens File Server"
"%NSSM%" set SiemensFileServer Description     "Siemens File Server (port %PORT%)"
"%NSSM%" set SiemensFileServer Start           SERVICE_AUTO_START
"%NSSM%" set SiemensFileServer AppStdout       "%BASE_DIR%\logs\service.log"
"%NSSM%" set SiemensFileServer AppStderr       "%BASE_DIR%\logs\service_error.log"
"%NSSM%" set SiemensFileServer AppRotateFiles  1
"%NSSM%" set SiemensFileServer AppRotateBytes  10485760
"%NSSM%" set SiemensFileServer AppRestartDelay 3000

echo        [OK] Service installed.

:: --------------------------------------------------
:: STEP 4: Start service
:: --------------------------------------------------
echo.
echo [4/4] Starting service...
"%NSSM%" start SiemensFileServer
timeout /t 3 /nobreak >nul

sc query SiemensFileServer | find "RUNNING" >nul
set SVC_RUNNING=%errorLevel%

if %SVC_RUNNING% equ 0 (
    echo.
    echo ============================================
    echo  [SUCCESS] Service installed and running!
    echo ============================================
    echo.
    echo  Service name : SiemensFileServer
    echo  Startup type : Automatic - starts with Windows
    echo  Access       : http://localhost:%PORT%
    echo.
    echo  Log files:
    echo    %BASE_DIR%\logs\service.log
    echo    %BASE_DIR%\logs\service_error.log
    echo.
    echo  Manage service:
    echo    Remove   : service\uninstall_service.bat  - run as Administrator
    echo    Restart  : service\restart_service.bat    - run as Administrator
    echo    Services : services.msc
    echo.
) else (
    echo.
    echo [ERROR] Service failed to start.
    echo        Check: %BASE_DIR%\logs\service_error.log
    goto :error
)

endlocal
pause
exit /b 0

:error
echo.
pause
endlocal
exit /b 1
