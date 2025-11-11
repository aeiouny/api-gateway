from datetime import datetime, timedelta
from jose import jwt, JWTError
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

SECRET_KEY = 'supersecret'
ALGORITHM = "HS256"

token_scheme = HTTPBearer()

def create_token(user_id: str):
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def validate_token(token: HTTPAuthorizationCredentials = Depends(token_scheme)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status=401, detail="Invalid or expired token")