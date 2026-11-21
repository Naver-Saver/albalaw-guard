from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, wage
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.core.response import register_exception_handlers

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title="알바생 노동권 지킴이 API", version=settings.app_version)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
register_exception_handlers(app)

app.include_router(health.router, prefix="/api")
app.include_router(wage.router, prefix="/api")
