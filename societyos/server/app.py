"""
FastAPI application.

Start with:
    uvicorn societyos.server.app:app --reload --port 8000

Endpoints so far (PR #1 — foundation):
    GET /health  →  {"status": "ok", "version": "0.1.0"}

More endpoints are added in later PRs.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..db.migrations import run_migrations
from ..settings import settings
from .routes.runs import router as runs_router


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
    allow_origins=settings.cors_allow_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Simple liveness check."""
    return {"status": "ok", "version": __version__}


app.include_router(runs_router)

_frontend = Path(__file__).parent.parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
