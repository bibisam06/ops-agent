from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import time

app=FastAPI()

# --- 카운터 ---

total_requests = Counter(
    'http_requests',
    'Total numbers of requests',
    ['method', 'path', 'status']
)

# --- 미들웨어 ---
# 처리 안 된 예외가 나면 call_next가 응답 대신 예외를 던지므로
# try/except로 잡아서 500으로 카운트한다.

@app.middleware("http")
async def count_request(request : Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)

    total_requests.labels(
        method = request.method,
        path = request.url.path,
        status = str(status)
    ).inc()

    return response


# --- 기본 엔드포인트 ---
@app.get("/")
async def root():
    return {"message" : "hello world"}

@app.get("/health")
async def health():
    return {"status" : "ok"}


# --- /metrics ---

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- /chaos ---

# CPU: async가 아닌 def로 써야 스레드풀에서 돌아서 이벤트 루프(/metrics)가 안 막힘
@app.get("/chaos/cpu")
def chaos_cpu(seconds: int = 10):
    end = time.time() + seconds
    x = 0
    while time.time() < end:
        x += 1
    return {"burned_seconds": seconds}


# 메모리 누수: 전역 리스트에 계속 쌓아서 GC가 회수 못 하게 함
_leak = []

@app.get("/chaos/memleak")
def chaos_memleak(mb: int = 50):
    _leak.append("x" * (mb * 1024 * 1024))
    return {"leaked_chunks": len(_leak), "leaked_mb_total": len(_leak) * mb}

@app.get("/chaos/memleak/reset")
def chaos_memleak_reset():
    _leak.clear()
    return {"leaked_chunks": 0}


# 에러: 처리 안 된 예외 → 미들웨어에서 500으로 집계
@app.get("/chaos/errors")
async def chaos_errors():
    raise RuntimeError("chaos!")
