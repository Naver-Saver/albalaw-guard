from fastapi import APIRouter, Query

from app.core.errors import NotFoundError
from app.core.response import ApiResponse, ok
from app.schemas.law import EvidenceSummary, LawSourceResponse, QaSearchResponse
from app.services.law_search import get_source, search_evidence

router = APIRouter(tags=["qa"])

SNIPPET_CHARS = 200


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[: SNIPPET_CHARS - 1].rstrip() + "…"


@router.get("/qa/search", response_model=ApiResponse[QaSearchResponse])
def qa_search(
    q: str = Query(..., min_length=1, description="검색어 또는 문장"),
    limit: int = Query(3, ge=1, le=10),
) -> ApiResponse[QaSearchResponse]:
    found = search_evidence(q, limit=limit)
    return ok(
        QaSearchResponse(
            items=[
                EvidenceSummary(
                    id=i["id"],
                    source=i["source"],
                    title=i["title"],
                    snippet=_snippet(i["text"]),
                    url=i["sourceUrl"],
                )
                for i in found
            ]
        )
    )


@router.get("/law/sources/{source_id}", response_model=ApiResponse[LawSourceResponse])
def law_source(source_id: str) -> ApiResponse[LawSourceResponse]:
    item = get_source(source_id)
    if item is None:
        raise NotFoundError("근거 원문을 찾을 수 없어요.")
    return ok(
        LawSourceResponse(
            id=item["id"],
            source=item["source"],
            title=item["title"],
            text=item["text"],
            url=item["sourceUrl"],
            related_article_ids=item.get("relatedArticleIds", []),
        )
    )
