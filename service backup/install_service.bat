@echo off
chcp 65001 >nul
echo ============================================
echo Siemens 파일 서버 - Windows 서비스 설치
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

:: Python 경로 찾기
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않거나 PATH에 없습니다.
    echo.
    pause
    exit /b 1
)

:: Python 경로 가져오기
for /f "tokens=*" %%i in ('where python') do set PYTHON_PATH=%%i
echo [정보] Python 경로: %PYTHON_PATH%

:: 현재 디렉토리
set SERVICE_DIR=%~dp0
set SERVICE_DIR=%SERVICE_DIR:~0,-1%
echo [정보] 서비스 디렉토리: %SERVICE_DIR%

:: NSSM 다운로드 확인
if not exist "%SERVICE_DIR%\nssm.exe" (
    echo.
    echo [알림] NSSM을 다운로드해야 합니다.
    echo.
    echo 방법 1: 자동 다운로드
    echo   - 계속하려면 아무 키나 누르세요
    echo.
    echo 방법 2: 수동 다운로드
    echo   - https://nssm.cc/download 에서 다운로드
    echo   - nssm-2.24\win64\nssm.exe 파일을 이 폴더에 복사
    echo   - 그리고 이 스크립트를 다시 실행
    echo.
    choice /c 12 /n /m "선택하세요 (1=자동, 2=수동): "

    if errorlevel 2 (
        echo.
        echo 수동 다운로드를 선택했습니다.
        echo NSSM을 다운로드한 후 다시 실행하세요.
        pause
        exit /b 0
    )

    echo.
    echo [진행] NSSM 다운로드 중...
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile '%SERVICE_DIR%\nssm.zip'}"

    if not exist "%SERVICE_DIR%\nssm.zip" (
        echo [오류] NSSM 다운로드 실패
        pause
        exit /b 1
    )

    echo [진행] 압축 해제 중...
    powershell -Command "& {Expand-Archive -Path '%SERVICE_DIR%\nssm.zip' -DestinationPath '%SERVICE_DIR%' -Force}"

    copy "%SERVICE_DIR%\nssm-2.24\win64\nssm.exe" "%SERVICE_DIR%\nssm.exe" >nul

    if exist "%SERVICE_DIR%\nssm.zip" del "%SERVICE_DIR%\nssm.zip"
    if exist "%SERVICE_DIR%\nssm-2.24" rmdir /s /q "%SERVICE_DIR%\nssm-2.24"

    echo [완료] NSSM 다운로드 완료
)

echo.
echo [정보] NSSM 발견: %SERVICE_DIR%\nssm.exe

:: 기존 서비스 확인
sc query SiemensFileServer >nul 2>&1
if %errorLevel% equ 0 (
    echo.
    echo [알림] 서비스가 이미 설치되어 있습니다.
    echo 기존 서비스를 제거하고 다시 설치합니다.
    echo.

    :: 서비스 중지
    echo [진행] 서비스 중지 중...
    nssm stop SiemensFileServer
    timeout /t 2 /nobreak >nul

    :: 서비스 제거
    echo [진행] 기존 서비스 제거 중...
    nssm remove SiemensFileServer confirm
)

:: 서비스 설치
echo.
echo [진행] 서비스 설치 중...
nssm install SiemensFileServer "%PYTHON_PATH%" "%SERVICE_DIR%\file_server.py"

:: 서비스 설정
echo [진행] 서비스 설정 중...
nssm set SiemensFileServer AppDirectory "%SERVICE_DIR%"
nssm set SiemensFileServer DisplayName "Siemens File Server"
nssm set SiemensFileServer Description "Siemens 파일 공유 서버 - 포트 8181"
nssm set SiemensFileServer Start SERVICE_AUTO_START
nssm set SiemensFileServer AppStdout "%SERVICE_DIR%\service_log.txt"
nssm set SiemensFileServer AppStderr "%SERVICE_DIR%\service_error.txt"

:: 서비스 시작
echo [진행] 서비스 시작 중...
nssm start SiemensFileServer

:: 결과 확인
timeout /t 2 /nobreak >nul
sc query SiemensFileServer | find "RUNNING" >nul
if %errorLevel% equ 0 (
    echo.
    echo ============================================
    echo [성공] 서비스 설치 및 시작 완료!
    echo ============================================
    echo.
    echo 서비스 이름: SiemensFileServer
    echo 상태: 실행 중
    echo 시작 유형: 자동 (Windows 시작 시 자동 실행)
    echo.
    echo 접속 주소:
    echo   - 로컬: http://localhost:8181
    echo   - 네트워크: http://[이 PC의 IP]:8181
    echo.
    echo 로그 파일:
    echo   - %SERVICE_DIR%\service_log.txt
    echo   - %SERVICE_DIR%\service_error.txt
    echo.
    echo 서비스 관리:
    echo   - 중지: uninstall_service.bat 실행
    echo   - 또는 서비스 관리자(services.msc)에서 관리
    echo.
) else (
    echo.
    echo [오류] 서비스 시작 실패
    echo service_error.txt 파일을 확인하세요.
    echo.
)

pause
