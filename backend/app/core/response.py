"""공통 응답 형식: {success, data} / {success: false, error: {code, message, details}}."""

import logging
from typing import Any, Generic, Literal, TypeVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError

T = TypeVar("T")
logger = logging.getLogger("app")


class ApiResponse(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: T


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorBody


def ok(data: T) -> ApiResponse[T]:
    return ApiResponse[T](data=data)


def _error(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump(exclude_none=True))


_HTTP_CODES = {400: "BAD_REQUEST", 404: "NOT_FOUND", 405: "BAD_REQUEST", 413: "FILE_TOO_LARGE"}
_HTTP_MESSAGES = {404: "요청한 정보를 찾을 수 없어요.", 405: "지원하지 않는 요청 방식이에요."}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.warning("app error %s: %s", exc.code, exc.message)
        return _error(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _error(422, "VALIDATION_ERROR", "입력값을 확인해 주세요.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, "INTERNAL_ERROR" if exc.status_code >= 500 else "BAD_REQUEST")
        message = _HTTP_MESSAGES.get(exc.status_code) or (exc.detail if isinstance(exc.detail, str) else "")
        return _error(exc.status_code, code, message or "요청을 처리할 수 없어요.")

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected error", exc_info=exc)
        return _error(500, "INTERNAL_ERROR", "잠시 후 다시 시도해 주세요.")
