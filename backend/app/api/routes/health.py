from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.response import ApiResponse, ok

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    version: str


@router.get("/health", response_model=ApiResponse[Health])
def health() -> ApiResponse[Health]:
    return ok(Health(status="ok", version=get_settings().app_version))
