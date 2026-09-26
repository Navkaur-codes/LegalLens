"""HTTP middleware: early upload-size rejection, response compression and security headers."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings

UPLOAD_PATH = "/api/brief"
# Allowance for multipart boundaries and headers around the file itself.
MULTIPART_OVERHEAD_BYTES = 64 * 1024

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    ),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

CallNext = Callable[[Request], Awaitable[Response]]


def upload_size_error(content_length: str | None, settings: Settings) -> JSONResponse | None:
    """Reject uploads by their declared size before the body is read or buffered."""
    if content_length is None:
        return JSONResponse(status_code=411, content={"detail": "The upload size could not be determined."})
    if not content_length.isdigit():
        return JSONResponse(status_code=400, content={"detail": "Invalid upload request."})
    if int(content_length) > settings.max_file_bytes + MULTIPART_OVERHEAD_BYTES:
        return JSONResponse(status_code=413, content={"detail": f"The file is larger than {settings.max_file_mb} MB."})
    return None


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Install middleware. The last one registered runs first (outermost)."""
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def limit_upload_size(request: Request, call_next: CallNext) -> Response:
        if request.method == "POST" and request.url.path == UPLOAD_PATH:
            error = upload_size_error(request.headers.get("content-length"), settings)
            if error is not None:
                return error
        return await call_next(request)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next: CallNext) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response
