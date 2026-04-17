import os
import sys
import time
import threading

# Wine/Windows Python의 cp1252 인코딩 문제 방지
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import uvicorn
from fastapi import FastAPI, HTTPException

# 환경변수 (docker-compose에서 주입)
XING_USER_ID = os.environ.get("XING_USER_ID", "")
XING_USER_PWD = os.environ.get("XING_USER_PWD", "")
XING_CERT_PWD = os.environ.get("XING_CERT_PWD", "")
XING_SERVER_TYPE = os.environ.get("XING_SERVER_TYPE", "demo")

app = FastAPI(title="Xing Data Shuttle")

# COM 객체는 Wine 환경에서 win32com으로 직접 호출
session = None
is_connected = False

def xing_login():
    """Xing API COM 세션 로그인"""
    global session, is_connected
    try:
        import win32com.client
        
        session = win32com.client.Dispatch("XA_Session.XASession")
        
        # 서버 연결
        server = "demo.ebestsec.co.kr" if XING_SERVER_TYPE == "demo" else "hts.ebestsec.co.kr"
        session.ConnectServer(server, 20001)
        
        # 로그인
        session.Login(XING_USER_ID, XING_USER_PWD, XING_CERT_PWD, 0, False)
        time.sleep(5)  # 로그인 응답 대기
        
        is_connected = session.IsConnected()
        print(f"Xing 로그인 {'성공' if is_connected else '실패'} (서버: {server})")
        
    except Exception as e:
        print(f"Xing 초기화 에러: {e}")

@app.on_event("startup")
async def startup_event():
    print("=== Xing Data Shuttle Starting ===")
    print(f"ID: {XING_USER_ID}, Server: {XING_SERVER_TYPE}")
    xing_login()

@app.get("/health")
def health_check():
    return {"status": "ok", "connected": is_connected}

@app.get("/api/intraday/{ticker}")
def get_intraday(ticker: str, date: str, count: int = 500):
    """t8412 TR: 특정 날짜의 분봉 데이터 조회"""
    global session
    
    if not is_connected:
        raise HTTPException(status_code=503, detail="Xing API not connected")
    
    clean_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    date_raw = date.replace("-", "")
    
    try:
        import win32com.client
        query = win32com.client.Dispatch("XA_DataSet.XAQuery")
        query.ResFileName = "/app/xing/Res/t8412.res"
        
        query.SetFieldData("t8412InBlock", "shcode", 0, clean_ticker)
        query.SetFieldData("t8412InBlock", "ncnt", 0, 1)       # 1분봉
        query.SetFieldData("t8412InBlock", "qrycnt", 0, count)
        query.SetFieldData("t8412InBlock", "nday", 0, "0")
        query.SetFieldData("t8412InBlock", "sdate", 0, date_raw)
        query.SetFieldData("t8412InBlock", "edate", 0, date_raw)
        query.SetFieldData("t8412InBlock", "comp_yn", 0, "N")
        
        query.Request(False)
        time.sleep(1)  # TR 응답 대기
        
        cnt = query.GetBlockCount("t8412OutBlock1")
        ticks = []
        
        for i in range(cnt):
            t_date = query.GetFieldData("t8412OutBlock1", "date", i)
            t_time = query.GetFieldData("t8412OutBlock1", "time", i)
            
            if t_date != date_raw:
                continue
            
            formatted_time = f"{t_time[0:2]}:{t_time[2:4]}" if len(t_time) >= 4 else t_time
            
            ticks.append({
                "time": formatted_time,
                "open": int(query.GetFieldData("t8412OutBlock1", "open", i)),
                "high": int(query.GetFieldData("t8412OutBlock1", "high", i)),
                "low": int(query.GetFieldData("t8412OutBlock1", "low", i)),
                "close": int(query.GetFieldData("t8412OutBlock1", "close", i)),
                "volume": int(query.GetFieldData("t8412OutBlock1", "jdiff_vol", i))
            })
        
        ticks.sort(key=lambda x: x["time"])
        
        return {"ticker": ticker, "date": date, "count": len(ticks), "intraday": ticks}
        
    except Exception as e:
        print(f"t8412 TR 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
