import os
import redis.asyncio as aioredis
from fastapi import FastAPI, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter


app = FastAPI(
    title="API Gateway",
)

@app.on_event("startup")
async def startup():
    r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"),
                          encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(r)

token_scheme = HTTPBearer()

@app.get("/")
def get_root():
    return {"message": "API Gateway is running"}


@app.get("/health")
def get_health():
    return {"status": "ok"}

@app.get("/secure", dependencies=[Depends(RateLimiter(times=60, seconds=60))])
def secure():
    return {"message": "secure route ok"}

from fastapi import Body, Depends
from fastapi_limiter.depends import RateLimiter

@app.get("/users/profile", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
def users_profile():
    return {"profile": {"name": "Demo User"}}

@app.post("/payments/charge", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def payments_charge(payload: dict = Body(...)):
    return { "amount": 1000, "currency": "USD"}

