import httpx
import os
from jose import jwt, jwk
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
JWKS_URL = f'https://{AUTH0_DOMAIN}/.well-known/jwks.json'
AUTH0_ISSUER = f'https://{AUTH0_DOMAIN}/'

cached_keys = None

bearer = HTTPBearer()

async def get_public_keys():
    global cached_keys
    
    if cached_keys is not None:
        return cached_keys
    
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        response.raise_for_status()
        jwks_data = response.json()
    
    cached_keys = {key['kid']: key for key in jwks_data['keys']}
    return cached_keys

async def validate_token(token: HTTPAuthorizationCredentials = Depends(bearer)):
    # Gets raw token string from "Bearer <token>"
    token_string = token.credentials
    
    # Read token header to get key id 
    # (key id grabs the right public key to use)
    header = jwt.get_unverified_header(token_string)
    key_id = header.get('kid')
    
    if not key_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing key ID")
    
    # Get public key from Auth0 JWKS using key id
    keys = await get_public_keys()
    matching_key = keys.get(key_id)
    
    if not matching_key:
        raise HTTPException(status_code=401, detail="Invalid token: key not found")
    
    # Build the public key
    public_key = jwk.construct(matching_key)
    
    # Verify and decode the token
    try:
        payload = jwt.decode(
            token_string,
            public_key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER
        )
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
