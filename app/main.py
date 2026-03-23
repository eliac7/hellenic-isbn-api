from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from curl_cffi import requests as curl_requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes.books import router as books_router
from app.services.cache import build_cache
from app.services.rate_limiter import InMemoryRateLimiter
from app.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    app.state.curl_session = curl_requests.AsyncSession(
        timeout=settings.request_timeout_seconds,
        impersonate=settings.curl_impersonate,
    )
    app.state.rate_limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    async with build_cache() as cache:
        app.state.cache = cache
        yield

    await app.state.curl_session.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(books_router)


@app.middleware("http")
async def simple_rate_limit(request: Request, call_next):
    client_host = request.client.host if request.client else "unknown"
    limiter = request.app.state.rate_limiter
    if not limiter.is_allowed(client_host):
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    return await call_next(request)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
