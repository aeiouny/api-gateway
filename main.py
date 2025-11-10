from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


limiter = Limiter(key_func=get_remote_address)


app = FastAPI(
    title="API Gateway",
    description="API gateway."
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

token_scheme = HTTPBearer()

@app.get("/")
@limiter.limit("5/minute")  
async def get_root(request: Request):
    return {"message": "Main Page!"}


@app.get("/health")
async def get_health(request: Request):
    return {"status": "ok", "message": "Gateway is running"}

@app.get("/secure")
async def get_secure_data(token: HTTPAuthorizationCredentials = Depends(token_scheme)):
    return {
        "message": "This is secure data!",
        "your_token_was": token.credentials
    }