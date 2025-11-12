import os
import httpx
from fastapi import Request
from fastapi.responses import Response, JSONResponse
from dotenv import load_dotenv

load_dotenv()

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8002")

ROUTES = {
    "/users": USER_SERVICE_URL,
    "/orders": ORDER_SERVICE_URL,
}

async def forward_request(request: Request, backend_url: str, route_prefix: str):
    path = request.url.path
    backend_path = path[len(route_prefix):]
    if not backend_path:
        backend_path = "/"
    
    full_backend_url = f"{backend_url}{backend_path}"
    
    if request.url.query:
        full_backend_url = f"{full_backend_url}?{request.url.query}"
    
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    headers = {}
    for header_name in ["authorization", "content-type", "accept"]:
        if header_name in request.headers:
            headers[header_name] = request.headers[header_name]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=full_backend_url,
                headers=headers,
                content=body
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return JSONResponse(status_code=503, content={"error": "Backend service unavailable"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Gateway error: {str(e)}"})

def get_backend_url(path: str):
    for route_prefix, backend_url in ROUTES.items():
        if path.startswith(route_prefix):
            return backend_url
    return None
