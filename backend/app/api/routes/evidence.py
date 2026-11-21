from fastapi import APIRouter

from app.core.response import ApiResponse, ok
from app.schemas.evidence import TimelineEvidenceRequest, TimelineEvidenceResult
from app.services.timeline_evidence import find_timeline_evidence
from app.services.translate import translate_texts

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.post("/evidence", response_model=ApiResponse[TimelineEvidenceResult])
async def timeline_evidence(req: TimelineEvidenceRequest) -> ApiResponse[TimelineEvidenceResult]:
    """대화 타임라인 발언의 근거와 '말로만 한 약속' 안내 (API-15). 서버에 아무것도 저장하지 않는다.
    lang 이 ko 가 아니면 안내 문장만 번역한다 (Papago 실패 시 원문 유지)."""
    result = find_timeline_evidence(req)
    if req.lang != "ko":
        advice_idx = [i for i, e in enumerate(result.entries) if e.advice]
        texts = (
            [result.entries[i].advice or "" for i in advice_idx]
            + result.checklist_for_next_time
            + [result.disclaimer]
        )
        out = await translate_texts(texts, req.lang)
        for pos, i in enumerate(advice_idx):
            result.entries[i].advice = out[pos]
        n = len(result.checklist_for_next_time)
        result.checklist_for_next_time = out[len(advice_idx) : len(advice_idx) + n]
        result.disclaimer = out[-1]
    return ok(result)
