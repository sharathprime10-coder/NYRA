import os
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.endpoints import analytics as analytics_router
from app.api.endpoints import auth as auth_router
from app.api.endpoints import chat as chat_router
from app.api.endpoints import curation as curation_router
from app.api.endpoints import documents as documents_router
from app.core.logging_config import setup_logging
from app.core.rate_limit import limiter
from app.db.database import Base, engine
from app.tools.mcp_client import cleanup_mcp, initialize_mcp

logger = setup_logging()
import logging
logging.getLogger("langchain_google_genai._function_utils").setLevel(logging.ERROR)


def _rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    """Return a 429 JSON response when a rate limit is exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


# Initialize Sentry if DSN is provided
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )
    logger.info("Sentry initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (for local dev)
    Base.metadata.create_all(bind=engine)
    # Startup
    await initialize_mcp()
    yield
    # Shutdown
    await cleanup_mcp()


app = FastAPI(
    title="NYRA Platform API",
    description="The core API powering NYRA, a premium agentic knowledge assistant featuring LangGraph and MCP capabilities.",
    version="1.0.0",
    contact={
        "name": "SOC Dev Ops Team",
        "email": "admin@nyra.ai",
    },
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", extra={"path": request.url.path}, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# Define allowed origins
origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]

frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time_ms = (time.time() - start_time) * 1000

    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(process_time_ms, 2),
        },
    )

    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents_router.router, prefix="/api/documents", tags=["documents"])
app.include_router(analytics_router.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(curation_router.router, prefix="/api/curation", tags=["curation"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
