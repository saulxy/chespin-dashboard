"""FastAPI Main Entrypoint for Chespin Local Dashboard."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db
from app.routers.api import router as api_router

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize SQLite database on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local Kiosk Web Dashboard for Chespin Personal Budget & Audio Hub",
    lifespan=lifespan,
)


# CORS middleware for local kiosk access & external network viewers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_header(request: Request, call_next):
    """Ensure static assets are not cached during local development / kiosk updates."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Mount static assets (CSS, JS, Icons)
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"

static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Include API Router
app.include_router(api_router)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    """Render the one-page Kiosk Dashboard."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "refresh_interval": settings.refresh_interval_seconds,
            "currency_symbol": settings.currency_symbol,
        },
    )


@app.get("/health")
async def health_check():
    """Simple healthcheck for kiosk watchdog services."""
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}
