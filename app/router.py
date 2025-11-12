import os
import httpx
from fastapi import Request
from fastapi.responses import Response, JSONResponse
from dotenv import load_dotenv

load_dotenv()

# Get service URLs from environment variables, with defaults
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8002")

# Route configuration: maps gateway paths to backend services
# Format: "gateway_path": "backend_url"
ROUTES = {
    "/users": USER_SERVICE_URL,
    "/orders": ORDER_SERVICE_URL,
}

async def forward_request(request: Request, backend_url: str, route_prefix: str):
    """
    Forwards a request to a backend service.
    
    Args:
        request: The incoming request from the client
        backend_url: The base URL of the backend service
        route_prefix: The route prefix that matched (e.g., "/api/users")
    
    Returns:
        Response from the backend service
    """
    # Get the full path from the request
    path = request.url.path
    
    # Remove the route prefix to get the backend path
    # Example: /users/get -> /get
    backend_path = path[len(route_prefix):]
    if not backend_path:
        backend_path = "/"
    
    # Build the full backend URL
    full_backend_url = f"{backend_url}{backend_path}"
    
    # Copy query parameters if they exist
    if request.url.query:
        full_backend_url = f"{full_backend_url}?{request.url.query}"
    
    # Get request body if it exists
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Copy important headers from the original request
    headers = {}
    for header_name in ["authorization", "content-type", "accept"]:
        if header_name in request.headers:
            headers[header_name] = request.headers[header_name]
    
    # Make the request to the backend service
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=full_backend_url,
                headers=headers,
                content=body
            )
            
            # Return the response from the backend
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return JSONResponse(
            status_code=503,
            content={"error": "Backend service unavailable"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Gateway error: {str(e)}"}
        )

def get_backend_url(path: str):
    """
    Finds the backend URL for a given path.
    
    Args:
        path: The request path (e.g., "/api/users/123")
    
    Returns:
        Backend URL if route exists, None otherwise
    """
    for route_prefix, backend_url in ROUTES.items():
        if path.startswith(route_prefix):
            return backend_url
    return None

