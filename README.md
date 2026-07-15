# 파일 서버 for Siemens Project

Siemens에서 Project 수행을 위한 깔끔한 UI를 가진 간단한 파일 공유 서버입니다.

## 빠른 시작 (배치파일)

| 파일 | 설명 | 권한 |
|------|------|------|
| `service\setup.bat` | Python 패키지 설치 + config.ini 생성 | 일반 |
| `service\start_server.bat` | 서버 직접 실행 (콘솔 창) | 일반 |
| `service\install_service.bat` | Windows 서비스로 등록 (부팅 시 자동 시작) | **관리자** |
| `service\uninstall_service.bat` | Windows 서비스 제거 | **관리자** |
| `service\restart_service.bat` | Windows 서비스 재시작 | **관리자** |

### 처음 설치하는 경우

```
1. service\setup.bat 실행
   → config.ini 가 자동 생성되고 메모장이 열립니다.
   → root_directory 와 port 를 확인·수정 후 저장하세요.

2-A. 직접 실행 (콘솔 창 유지)
   → service\start_server.bat 실행

2-B. Windows 서비스로 등록 (권장 — 백그라운드 상시 실행)
   → service\install_service.bat 을 마우스 우클릭 → 관리자 권한으로 실행
```

### 이미 설치된 경우

- `service\setup.bat` 재실행 시 Python·패키지·config.ini 가 이미 존재하면 자동으로 Skip됩니다.
- `service\install_service.bat` 재실행 시 기존 서비스를 자동으로 제거 후 재설치합니다.

## 설정

`config.ini.sample`을 복사하여 `config.ini`를 만든 뒤 값을 수정하세요.  
(`setup.bat` 실행 시 자동으로 생성됩니다.)

```ini
[server]
# 파일 서버가 열릴 포트 번호
port = 8181

# 공유할 파일들이 있는 루트 디렉토리 경로
root_directory = C:\Siemens
```

> `config.ini`는 `.gitignore`에 등록되어 있어 git에 커밋되지 않습니다.

## 수동 설치 방법

1. Python 설치 (Python 3.7 이상, 설치 시 "Add Python to PATH" 체크)

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 수동 실행 방법

1. 설정 파일에서 `root_directory`와 `port`를 원하는 값으로 수정

2. 서버 실행:
```bash
python file_server.py
```

3. 브라우저에서 접속:
   - 같은 PC: `http://localhost:8181`
   - 다른 PC: `http://<이_PC의_IP>:8181`

## IP 주소 확인 방법

Windows에서 명령 프롬프트를 열고:
```bash
ipconfig
```

"IPv4 주소" 항목을 확인하세요 (예: 192.168.0.10)

## 방화벽 설정

다른 PC에서 접속이 안 되면 Windows 방화벽에서 포트를 열어야 합니다:
1. Windows 방화벽 설정 열기
2. 고급 설정 → 인바운드 규칙 → 새 규칙
3. 포트 → TCP → 특정 로컬 포트: `config.ini`에 설정한 포트 번호
4. 연결 허용 → 다음 → 이름: "Flask File Server"

## 기능

### 📁 파일 공유
- 파일 및 폴더 업로드 (최대 50GB, 드래그 앤 드롭 지원)
- 파일 및 폴더 다운로드 (폴더는 ZIP으로 자동 압축)
- 다운로드 링크 복사
- 파일/폴더 검색 및 정렬 (이름, 날짜)
- 새 폴더 생성
- 파일 삭제 및 휴지통 (24시간 후 자동 영구 삭제, 복원 가능)
- 동일 파일명 업로드 시 덮어쓰기 / 자동 이름 변경 / 직접 입력 선택

### 📝 메모
- 메모 작성 / 수정 / 삭제
- 자동 저장 (2.5초 딜레이)
- 제목 및 내용 검색
- 10개씩 페이지네이션

### 공통
- 반응형 디자인 (모바일 지원)
- 경로 조작 방지 보안

## 주의사항

- 신뢰할 수 있는 네트워크에서만 사용하세요
- 중요한 파일은 공유하지 마세요
- 프로덕션 환경에서는 추가 보안 설정이 필요합니다
