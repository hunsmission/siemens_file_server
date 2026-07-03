# 파일 서버 for Siemens Project

Siemens에서 Project 수행을 위한 깔끔한 UI를 가진 간단한 파일 공유 서버입니다.

## 설치 방법

1. Python 설치 (Python 3.7 이상)

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

## 사용 방법

1. `file_server.py` 파일을 열어서 공유할 폴더 경로를 수정:
```python
FILE_DIRECTORY = r"D:\FileShare"  # 원하는 경로로 변경
```

2. 서버 실행:
```bash
python file_server.py
```

3. 브라우저에서 접속:
   - 같은 PC: http://localhost:8000
   - 다른 PC: http://<이_PC의_IP>:8000

## IP 주소 확인 방법

Windows에서 명령 프롬프트를 열고:
```bash
ipconfig
```

"IPv4 주소" 항목을 확인하세요 (예: 192.168.0.10)

## 방화벽 설정

다른 PC에서 접속이 안 되면 Windows 방화벽에서 포트 8181 열어야 합니다:
1. Windows 방화벽 설정 열기
2. 고급 설정 → 인바운드 규칙 → 새 규칙
3. 포트 → TCP → 특정 로컬 포트: 8181
4. 연결 허용 → 다음 → 이름: "Flask File Server"

## 기능

- ✨ 깔끔한 UI
- 🔍 파일 검색
- 📥 파일 다운로드
- 📱 반응형 디자인 (모바일 지원)
- 🔒 경로 조작 방지 보안

## 주의사항

- 신뢰할 수 있는 네트워크에서만 사용하세요
- 중요한 파일은 공유하지 마세요
- 프로덕션 환경에서는 추가 보안 설정이 필요합니다
