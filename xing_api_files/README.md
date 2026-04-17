# Xing API 파일 배치 안내

이 디렉토리에 LS증권(eBest) xingAPI 프로그램의 파일을 배치하세요.

## 다운로드

1. [LS증권 OpenAPI](https://openapi.ls-sec.co.kr/) 접속
2. xingAPI 프로그램 다운로드 (Windows 전용)
3. 설치 후 **설치 폴더 전체를 이 디렉토리에 복사**하는 것을 권장

## 필수 파일 목록

```
# 핵심 COM DLL
XA_Common.dll
XA_DataSet.dll
XA_Session.dll
XingAPI.dll

# VC++ 런타임 (디버그 + 릴리스)
mfc100d.dll / mfc100.dll
msvcr100d.dll / msvcr100.dll
msvcp100d.dll / msvcp100.dll
atl100.dll

# 통신/보안 모듈
XecureS.dll
SKComd*.dll / SKComm*.dll
ini*.dll
hkdnsres.dll / enmsgoem.dll / nsldap32v11.dll

# 설정
xingAPI.ini / glb_oem.ini

# TR 리소스 파일 (사용할 TR에 따라 선택)
res/t8412.res    ← 분봉 조회
res/t1102.res    ← 현재가 조회 (필요 시)
res/...          ← 기타 필요한 TR
```

> 💡 `res/` 폴더에는 사용할 TR의 `.res` 파일만 넣으면 됩니다.
> xingAPI 설치 폴더의 `Res/` 디렉토리에서 복사하세요.

> ⚠️ 모든 파일은 LS증권 저작물이므로 Git에 커밋하지 마세요.

