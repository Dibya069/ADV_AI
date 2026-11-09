from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time

app = FastAPI()


@app.middleware("http")
async def measure_server_time(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = (time.perf_counter() - start) * 1000
    response.headers["X-Server-Processing-Ms"] = f"{elapsed:.3f}"

    return response


@app.get("/test")
async def test():
    start = time.perf_counter()

    time.sleep(0.1)

    processing_ms = (time.perf_counter() - start) * 1000

    return {
        "status": "success",
        "message": "Hello from server",
        "server_processing_ms": round(processing_ms, 3)
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}