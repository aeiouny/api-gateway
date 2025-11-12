import os
import redis.asyncio as redis
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

app = FastAPI(
    title="API Gateway",
    description="API gateway with rate limiting."
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
token_scheme = HTTPBearer()

# Connects to Redis when server starts.
@app.on_event("startup")
async def startup():
    try:
        redis_connection = await redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        await FastAPILimiter.init(redis_connection)
        
        print(f"✅ Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("\n💡 Make sure Redis is running:")
        print("   Local: docker-compose up -d")
        print("   Or: redis-server")
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
    """
    Kubernetes.
    """
    return {"status": "ok", "message": "Gateway is running"}

# Showcase metrics endpoint.
@app.get("/metrics")
async def get_metrics():
    """
    Prometheus / OpenTelemetry.
    """
    return {"metrics": "metrics"}

# Test auth0 endpoint.
@app.get("/api/v1/me")
async def get_user():
    """
    Auth0-protected endpoint.
    """
    return {
        "message": "This is Auth0-protected endpoint.",
        "users": "test user"
    }

# Test strip payment endpoint.
@app.get("/secure")
async def get_secure_data(
    token: HTTPAuthorizationCredentials = Depends(token_scheme),
    # Add rate limiting: 10 requests per 60 seconds
    rate_limiter: RateLimiter = Depends(RateLimiter(times=10, seconds=60))
):
    """
    Secure endpoint with authentication AND rate limiting.
    - Requires valid token (authentication)
    - Limits to 10 requests per minute (rate limiting)
    """
    return {
        "message": "This is secure data!",
        "your_token_was": token.credentials
    }
