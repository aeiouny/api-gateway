import httpx
import os
from jose import jwt, jwk
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

auth0_domain = os.getenv("AUTH0_DOMAIN")
auth0_audience = os.getenv("AUTH0_AUDIENCE")
algorithm = "RS256"
jwks_url = f'https://{auth0_domain}/.well-known/jwks.json'
auth0_issuer = f'https://{auth0_domain}/'

cached_keys = None
bearer = HTTPBearer()

async def get_public_keys():
    global cached_keys
    if cached_keys is None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
                data = response.json()
            
            cached_keys = {}
            for key in data['keys']:
                cached_keys[key['kid']] = key
        except Exception:
            raise RuntimeError("Auth0 key fetching failed.")
    return cached_keys

async def validate_token(token: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        token_string = token.credentials
        header = jwt.get_unverified_header(token_string)
        kid = header.get('kid')

        if kid is None:
            raise HTTPException(status_code=401, detail="Invalid token: Key ID missing.")
        
        keys = await get_public_keys()
        matching_key = keys.get(kid)

        if matching_key is None:
            raise HTTPException(status_code=401, detail="Invalid token: Key ID not found.")

        public_key = jwk.construct(matching_key)

        payload = jwt.decode(
            token_string,
            public_key,
            algorithms=[algorithm],
            audience=auth0_audience,
            issuer=auth0_issuer
        )
        
        return payload

    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or expired token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")