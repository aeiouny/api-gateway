# ============================================================================
# MAIN APPLICATION FILE - API Gateway Entry Point
# ============================================================================
# This is the main FastAPI application that ties everything together:
# - Sets up the FastAPI app instance
# - Configures telemetry (OpenTelemetry)
# - Initializes rate limiting (Redis)
# - Defines all API endpoints
# ============================================================================

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
from app.stripe_payments import create_payment

# Load environment variables from .env file
# This allows us to configure the app without hardcoding secrets
load_dotenv()

# Create the FastAPI application instance
# This is the main object that handles all HTTP requests
app = FastAPI()

# Initialize OpenTelemetry for metrics and tracing
# This automatically instruments all HTTP requests to collect telemetry data
setup_telemetry(app)

# Get Redis URL from environment (defaults to localhost if not set)
# Redis is used for rate limiting - it stores request counts per user/IP
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ============================================================================
# APPLICATION LIFECYCLE EVENTS
# ============================================================================
# These functions run when the application starts and stops
# ============================================================================

@app.on_event("startup")
async def startup():
    """
    Runs once when the FastAPI application starts up.
    This is where we initialize connections to external services.
    """
    try:
        # Create async Redis connection
        # Redis is used to store rate limit counters (how many requests per time window)
        redis_conn = await redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        
        # Initialize FastAPI-Limiter with Redis connection
        # This enables rate limiting across all endpoints that use RateLimiter
        await FastAPILimiter.init(redis_conn)
        print(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        # If Redis connection fails, the app can't start (rate limiting won't work)
        print(f"Redis connection failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    """
    Runs once when the FastAPI application shuts down.
    This is where we clean up connections gracefully.
    """
    # Close the rate limiter connection to Redis
    # This ensures we don't leave hanging connections
    await FastAPILimiter.close()

# ============================================================================
# HEALTH & MONITORING ENDPOINTS
# ============================================================================
# These endpoints provide basic health checks and observability
# ============================================================================

@app.get("/")
async def get_root(request: Request, rate_limiter: RateLimiter = Depends(RateLimiter(times=5, seconds=60))):
    """
    Root endpoint - simple welcome message.
    
    Rate Limiting: 5 requests per 60 seconds
    - This prevents abuse of the root endpoint
    - RateLimiter is a FastAPI dependency that automatically checks Redis
    - If limit exceeded, returns HTTP 429 (Too Many Requests)
    """
    return {"message": "Main Page!"}

@app.get("/health")
async def get_health(request: Request):
    """
    Health check endpoint for monitoring tools (Kubernetes, load balancers, etc.)
    
    No rate limiting - health checks need to work even under load
    Returns simple status to indicate the API is running
    """
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

# ============================================================================
# AUTHENTICATION ENDPOINT
# ============================================================================
# Demonstrates Auth0 JWT token validation
# ============================================================================

@app.get("/api/v1/me")
async def get_user(user: dict = Depends(validate_token)):
    """
    Get current authenticated user information.
    
    Authentication: Requires valid Auth0 JWT token in Authorization header
    - validate_token dependency automatically:
      1. Extracts token from "Authorization: Bearer <token>" header
      2. Verifies token signature with Auth0's public keys
      3. Checks token expiration and audience
      4. Returns decoded token payload (user info) if valid
      5. Returns HTTP 401 if invalid/expired
    
    The 'user' dict contains JWT claims like:
    - sub: User ID (e.g., "auth0|123456")
    - email: User's email address
    - exp: Token expiration timestamp
    """
    return {
        "user_id": user.get("sub"),  # Auth0 user ID
        "email": user.get("email"),   # User's email from token
        "feature": "authentication"    # Indicates this uses auth feature
    }

# ============================================================================
# PAYMENT PROCESSING ENDPOINT
# ============================================================================
# Demonstrates Stripe payment integration with authentication
# ============================================================================

class PaymentRequest(BaseModel):
    """
    Pydantic model for payment request validation.
    
    FastAPI automatically validates incoming JSON against this model:
    - amount: Required integer (in cents, e.g., 2000 = $20.00)
    - currency: Optional string, defaults to "usd"
    - description: Optional string, defaults to empty
    """
    amount: int
    currency: str = "usd"
    description: str = ""

@app.post("/api/payments/create")
async def create_payment_endpoint(
    payment: PaymentRequest,
    user: dict = Depends(validate_token),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=20, seconds=60))
):
    """
    Create a Stripe payment intent.
    
    Authentication: Requires valid Auth0 JWT token (same as /api/v1/me)
    Rate Limiting: 20 requests per 60 seconds (higher limit than root endpoint)
    
    Flow:
    1. FastAPI validates request body against PaymentRequest model
    2. validate_token dependency verifies Auth0 JWT token
    3. Rate limiter checks if user exceeded 20 requests/minute
    4. If all checks pass, create Stripe payment intent
    5. Return payment intent details to client
    
    The client_secret is used by frontend to complete payment with Stripe.js
    """
    # Call Stripe API to create payment intent
    # This is an async call to Stripe's API
    payment_intent = await create_payment(
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description
    )
    
    # Return payment intent details
    # client_secret is used by frontend to confirm payment with Stripe
    return {
        "payment_id": payment_intent.id,
        "client_secret": payment_intent.client_secret,
        "amount": payment_intent.amount,
        "status": payment_intent.status,
        "feature": "stripe_payments"
    }
