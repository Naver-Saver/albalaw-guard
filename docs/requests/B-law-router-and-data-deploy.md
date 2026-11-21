# 요청: 담당 B — 번역(Papago) 연결, 신규 라우터 등록

작성: 파트 A / 2026-11-21 (갱신, #28 확인 후) · 대상 파일은 B 소유라 A는 수정하지 않았습니다.
관련 이슈: #27 (Papago, 병합됨), #28 (근거·번역 연결 확인)

## 완료된 요청 (고맙습니다)

- Dockerfile `COPY data ./data` (#20)
- `law` 라우터 등록, 서버 시작 시 `load_law_data()` (#32)
- `review.py` 근거 검색을 `law_search`로 교체, 주제별 근거 검색 (#32, #39) — 실제 데이터로 확인함
- 최저임금을 `law-data/min-wage.json` 한 곳으로 통일, 2027년 값 보충 (#32)

## 남은 요청 (3가지, 합쳐서 약 8줄)

### 1. `app/main.py` — translate 라우터 등록

현재 `POST /api/translate`가 404입니다 (확인함). `translate.py` 라우터와 서비스는 #27로 `main`에 들어와 있습니다.

```python
from app.api.routes import contracts, health, law, recordings, translate, wage
...
app.include_router(translate.router, prefix="/api")  # API-10
```

등록하면 `tests/test_openapi_contract.py`가 `openapi.yaml`(API-10 정의 있음)과 대조합니다.

### 1-2. `main.py` — 급여명세서·대화 근거 라우터도 함께 (A가 구현 완료, 등록만 필요)

```python
from app.api.routes import contracts, evidence, health, law, payslips, recordings, translate, wage
...
app.include_router(payslips.router, prefix="/api")   # API-14 POST /payslips/review
app.include_router(evidence.router, prefix="/api")   # API-15 POST /recordings/evidence
```

(`recordings.router`와 prefix가 같은 `/recordings`지만 `POST /recordings/evidence`는 별도 경로라 충돌하지 않습니다.)

### 2. `app/api/routes/contracts.py` — 점검 결과 번역 연결

`ReviewRequest.lang`은 이미 있지만 아무 데서도 쓰이지 않아서, `lang=en`으로 요청해도 한국어로 나옵니다.

```python
from app.services.translate import translate_result

@router.post("/review", response_model=ApiResponse[ReviewResult])
async def review_contract(req: ReviewRequest) -> ApiResponse[ReviewResult]:
    try:
        result = await review.review(req)
    except ValueError as e:
        raise BadRequestError(str(e)) from e
    if req.lang != "ko":  # 설명 문장만 번역, 실패하면 원문 유지
        result = ReviewResult.model_validate(await translate_result(result.model_dump(), req.lang))
    return ok(result)
```

- `translate_result`는 `async`라 `await`가 필요합니다.
- 번역 대상: `explanation`, `disclaimer`, `items[].title/description`. `sources`·`calculation`은 번역하지 않습니다.
- Papago가 실패하면 해당 문장은 원문 그대로 나옵니다(응답이 깨지지 않음).
- 같은 문장은 메모리 캐시라 같은 결과를 반복 요청해도 Papago를 다시 부르지 않습니다.
- 대화 점검(C)의 결과(`findings`, `verbalPromises`, `checklistForNextTime`)도 같은 함수로 번역됩니다.
- 테스트는 `tests/test_translate.py`의 `fake_papago` 픽스처 방식(`mock_transport`)을 참고하세요. 가짜 번역은 `"[en]원문"` 형태입니다.

## 참고

- 계산: `calc.check_contract_wage(hourly_wage, weekly_hours, year=None)` (camelCase dict, 연도 데이터 없으면 `WageYearNotFound`).
- 필수 항목 누락: `checklist.find_missing("CONTRACT" | "PAYSLIP", fields)`.
- 급여명세서 검산: `calc.check_payslip_totals(items, deductions, total_pay, net_pay)`.
- 시그니처와 규칙은 `docs/CHANGELOG.md` 참고.
