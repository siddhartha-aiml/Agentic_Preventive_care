import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .agents.graph import get_graph
from .agents.llm import LLM_HEALTH, agent_mode
from .agents.specialties import SPECIALTIES
from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import Provider, User
from .routers import appointments, auth, conversations, doctor, patients, providers, voice
from .seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("yhg")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed(db)
    get_graph()
    if settings.demo_mode:
        log.warning("OPENAI_API_KEY not found in environment -> DEMO MODE (rule-based agents)")
    else:
        log.info("OPENAI_API_KEY loaded (length %d) -> GPT agents enabled, model=%s", len(settings.openai_api_key), settings.openai_model)
    if settings.voice_enabled:
        log.info("SARVAM_API_KEY loaded -> Sarvam voice enabled (stt=%s, tts=%s)", settings.sarvam_stt_model, settings.sarvam_tts_model)
    else:
        log.warning("SARVAM_API_KEY not set -> voice falls back to the browser's built-in speech")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
for r in (auth.router, patients.router, conversations.router, providers.router, appointments.router, doctor.router, voice.router):
    api.include_router(r)


@api.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@api.get("/meta", tags=["meta"])
def meta():
    demo_accounts = None
    if settings.show_demo_accounts:
        with SessionLocal() as db:
            rows = db.query(Provider.name, Provider.specialty, User.email).join(User, Provider.user_id == User.id).order_by(Provider.specialty).all()
        demo_accounts = {
            "patient": {"email": "patient@demo.com", "password": "demo1234"},
            "doctor_password": "doctor123",
            "doctors": [{"name": n, "specialty": s, "email": e} for n, s, e in rows],
        }
    return {
        "demo_accounts": demo_accounts,
        "app_name": settings.app_name,
        "demo_mode": settings.demo_mode,
        "voice_provider": "sarvam" if settings.voice_enabled else "browser",
        "agent_mode": agent_mode(),
        "llm_last_error_type": LLM_HEALTH["last_error_type"] if agent_mode() == "degraded" else None,
        "model": None if settings.demo_mode else settings.openai_model,
        "specialties": [{"name": k, "description": v["description"], "icon": v["icon"]} for k, v in SPECIALTIES.items()],
    }


app.include_router(api)

# ── Serve the built React app (single-image deploy) ──
static_dir = Path(settings.static_dir)
if static_dir.exists():
    if (static_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = (static_dir / full_path).resolve()
        if full_path and candidate.is_file() and static_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(static_dir / "index.html")
