from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app=FastAPI()

# --- 카운터 ---

total_requests = Counter(
    'http_requests',
    'Total numbers of requests',
    ['method', 'path', 'status']
)

# --- 미들웨어 ---

@app.middleware("http")
async def count_request(request : Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    response = await call_next(request)

    total_requests.labels(
        method = request.method,
        path = request.url.path,
        status = str(response.status_code)
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
# 프로메테우스가 긁어가는 곳 (localhost:8000/metrics)
# json 말고 텍스트로 줘야 읽음!
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
