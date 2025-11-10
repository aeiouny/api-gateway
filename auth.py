from jose import jwt
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx


AUTH0_DOMAIN = 'dev-kmxxj2ycis6e0x01.us.auth0.com' 
ALGORITHMS = ["RS256"]
JWKS_URL = f'https://{AUTH0_DOMAIN}/.well-known/jwks.json'


PUBLIC_KEYS = None
http_client = httpx.Client()
token_scheme = HTTPBearer()

async def get_public_keys():
    global PUBLIC_KEYS
    if PUBLIC_KEYS is None:
        try:
            jwks = http_client.get(JWKS_URL).json()
            PUBLIC_KEYS = {key['kid']: key for key in jwks['keys']}
        except Exception as e:
            print(f"ERROR: Could not fetch Auth0 public keys: {e}")
            raise RuntimeError("Auth0 key fetching failed.")
    return PUBLIC_KEYS

async def validate_token(token: HTTPAuthorizationCredentials = Depends(token_scheme)):
    try:
        unverified_header = jwt.get_unverified_header(token.credentials)
        kid = unverified_header.get('kid')

        if kid is None:
            raise HTTPException(status_code=401, detail="Invalid token: Key ID (kid) missing.")
        
        public_keys = await get_public_keys()
        rsa_key = public_keys.get(kid)

        if rsa_key is None:
            raise HTTPException(status_code=401, detail="Invalid token: Key ID not recognized.")

        payload = jwt.decode(
            token.credentials,
            rsa_key,
            algorithms=ALGORITHMS,
            audience="https://api.mygateway.com", 
            issuer=f'https://{AUTH0_DOMAIN}/'
        )
        
        return payload

    except JWTError as e:
        print(f"JWT Validation Error: {e}")
        raise HTTPException(status_code=401, detail=f"Unauthorized: {e.__class__.__name__}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication server error: {e}")