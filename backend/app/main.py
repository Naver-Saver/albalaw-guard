from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import contracts, evidence, health, law, payslips, recordings, translate, wage
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.core.response import register_exception_handlers
from app.services.law_search import load_law_data

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    load_law_data()  # 근거 데이터(law-data/*.json)를 시작 시 메모리에 적재 (NFR: DB 없음)
    yield


app = FastAPI(title="알바생 노동권 지킴이 API", version=settings.app_version, lifespan=lifespan)

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
app.include_router(contracts.router, prefix="/api")
app.include_router(law.router, prefix="/api")
app.include_router(recordings.router, prefix="/api")
app.include_router(evidence.router, prefix="/api")
app.include_router(payslips.router, prefix="/api")
app.include_router(translate.router, prefix="/api")
