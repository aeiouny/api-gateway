import os
import redis.asyncio as redis
from fastapi import FastAPI, Request, Depends
from fastapi.responses import Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from dotenv import load_dotenv
from pydantic import BaseModel
from app.auth import validate_token
from app.telemetry import setup_telemetry, get_metrics
from app.stripe_payments import create_payment

load_dotenv()
app = FastAPI()
setup_telemetry(app)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

@app.on_event("startup")
async def startup():
    try:
        redis_conn = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        
        await FastAPILimiter.init(redis_conn)
        print(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    await FastAPILimiter.close()

@app.get("/")
async def get_root(rate_limiter: RateLimiter = Depends(RateLimiter(times=5, seconds=60))):
    return {"message": "Main Page!"}

@app.get("/health")
async def get_health(request: Request):
    return {"status": "ok"}

@app.get("/metrics")
async def metrics_endpoint(request: Request):
    """
    Prometheus metrics endpoint - exposes OpenTelemetry metrics in Prometheus format.
    
    This endpoint is scraped by Prometheus (or other monitoring tools) to collect:
    - HTTP request counts, durations, status codes
    - System metrics (memory, CPU)
    - Active request counts
    
    Returns raw Prometheus format (text/plain) - no formatting needed
    """
    # Get metrics from OpenTelemetry PrometheusMetricReader
    metrics_data = get_metrics()
    # Return with Prometheus content type
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4")

@app.get("/api/v1/me")
async def get_user(user: dict = Depends(validate_token)):
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "message": "User authenticated"
    }

class PaymentRequest(BaseModel):
    amount: int
    currency: str = "usd"
    description: str = ""

@app.post("/api/payments/create")
async def create_payment_endpoint(
    payment: PaymentRequest,
    user: dict = Depends(validate_token),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=20, seconds=60))
):

    payment_intent = await create_payment(
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description
    )
    
    return {
        "payment_id": payment_intent.id,
        "client_secret": payment_intent.client_secret,
        "amount": payment_intent.amount,
        "status": payment_intent.status,
        "feature": "stripe_payments"
    }

