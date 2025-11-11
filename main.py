import os
import redis.asyncio as aioredis
from fastapi import FastAPI, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from auth import create_token, validate_token

app = FastAPI(
    title="API Gateway",
)

@app.on_event("startup")
async def startup():
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"),
                          encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(r)

@app.get("/dev/token")
def get_dev_token():
    return {"token": create_token("user123")}

@app.get("/")
def get_root():
    return {"message": "API Gateway is running"}

@app.get("/health")
def get_health():
    return {"status": "ok"}

@app.get("/auth/check")
def secure(payload: dict = Depends(validate_token)):
    return {"valid": True, "user": payload["sub"]}

@app.get("/secure", dependencies=[Depends(validate_token), Depends(RateLimiter(times=60, seconds=60))])
def secure():
    return {"message": "This is a secure message"}

@app.get("/users/profile", dependencies=[Depends(validate_token), Depends(RateLimiter(times=100, seconds=60))])
def users_profile(payload: dict = Depends(validate_token)):
    return {"user": payload["sub"], "profile": {"name": "Demo User"}}

@app.post("/payments/charge", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def payments_charge():
    return { "amount": 1000, "currency": "USD"}
