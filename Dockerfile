# 1. Wine이 설치된 베이스 이미지 사용 (32비트 지원 필수)
FROM i386/ubuntu:20.04

# 환경변수 세팅
ENV DEBIAN_FRONTEND=noninteractive
ENV WINEARCH=win32
ENV WINEPREFIX=/root/.wine
ENV WINEDEBUG=-all
ENV DISPLAY=:99

# 2. 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    wine \
    xvfb \
    wget \
    ca-certificates \
    && apt-get clean

# 헬퍼: Xvfb 시작 후 wine 명령 실행 (xvfb-run이 i386에서 불안정)
RUN printf '#!/bin/sh\nrm -f /tmp/.X99-lock\nXvfb :99 -screen 0 1024x768x16 &\nsleep 1\nexec "$@"\n' > /usr/local/bin/with-xvfb && \
    chmod +x /usr/local/bin/with-xvfb

# 3. Wine prefix 초기화 (후속 wine 호출의 안정성 확보)
RUN with-xvfb wineboot --init && wineserver --wait

# 4. Windows 32비트용 Python 3.8.10 무인(Silent) 설치
RUN wget --no-check-certificate https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe && \
    with-xvfb wine python-3.8.10.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 && \
    wineserver --wait && \
    rm python-3.8.10.exe

# 5. Xing API DLL 복사 및 COM 등록
COPY ./xing_api_files /app/xing
WORKDIR /app
RUN with-xvfb wine regsvr32 /s /app/xing/XA_DataSet.dll && \
    with-xvfb wine regsvr32 /s /app/xing/XA_Session.dll || true

# 6. 의존성 설치 (Wine 윈도우 파이썬의 pip 사용)
COPY ./requirements.txt /app/requirements.txt
RUN with-xvfb wine python -m pip install --upgrade pip \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org && \
    wineserver --wait
RUN with-xvfb wine python -m pip install pypiwin32 \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org && \
    wineserver --wait
RUN with-xvfb wine python -m pip install --no-cache-dir -r requirements.txt \
        --trusted-host pypi.org --trusted-host files.pythonhosted.org && \
    wineserver --wait

# 7. 소스 코드 복사
COPY . /app
EXPOSE 8000

# 8. Xvfb 가상 디스플레이 + COM 등록 + uvicorn 실행
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x16 & sleep 1 && wine regsvr32 /s /app/xing/XA_DataSet.dll && wine regsvr32 /s /app/xing/XA_Session.dll && wine python -m uvicorn main:app --host 0.0.0.0 --port 8000"]