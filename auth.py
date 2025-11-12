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
ALGORITHMS = ["RS256"]
JWKS_URL = f'https://{AUTH0_DOMAIN}/.well-known/jwks.json'
AUTH0_ISSUER = f'https://{AUTH0_DOMAIN}/'

PUBLIC_KEYS = None
token_scheme = HTTPBearer()

async def get_public_keys():
    global PUBLIC_KEYS
    if PUBLIC_KEYS is None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(JWKS_URL)
                response.raise_for_status()
                jwks = response.json()
            
            PUBLIC_KEYS = {key['kid']: key for key in jwks['keys']}
        except Exception as e:
            raise RuntimeError("Auth0 key fetching failed.")
    return PUBLIC_KEYS


async def validate_token(token: HTTPAuthorizationCredentials = Depends(token_scheme)):
    try:
        unverified_header = jwt.get_unverified_header(token.credentials)
        kid = unverified_header.get('kid')

        if kid is None:
            raise HTTPException(
                status_code=401, 
                detail="Invalid token: Key ID (kid) missing."
            )
        
        public_keys = await get_public_keys()
        jwks_key = public_keys.get(kid)

        if jwks_key is None:
            raise HTTPException(
                status_code=401, 
                detail="Invalid token: Key ID not recognized."
            )

        rsa_key = jwk.construct(jwks_key)

        payload = jwt.decode(
            token.credentials,
            rsa_key,
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=AUTH0_ISSUER
        )
        
        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=401, 
            detail=f"Unauthorized: Invalid or expired token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Authentication server error: {str(e)}"
        )