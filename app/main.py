"""FastAPI app factory: routes, static frontend, middleware and error handling."""

import logging
import mimetypes

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import STATIC_DIR, Settings, get_settings
from app.errors import LegalLensError
from app.middleware import register_middleware
from app.rate_limit import RateLimiter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("legallens")

# ES modules must be served with a JavaScript MIME type; some OS registries map ".js" incorrectly.
mimetypes.add_type("text/javascript", ".js")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="LegalLens", version="1.0.0", docs_url=None, redoc_url=None)
    app.state.rate_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_s)
    register_middleware(app, settings)
    logger.info("LLM mode: %s", settings.llm_mode)

    @app.exception_handler(LegalLensError)
    async def handle_app_error(request: Request, exc: LegalLensError) -> JSONResponse:
        logger.info("request failed status=%d error=%s", exc.status_code, type(exc).__name__)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def handle_bad_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": "Please choose a PDF file to upload."})

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected error")
        return JSONResponse(status_code=500, content={"detail": "Something went wrong. Please try again."})

    app.include_router(router)
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
