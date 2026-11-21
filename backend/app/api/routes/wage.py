from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from app.schemas.law import MinimumWageResponse
from app.schemas.wage import WageCheckRequest, WageCheckResponse
from app.services.calc import WageYearNotFound, get_min_wage
from app.services.wage import check_wage

router = APIRouter(prefix="/wage", tags=["wage"])


@router.post("/check", response_model=WageCheckResponse)
def wage_check(req: WageCheckRequest) -> WageCheckResponse:
    try:
        result = check_wage(req.hourly_wage, req.weekly_hours, req.year)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return WageCheckResponse(**asdict(result))


@router.get("/minimum", response_model=MinimumWageResponse)
def minimum_wage_by_year(year: int | None = Query(None, ge=1900, le=2200)) -> MinimumWageResponse:
    """연도별 최저임금. year 미지정 시 올해(없으면 데이터가 있는 가장 최근 연도로 대체, is_fallback=true)."""
    try:
        mw = get_min_wage(year)
    except WageYearNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return MinimumWageResponse(
        year=mw["year"],
        hourly_wage=mw["hourlyWage"],
        period_start=mw["periodStart"],
        period_end=mw["periodEnd"],
        is_fallback=mw["isFallback"],
    )
