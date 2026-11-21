from dataclasses import asdict

from fastapi import APIRouter

from app.core.errors import BadRequestError
from app.core.response import ApiResponse, ok
from app.schemas.wage import WageCheckRequest, WageCheckResponse
from app.services.wage import check_wage

router = APIRouter(prefix="/wage", tags=["wage"])


@router.post("/check", response_model=ApiResponse[WageCheckResponse])
def wage_check(req: WageCheckRequest) -> ApiResponse[WageCheckResponse]:
    try:
        result = check_wage(req.hourly_wage, req.weekly_hours, req.year)
    except ValueError as e:
        raise BadRequestError(str(e)) from e
    return ok(WageCheckResponse(**asdict(result)))
