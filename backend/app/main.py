from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import Base, engine
from app.db.models import user, document, chat
from app.api.endpoints import chat as chat_router
from app.api.endpoints import auth as auth_router
from app.api.endpoints import documents as documents_router
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter, _rate_limit_exceeded_handler
# Create tables (for local dev)
Base.metadata.create_all(bind=engine)

from contextlib import asynccontextmanager

from app.tools.mcp_client import initialize_mcp, cleanup_mcp

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

import os

# Define allowed origins
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]

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

app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents_router.router, prefix="/api/documents", tags=["documents"])

@app.get("/api/health")
def health_check():
    return {"status": "ok"}
