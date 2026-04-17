# Xing API DLL 파일 배치 안내

이 디렉토리에 LS증권(eBest) xingAPI 프로그램의 DLL 파일을 배치하세요.

## 다운로드

1. [LS증권 OpenAPI](https://openapi.ls-sec.co.kr/) 접속
2. xingAPI 프로그램 다운로드 (Windows 전용)
3. 설치 후 설치 폴더의 파일들을 이 디렉토리에 복사

## 필수 파일 목록

```
XA_Common.dll
XA_DataSet.dll
XA_Session.dll
XingAPI.dll
mfc100d.dll
msvcr100d.dll
msvcp100d.dll
mfc100.dll
msvcr100.dll
msvcp100.dll
atl100.dll
XecureS.dll
SKComdCM.dll / SKComdEM.dll / SKComdIF.dll / SKComdSC.dll
SKCommCM.dll / SKCommEM.dll / SKCommIC.dll / SKCommIF.dll / SKCommSC.dll
inicore_v*.dll / inicrypto_v*.dll / inipki_v*.dll / inisafenet_v*.dll
hkdnsres.dll
enmsgoem.dll
nsldap32v11.dll
xingAPI.ini
glb_oem.ini
res/t8412.res
```

> ⚠️ 이 파일들은 LS증권 저작물이므로 Git에 커밋하지 마세요.
