from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_cors_origin_regex, get_cors_origins
from app.incidents.router import router as incidents_router
from auth.config import get_jwt_secret, validate_password_reset_config
from routes.auth import router as auth_router
from routes.profiles import router as profiles_router
from routes.suppliers import router as suppliers_router
from routes.users import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_jwt_secret()
    validate_password_reset_config()
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

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(profiles_router)
app.include_router(incidents_router, prefix="/api")
app.include_router(suppliers_router)
