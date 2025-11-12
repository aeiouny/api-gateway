import os
import redis.asyncio as redis
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from dotenv import load_dotenv
from auth import validate_token
from telemetry import setup_telemetry, get_metrics
from fastapi.responses import Response

load_dotenv()
app = FastAPI(
    title="API Gateway",
    description="API gateway with rate limiting and observability."
)

setup_telemetry(app)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Connects to Redis when server starts.
@app.on_event("startup")
async def startup():
    try:
        redis_conn = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_conn)
        print(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        raise

# Closes Redis connection when server stops.
@app.on_event("shutdown")
async def shutdown():
    await FastAPILimiter.close()

@app.get("/")
async def get_root(request: Request, rate_limiter: RateLimiter = Depends(RateLimiter(times=5, seconds=60))):
    return {"message": "Main Page!"}

# Kubernetes health check endpoint.
@app.get("/health")
async def get_health(request: Request):
    return {"status": "ok", "message": "Gateway is running"}

@app.get("/metrics")
async def metrics_endpoint():
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4")

# Test auth0 endpoint.
@app.get("/api/v1/me")
async def get_user(user: dict = Depends(validate_token)):
    """
    Protected endpoint, requires valid token for access.
    """
    return {
        "message": "This is Auth0-protected endpoint.",
        "user_id": user.get("sub"),
        "token_info": user
    }

@app.get("/secure")
async def get_secure_data(
    user: dict = Depends(validate_token),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=10, seconds=60))
):
    return {
        "message": "This is secure data!",
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "authenticated": True
    }
