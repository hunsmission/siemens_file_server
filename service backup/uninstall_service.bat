@echo off
chcp 65001 >nul
echo ============================================
echo Siemens 파일 서버 - Windows 서비스 제거
echo ============================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] 이 스크립트는 관리자 권한이 필요합니다.
    echo 마우스 우클릭 후 "관리자 권한으로 실행"을 선택하세요.
    echo.
    pause
    exit /b 1
)

:: 현재 디렉토리
set SERVICE_DIR=%~dp0
set SERVICE_DIR=%SERVICE_DIR:~0,-1%

:: NSSM 확인
if not exist "%SERVICE_DIR%\nssm.exe" (
    echo [오류] NSSM이 없습니다.
    echo install_service.bat을 먼저 실행하세요.
    echo.
    pause
    exit /b 1
)

:: 서비스 확인
sc query SiemensFileServer >nul 2>&1
if %errorLevel% neq 0 (
    echo [알림] 서비스가 설치되어 있지 않습니다.
    echo.
    pause
    exit /b 0
)

echo [진행] 서비스 중지 중...
nssm stop SiemensFileServer
timeout /t 2 /nobreak >nul

echo [진행] 서비스 제거 중...
nssm remove SiemensFileServer confirm

echo.
echo ============================================
echo [완료] 서비스 제거 완료!
echo ============================================
echo.
echo 서비스가 제거되었습니다.
echo 파일 서버를 다시 사용하려면:
echo   - install_service.bat 실행 (서비스로 등록)
echo   - 또는 python file_server.py 실행 (직접 실행)
echo.

pause
