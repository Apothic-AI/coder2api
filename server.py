import httpx
from litestar import Litestar, Request, Response, get
from litestar.status_codes import HTTP_200_OK
from litestar.exceptions import HTTPException
import os

# Configuration for backend ports
GEMINI_PORT = int(os.environ.get("CODER2API_GEMINI_PORT", 3001))
CODEX_PORT = int(os.environ.get("CODER2API_CODEX_PORT", 3002))
CC_PORT = int(os.environ.get("CODER2API_CC_PORT", 3003))

async def proxy_request(request: Request, target_base_url: str, path: str) -> Response:
    # Strip leading slash to avoid double slashes when constructing url
    path = path.lstrip("/")
    client = httpx.AsyncClient(base_url=target_base_url, timeout=60.0)
    
    # Construct the target URL
    url = f"/{path}"
    if request.url.query:
        url += f"?{request.url.query}"
    
    # Filter headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    try:
        api_response = await client.request(
            method=request.method,
            url=url,
            content=content,
            headers=headers,
        )
        
        return Response(
            content=api_response.content,
            status_code=api_response.status_code,
            headers=dict(api_response.headers),
            media_type=api_response.headers.get("content-type"),
        )
    except httpx.RequestError as exc:
        return Response(
            content={"error": f"Proxy error: {str(exc)}"},
            status_code=502,
            media_type="application/json"
        )
    finally:
        await client.aclose()

@get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "coder2api"}

# Routes for Codex (ChatMock)
async def codex_proxy(request: Request, path: str) -> Response:
    return await proxy_request(request, f"http://localhost:{CODEX_PORT}", path)

# Routes for CC (Claude Code API)
async def cc_proxy(request: Request, path: str) -> Response:
    return await proxy_request(request, f"http://localhost:{CC_PORT}", path)

# Routes for Gemini
async def gemini_proxy(request: Request, path: str) -> Response:
    return await proxy_request(request, f"http://localhost:{GEMINI_PORT}", path)

# We register these as handlers for all methods
from litestar.handlers import HTTPRouteHandler

def create_proxy_handler(path_prefix: str, handler_func):
    # Litestar doesn't support "all methods" wildcard easily in one decorator line without a list
    # We create a handler that accepts the path parameter
    return HTTPRouteHandler(
        path=f"/{path_prefix}/{{path:path}}",
        http_method=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    )(handler_func)

app = Litestar(
    route_handlers=[
        health_check,
        create_proxy_handler("codex", codex_proxy),
        create_proxy_handler("cc", cc_proxy),
        create_proxy_handler("gemini", gemini_proxy),
    ]
)
