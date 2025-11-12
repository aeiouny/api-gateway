import os
import redis.asyncio as redis
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from dotenv import load_dotenv
from pydantic import BaseModel
from app.auth import validate_token
from app.telemetry import setup_telemetry, get_metrics
from app.router import forward_request, get_backend_url, ROUTES
from app.stripe_payments import create_payment

load_dotenv()

app = FastAPI(title="API Gateway", description="API gateway with rate limiting and observability")
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
async def get_root(request: Request, rate_limiter: RateLimiter = Depends(RateLimiter(times=5, seconds=60))):
    return {"message": "Main Page!"}

@app.get("/health")
async def get_health(request: Request):
    return {"status": "ok"}

@app.get("/metrics")
async def metrics_endpoint():
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type="text/plain; version=0.0.4")

@app.get("/api/v1/me")
async def get_user(user: dict = Depends(validate_token)):
    return {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "feature": "authentication"
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

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    full_path = f"/{path}"
    backend_url = get_backend_url(full_path)
    
    if backend_url is None:
        return JSONResponse(status_code=404, content={"error": "Route not found", "path": full_path})
    
    route_prefix = None
    for route in ROUTES.keys():
        if full_path.startswith(route):
            route_prefix = route
            break
    
    return await forward_request(request, backend_url, route_prefix)
