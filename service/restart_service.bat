@echo off
chcp 437 >nul
setlocal

echo ============================================
echo  Siemens File Server - Restart Service
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

:: SERVICE_DIR = service folder
set "SERVICE_DIR=%~dp0"
set "SERVICE_DIR=%SERVICE_DIR:~0,-1%"
set "NSSM=%SERVICE_DIR%\nssm.exe"

:: BASE_DIR = project root
set "BASE_DIR=%~dp0.."
pushd "%BASE_DIR%"
set "BASE_DIR=%CD%"
popd

:: Check nssm.exe
if not exist "%NSSM%" (
    echo [ERROR] nssm.exe not found.
    echo        Please run install_service.bat first.
    goto :error
)

:: Check service
sc query SiemensFileServer >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Service is not installed.
    echo        Please run install_service.bat first.
    goto :error
)

:: Read port from config.ini
for /f "tokens=1,* delims==" %%a in ('type "%BASE_DIR%\config.ini" ^| findstr /i "^port"') do (
    for /f "tokens=1 delims=#" %%x in ("%%b") do set "PORT=%%x"
)
set "PORT=%PORT: =%"
if not defined PORT set "PORT=8181"

echo [1/2] Stopping service...
"%NSSM%" stop SiemensFileServer
timeout /t 3 /nobreak >nul

echo [2/2] Starting service...
"%NSSM%" start SiemensFileServer
timeout /t 3 /nobreak >nul

sc query SiemensFileServer | find "RUNNING" >nul
set SVC_RUNNING=%errorLevel%

if %SVC_RUNNING% equ 0 (
    echo.
    echo ============================================
    echo  [SUCCESS] Service restarted successfully.
    echo ============================================
    echo.
    echo  Access: http://localhost:%PORT%
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
