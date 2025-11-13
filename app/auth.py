"""
AUTHENTICATION BASICS - What is this code doing?

WHAT IS AUTHENTICATION?
----------------------
Authentication is proving "who you are" to our API. Think of it like showing ID at a bar.
Without authentication, anyone could access protected endpoints. With it, only logged-in users can.

WHAT IS AUTH0?
--------------
Auth0 is a service that handles user login for us. Instead of building our own login system
(username/password, social login, etc.), we use Auth0. Users log in through Auth0's website,
and Auth0 gives them a "token" (like a temporary ID card) that proves they're logged in.

WHAT IS A JWT TOKEN?
--------------------
JWT = JSON Web Token. It's like a digital ID card that contains:
  - Who the user is (user ID, email)
  - When it expires
  - Who issued it (Auth0)
  - A signature (like a tamper-proof seal)

The token looks like: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0..."
It has 3 parts separated by dots: header.payload.signature

HOW DOES IT WORK? (The Complete Flow)
-------------------------------------
1. USER LOGS IN:
   - User goes to Auth0's login page (not our API)
   - User enters email/password (or uses Google, Facebook, etc.)
   - Auth0 verifies credentials and creates a JWT token
   - Auth0 signs the token with their PRIVATE KEY (like a secret stamp)
   - Auth0 gives the token to the user

2. USER MAKES A REQUEST TO OUR API:
   - User includes token in the request header: "Authorization: Bearer <token>"
   - This is like showing your ID card to the bouncer

3. OUR API VERIFIES THE TOKEN (this file does this):
   - Extract the token from the "Bearer <token>" header
   - Read the token header to find which key Auth0 used to sign it (key ID)
   - Fetch Auth0's PUBLIC KEY from their website (JWKS endpoint)
   - Use the public key to verify the signature (proves Auth0 created it, not a fake)
   - Check the token hasn't expired
   - Check the token is for our API (audience) and from our Auth0 domain (issuer)
   - If all checks pass, decode the token to get user info (user ID, email, etc.)

WHY PUBLIC/PRIVATE KEYS?
------------------------
Think of it like a lock and key system:
  - Auth0 has a PRIVATE KEY (like a master key) - they use it to SIGN tokens
  - Everyone can have the PUBLIC KEY (like a lock) - we use it to VERIFY signatures
  - If the signature verifies, we know Auth0 created the token (because only they have the private key)
  - This prevents people from creating fake tokens

WHAT IS THE AUTHORIZATION HEADER?
----------------------------------
HTTP headers are extra information sent with every request. The "Authorization" header
is a standard way to send credentials. The format is: "Bearer <token>"
  - "Bearer" tells us it's a token (not a username/password)
  - "<token>" is the actual JWT token string

WHAT HAPPENS IF TOKEN IS INVALID?
----------------------------------
If the token is fake, expired, or wrong, we return HTTP 401 (Unauthorized) and reject the request.
The user must log in again to get a new token.
"""

import httpx
import os
from jose import jwt, jwk
from jose.exceptions import JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from dotenv import load_dotenv

load_dotenv()

# Auth0 configuration from environment variables
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")  # Expected API identifier in token
JWKS_URL = f'https://{AUTH0_DOMAIN}/.well-known/jwks.json'  # Public keys endpoint
AUTH0_ISSUER = f'https://{AUTH0_DOMAIN}/'  # Token must be issued by this Auth0 domain

# Cache for public keys (fetched once, reused for all requests)
# Auth0 signs tokens with private keys, we verify with public keys from JWKS endpoint
cached_keys = None

# FastAPI security scheme: extracts "Bearer <token>" from Authorization header
bearer = HTTPBearer()

async def get_public_keys():
    """
    Fetch and cache Auth0 public keys for JWT verification.
    
    JWKS (JSON Web Key Set) contains public keys used to verify JWT signatures.
    Auth0 rotates keys periodically, so we cache them and can refresh when needed.
    Each key has a 'kid' (key ID) that matches the 'kid' in the JWT header.
    """
    global cached_keys
    
    # Return cached keys if already fetched (performance optimization)
    if cached_keys is not None:
        return cached_keys
    
    # Fetch public keys from Auth0's JWKS endpoint
    # These are the public keys that correspond to Auth0's private signing keys
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        response.raise_for_status()
        jwks_data = response.json()
    
    # Store keys by their key ID (kid) for O(1) lookup when verifying tokens
    # Token header contains 'kid' → we use it to find the right public key
    cached_keys = {key['kid']: key for key in jwks_data['keys']}
    return cached_keys

async def validate_token(token: HTTPAuthorizationCredentials = Depends(bearer)):
    """
    Validate JWT token from Authorization header.
    
    Authentication Flow:
    1. Extract token from "Bearer <token>" header
    2. Read token header to get key ID (kid) - tells us which Auth0 key signed it
    3. Fetch matching public key from Auth0's JWKS endpoint
    4. Verify signature using RS256 algorithm (proves token came from Auth0)
    5. Verify audience and issuer (ensures token is for our API and from our Auth0 domain)
    6. Return decoded payload with user info (sub, email, etc.)
    
    Returns the decoded token payload if valid, raises 401 if invalid.
    """
    # Step 1: Extract token string from "Bearer <token>" format
    token_string = token.credentials
    
    # Step 2: Read token header (without verification) to get the key ID
    # JWT has 3 parts: header.payload.signature - we need header to find which key was used
    header = jwt.get_unverified_header(token_string)
    key_id = header.get('kid')  # Key ID tells us which Auth0 public key to use
    
    if not key_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing key ID")
    
    # Step 3: Get the matching public key from Auth0's JWKS endpoint
    # The key_id in token header must match a 'kid' in Auth0's public keys
    keys = await get_public_keys()
    matching_key = keys.get(key_id)
    
    if not matching_key:
        raise HTTPException(status_code=401, detail="Invalid token: key not found")
    
    # Step 4: Construct public key object for signature verification
    # RS256 = RSA signature with SHA-256 (asymmetric encryption)
    public_key = jwk.construct(matching_key)
    
    # Step 5: Verify signature and decode token
    # jwt.decode() will:
    #   - Verify the signature matches (proves Auth0 signed it)
    #   - Check expiration time (exp claim)
    #   - Verify audience matches (token is for our API)
    #   - Verify issuer matches (token came from our Auth0 domain)
    try:
        payload = jwt.decode(
            token_string,
            public_key,
            algorithms=["RS256"],  # RSA signature algorithm
            audience=AUTH0_AUDIENCE,  # Token must be for this API
            issuer=AUTH0_ISSUER      # Token must be from this Auth0 domain
        )
        return payload  # Contains user info: sub (user ID), email, permissions, etc.
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
