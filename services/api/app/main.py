from contextlib import asynccontextmanager
from pathlib import Path
import sys

# Repo root so `data.pipelines` / `data.process` resolve when uvicorn cwd is services/api.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)
except ImportError:
    pass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_cors_origin_regex, get_cors_origins
from app.incidents.manager_router import router as incident_manager_router
from app.incidents.router import router as incidents_router
from auth.config import get_jwt_secret, validate_password_reset_config
from inventory.database import init_inventory_schema
from inventory.router import router as inventory_router
from knowledge.router import router as knowledge_router
from reporting.router import router as reporting_router
from routes.auth import router as auth_router
from routes.profiles import router as profiles_router
from routes.suppliers import router as suppliers_router
from routes.users import router as users_router
from telemetry.router import router as telemetry_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_jwt_secret()
    validate_password_reset_config()
    init_inventory_schema()
    from inventory.database import _engine
    from data.pipelines.monthly_clinic_supply_performance.db import (
        ensure_reporting_schema,
    )

    if _engine is not None:
        ensure_reporting_schema()
    yield


app = FastAPI(
    title="HealthCore API",
    description="Internal API for HealthCore Digital operations tools.",
    version="0.1.0",
    lifespan=lifespan,
)

_origins = get_cors_origins()
_allow_all = _origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=None if _allow_all else get_cors_origin_regex(),
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.core.validation_errors import sanitize_validation_errors


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": sanitize_validation_errors(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(incidents_router, prefix="/api")
app.include_router(incident_manager_router, prefix="/api")
app.include_router(suppliers_router)
app.include_router(inventory_router)
app.include_router(telemetry_router)
app.include_router(reporting_router)
app.include_router(knowledge_router)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
