@echo off
chcp 437 >nul
setlocal

echo ============================================
echo  Siemens File Server - Uninstall Service
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
    echo [INFO] No installed service found.
    echo.
    pause
    exit /b 0
)

echo  This will stop and remove the SiemensFileServer service.
echo.
choice /c YN /n /m "  Continue? (Y/N): "
if errorlevel 2 (
    echo.
    echo  Cancelled.
    echo.
    pause
    exit /b 0
)

echo.
echo [1/2] Stopping service...
"%NSSM%" stop SiemensFileServer
timeout /t 3 /nobreak >nul

echo [2/2] Removing service...
"%NSSM%" remove SiemensFileServer confirm

echo.
echo ============================================
echo  [DONE] Service removed successfully.
echo ============================================
echo.
echo  To re-register: service\install_service.bat  (as Administrator)
echo  To run directly: service\start_server.bat
echo.
endlocal
pause
exit /b 0

:error
echo.
pause
endlocal
exit /b 1
