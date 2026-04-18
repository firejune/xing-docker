import os
import sys
import time
import queue
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

# COM 쓰레드 관련 — Windows COM은 단일 쓰레드에서만 안전
com_queue = queue.Queue()
is_connected = False
login_done = False


class XASessionEventHandler:
    """XASession 이벤트 핸들러 — OnLogin 콜백 수신"""
    def OnLogin(self, code, msg):
        global login_done
        login_done = True
        print(f"[세션] OnLogin 이벤트: code={code}, msg={msg}", flush=True)

    def OnDisconnect(self):
        global is_connected
        is_connected = False
        print("[세션] OnDisconnect 이벤트", flush=True)


def com_worker():
    """단일 쓰레드에서 모든 COM 작업 처리 (STA 모델 + 메시지 펌프)"""
    global is_connected, login_done

    import pythoncom
    pythoncom.CoInitialize()

    import win32com.client

    session = None

    # 로그인 — DispatchWithEvents로 OnLogin 이벤트 수신
    try:
        session = win32com.client.DispatchWithEvents("XA_Session.XASession", XASessionEventHandler)
        server = "demo.ebestsec.co.kr" if XING_SERVER_TYPE == "demo" else "hts.ebestsec.co.kr"
        session.ConnectServer(server, 20001)
        session.Login(XING_USER_ID, XING_USER_PWD, XING_CERT_PWD, 0, False)

        # OnLogin 이벤트 대기 (메시지 펌핑, 최대 30초)
        for i in range(300):
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
            if login_done:
                break

        is_connected = session.IsConnected()
        print(f"Xing 로그인 {'성공' if is_connected else '실패'} (서버: {server}, login_done={login_done})", flush=True)

        if not login_done:
            print("[세션] 경고: OnLogin 이벤트를 수신하지 못함 — TR 조회가 실패할 수 있음", flush=True)

    except Exception as e:
        print(f"Xing 초기화 에러: {e}", flush=True)
        import traceback
        traceback.print_exc()

    # 큐에서 작업 대기 및 처리
    while True:
        try:
            try:
                task = com_queue.get(timeout=0.1)
            except queue.Empty:
                pythoncom.PumpWaitingMessages()
                continue

            func, args, result_q = task
            try:
                result = func(win32com, pythoncom, *args)
                result_q.put(("ok", result))
            except Exception as e:
                import traceback
                err_msg = f"{type(e).__name__}: {repr(e)}"
                print(f"[COM 워커] 에러: {err_msg}", flush=True)
                sys.stderr.write(f"[COM 워커] 에러: {err_msg}\n")
                sys.stderr.flush()
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                result_q.put(("error", err_msg))
        except Exception as e:
            print(f"COM 워커 에러: {repr(e)}", flush=True)


def com_call(func, *args, timeout=30):
    """COM 쓰레드에 작업 위임 후 결과 대기"""
    result_q = queue.Queue()
    com_queue.put((func, args, result_q))
    status, result = result_q.get(timeout=timeout)
    if status == "error":
        raise Exception(result)
    return result


# ─── COM 작업 함수들 (com_worker 쓰레드 내에서 실행됨) ───

def _query_t8412(win32com, pythoncom, ticker, date_raw, count):
    """t8412 TR: 분봉 조회 (COM 쓰레드, 동기 Request + 메시지 펌프 폴링)"""
    print(f"[t8412] _query_t8412 진입: {ticker} / {date_raw}", flush=True)
    sys.stderr.write(f"[t8412] _query_t8412 진입: {ticker} / {date_raw}\n")
    sys.stderr.flush()
    
    try:
        query = win32com.client.Dispatch("XA_DataSet.XAQuery")
        print(f"[t8412] Dispatch 성공: {query}", flush=True)
    except Exception as e:
        msg = f"Dispatch 실패: {type(e).__name__}: {repr(e)}"
        print(f"[t8412] {msg}", flush=True)
        sys.stderr.write(f"[t8412] {msg}\n")
        sys.stderr.flush()
        raise

    res_path = "Z:\\app\\xing\\res\\t8412.res"
    try:
        query.ResFileName = res_path
        print(f"[t8412] ResFileName 설정 OK: {res_path}", flush=True)
    except Exception as e:
        msg = f"ResFileName 설정 실패: {type(e).__name__}: {repr(e)}"
        print(f"[t8412] {msg}", flush=True)
        sys.stderr.write(f"[t8412] {msg}\n")
        sys.stderr.flush()
        raise

    query.SetFieldData("t8412InBlock", "shcode", 0, ticker)
    query.SetFieldData("t8412InBlock", "ncnt", 0, "1")       # 1분봉 (문자열)
    query.SetFieldData("t8412InBlock", "qrycnt", 0, str(count))
    query.SetFieldData("t8412InBlock", "nday", 0, "0")
    query.SetFieldData("t8412InBlock", "sdate", 0, date_raw)
    query.SetFieldData("t8412InBlock", "edate", 0, date_raw)
    query.SetFieldData("t8412InBlock", "comp_yn", 0, "N")

    print(f"[t8412] SetFieldData 완료, 요청: {ticker} / {date_raw} / {count}건", flush=True)

    # Request(False) = 최초 조회 (True는 연속조회=다음 페이지)
    ret = query.Request(False)
    print(f"[t8412] Request(False) 반환: {ret}", flush=True)

    if ret < 0:
        # GetLastError로 상세 에러 확인 시도
        try:
            err_code = query.GetLastError()
            print(f"[t8412] GetLastError: {err_code}", flush=True)
        except:
            pass
        # 세션에서도 에러 확인
        try:
            import win32com.client as wc
            sess = wc.Dispatch("XA_Session.XASession")
            err_msg = sess.GetLastError()
            print(f"[t8412] Session.GetLastError: {err_msg}", flush=True)
        except:
            pass
        raise Exception(f"t8412 Request 실패: 코드 {ret}")

    # 비동기 응답 대기 — 메시지 펌프 돌려서 COM 이벤트 처리
    for i in range(100):
        pythoncom.PumpWaitingMessages()
        time.sleep(0.1)

    # 메시지 펌프 몇 번 더 돌려서 안정화
    for _ in range(30):
        pythoncom.PumpWaitingMessages()
        time.sleep(0.1)

    cnt = query.GetBlockCount("t8412OutBlock1")
    print(f"[t8412] 수신 건수: {cnt}", flush=True)

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
    print(f"[t8412] 파싱 완료: {len(ticks)}개 틱", flush=True)
    return ticks


# ─── FastAPI 엔드포인트 ───

@app.on_event("startup")
async def startup_event():
    print("=== Xing Data Shuttle Starting ===", flush=True)
    print(f"ID: {XING_USER_ID}, Server: {XING_SERVER_TYPE}", flush=True)
    t = threading.Thread(target=com_worker, daemon=True)
    t.start()
    time.sleep(8)


@app.get("/health")
def health_check():
    return {"status": "ok", "connected": is_connected}


@app.get("/api/intraday/{ticker}")
def get_intraday(ticker: str, date: str, count: int = 500):
    """t8412 TR: 특정 날짜의 분봉 데이터 조회"""
    if not is_connected:
        raise HTTPException(status_code=503, detail="Xing API not connected")

    clean_ticker = ticker.split('.')[0] if '.' in ticker else ticker
    date_raw = date.replace("-", "")

    try:
        ticks = com_call(_query_t8412, clean_ticker, date_raw, count)
        return {"ticker": ticker, "date": date, "count": len(ticks), "intraday": ticks}
    except Exception as e:
        print(f"t8412 TR 에러: {e}", flush=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
