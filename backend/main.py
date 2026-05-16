"""
Smart Accident Detection and Alert System
FastAPI application entry point.
"""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import FRAMES_DIR, FRONTEND_DIST_DIR, UPLOAD_DIR
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.detection import router as detection_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Accident Detection and Alert System",
    description="CNN-powered road accident detection with automated email alerts",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth_router)
app.include_router(detection_router)
app.include_router(chat_router)

# Static mounts for generated media
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/frames", StaticFiles(directory=str(FRAMES_DIR)), name="frames")

if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets")
    logger.info("Mounted React assets from %s", FRONTEND_DIST_DIR / "assets")


def _resolve_frontend_index() -> Path:
    react_index = FRONTEND_DIST_DIR / "index.html"
    if react_index.exists():
        return react_index

    raise HTTPException(
        status_code=503,
        detail="Frontend build not found. Build frontend and retry.",
    )


@app.get("/", include_in_schema=False)
async def root_page():
    return FileResponse(str(_resolve_frontend_index()))


@app.get("/login", include_in_schema=False)
async def login_page():
    return FileResponse(str(_resolve_frontend_index()))


@app.get("/signup", include_in_schema=False)
async def signup_page():
    return FileResponse(str(_resolve_frontend_index()))


@app.get("/dashboard", include_in_schema=False)
async def dashboard_page():
    return FileResponse(str(_resolve_frontend_index()))


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    protected_prefixes = ("api", "uploads", "frames", "assets")
    if full_path.startswith(protected_prefixes):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(str(_resolve_frontend_index()))


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Smart Accident Detection and Alert System")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
