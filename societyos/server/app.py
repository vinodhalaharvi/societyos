"""
FastAPI application.

Start with:
    uvicorn societyos.server.app:app --reload --port 8000

Endpoints so far (PR #1 — foundation):
    GET /health  →  {"status": "ok", "version": "0.1.0"}

More endpoints are added in later PRs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from ..db.migrations import run_migrations
from .. import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once on startup: migrate the database."""
    await run_migrations()
    yield  # app runs here
    # (cleanup on shutdown goes after yield)


app = FastAPI(
    title="SocietyOS",
    description="Multi-agent collaboration platform",
    version=__version__,
    lifespan=lifespan,
)

# Allow the frontend (running on a different port locally) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Simple liveness check."""
    return {"status": "ok", "version": __version__}
