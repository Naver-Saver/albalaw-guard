from fastapi import APIRouter

from app.core.response import ApiResponse, ok
from app.schemas.payslips import PayslipReviewRequest, PayslipReviewResult
from app.services.payslip_review import review_payslip
from app.services.translate import translate_result

router = APIRouter(prefix="/payslips", tags=["payslips"])


@router.post("/review", response_model=ApiResponse[PayslipReviewResult])
async def payslip_review(req: PayslipReviewRequest) -> ApiResponse[PayslipReviewResult]:
    """급여명세서 점검 (API-14). 검산·필수 항목·최저임금·공제를 코드로 확인하고 근거를 붙인다.
    lang 이 ko 가 아니면 설명 문장만 번역한다 (Papago 실패 시 원문 유지)."""
    result = review_payslip(req)
    if req.lang != "ko":
        result = PayslipReviewResult.model_validate(await translate_result(result.model_dump(), req.lang))
    return ok(result)
