from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from app.schemas.wage import WageCheckRequest, WageCheckResponse
from app.services.wage import check_wage

router = APIRouter(prefix="/wage", tags=["wage"])


@router.post("/check", response_model=WageCheckResponse)
def wage_check(req: WageCheckRequest) -> WageCheckResponse:
    try:
        result = check_wage(req.hourly_wage, req.weekly_hours, req.year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WageCheckResponse(**asdict(result))
