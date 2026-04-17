# xing-docker

> Xing API (eBest/LS증권)를 macOS/Linux에서 Docker + Wine으로 실행하는 컨테이너

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 왜 필요한가?

Xing API는 **Windows 32비트 COM 객체** 기반이라 macOS/Linux에서 직접 실행할 수 없습니다.
이 프로젝트는 Docker 컨테이너 안에서 **Wine + Windows Python 3.8**을 구동하여,
REST API로 Xing API의 TR 데이터를 제공합니다.

### 지원 기능

- `t8412` TR — 과거 분봉(1분/5분/10분 등) 데이터 조회
- 모의투자 / 실투자 서버 전환
- FastAPI 기반 REST API (Swagger UI: `http://localhost:8000/docs`)

## 빠른 시작

### 1. Xing API DLL 준비

> ⚠️ Xing API DLL은 LS증권 저작물이므로 이 레포에 포함되어 있지 않습니다.

[LS증권 OpenAPI](https://openapi.ls-sec.co.kr/) 또는 eBest에서 **xingAPI 프로그램**을 다운로드하고,
`xing_api_files/` 디렉토리에 아래 파일들을 배치하세요:

```
xing_api_files/
├── XA_Common.dll          # 필수
├── XA_DataSet.dll         # 필수
├── XA_Session.dll         # 필수
├── XingAPI.dll            # 필수
├── mfc100d.dll            # VC++ 2010 디버그 런타임
├── msvcr100d.dll          # VC++ 2010 디버그 런타임
├── msvcp100d.dll          # VC++ 2010 디버그 런타임
├── mfc100.dll             # VC++ 2010 릴리스 런타임
├── msvcr100.dll           # VC++ 2010 릴리스 런타임
├── msvcp100.dll           # VC++ 2010 릴리스 런타임
├── atl100.dll             # ATL 런타임
├── XecureS.dll            # 보안 모듈
├── SKComm*.dll / SKComd*.dll  # 통신 모듈
├── ini*.dll               # 인증서 모듈
├── hkdnsres.dll           # DNS 모듈
├── enmsgoem.dll           # 메시지 모듈
├── nsldap32v11.dll        # LDAP 모듈
├── xingAPI.ini            # API 설정
├── glb_oem.ini            # OEM 설정
└── res/
    └── t8412.res          # t8412 TR 리소스 파일
```

> 💡 xingAPI 설치 폴더에서 위 파일들을 통째로 복사하면 가장 확실합니다.

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열고 LS증권 계정 정보를 입력하세요:

```env
XING_USER_ID=your_id
XING_USER_PWD='your_password'    # 특수문자 포함 시 싱글쿼트
XING_CERT_PWD='your_cert_pwd'
XING_SERVER_TYPE=demo             # demo: 모의투자, real: 실투자
```

### 3. 실행

```bash
docker compose up -d --build
```

### 4. 확인

```bash
# 헬스 체크 (connected: true 확인)
curl http://localhost:8000/health

# 삼성전자 분봉 조회 (예시)
curl "http://localhost:8000/api/intraday/005930?date=2026-04-01"
```

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 및 Xing API 연결 여부 |
| GET | `/api/intraday/{ticker}?date=YYYY-MM-DD&count=500` | t8412 분봉 데이터 조회 |
| GET | `/docs` | Swagger UI (자동 생성) |

### 응답 예시

```json
{
  "ticker": "005930",
  "date": "2026-04-01",
  "count": 380,
  "intraday": [
    {"time": "09:01", "open": 67000, "high": 67100, "low": 66900, "close": 67000, "volume": 125000},
    {"time": "09:02", "open": 67000, "high": 67200, "low": 67000, "close": 67100, "volume": 98000},
    ...
  ]
}
```

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  Docker (linux/386, QEMU 에뮬레이션)                │
│  ┌───────────────────────────────────────────────┐   │
│  │  Wine + Windows Python 3.8 (32-bit)          │   │
│  │  ┌─────────────────────────────────────┐      │   │
│  │  │  FastAPI (uvicorn :8000)            │      │   │
│  │  │  └─ win32com.client                 │      │   │
│  │  │     └─ XA_Session / XA_DataSet COM  │      │   │
│  │  │        └─ t8412 TR (분봉 조회)      │      │   │
│  │  └─────────────────────────────────────┘      │   │
│  └───────────────────────────────────────────────┘   │
│  Xvfb :99 (가상 디스플레이)                          │
└─────────────────────────────────────────────────────┘
```

## 삽질 기록 (Troubleshooting)

이 프로젝트를 만들면서 겪은 모든 에러와 해결 방법입니다.

| 에러 | 원인 | 해결 |
|------|------|------|
| `pyxing` 패키지 사용 불가 | 리눅스 Python은 Windows COM 통신 불가 | Wine 위에 Windows Python 설치 + `pypiwin32`로 직접 COM 호출 |
| `xvfb-run: Xvfb failed to start` | i386 환경에서 xvfb-run 불안정 | `with-xvfb` 헬퍼 스크립트로 Xvfb 직접 관리 |
| `Server is already active for display 99` | Docker RUN 레이어 간 lock 파일 잔류 | 헬퍼에 `rm -f /tmp/.X99-lock` 추가 |
| `mfc100d.dll not found` | Xing DLL이 VC++2010 디버그 런타임 의존 | xingAPI 설치 폴더에서 런타임 DLL 복사 |
| COM Error `0x800401f3` (런타임) | 빌드 시 regsvr32 등록이 런타임에 미적용 | CMD에서 서버 시작 전 `regsvr32` 재실행 |
| 한글 환경변수 깨짐 | Wine Python의 cp1252 인코딩 | 환경변수 영문화 + `sys.stdout.reconfigure(encoding='utf-8')` |
| wget SSL 실패 | CA 인증서 번들 없음 | `ca-certificates` 패키지 + `--no-check-certificate` |

## 요구사항

- Docker Desktop (Apple Silicon 맥의 경우 QEMU i386 에뮬레이션 사용)
- LS증권(eBest) 계정 (모의투자 가능)
- xingAPI 프로그램에서 추출한 DLL 파일들

## 라이선스

MIT License

> **주의**: 이 프로젝트는 Xing API DLL을 포함하지 않습니다.
> Xing API는 LS증권의 저작물이며, 사용 시 LS증권의 이용약관을 준수해야 합니다.
