# 요청: 담당 B — 번역 연결, 근거 검색 개선 제안

작성: 파트 A / 2026-11-21 (갱신, #31·#32 반영 후) · 대상 파일은 B 소유라 A는 수정하지 않았습니다.
관련 이슈: AI 쪽 #27 (Papago), 데이터 쪽 #28 (근거 연결)

## 완료된 요청 (고맙습니다)

- Dockerfile `COPY data ./data` (#20)
- `law` 라우터 등록과 서버 시작 시 `load_law_data()` (#32)
- `review.py`의 근거 검색을 `law_search.search_evidence`로 교체, `law_qa` 삭제 (#32)
- 최저임금을 `law-data/min-wage.json` 한 곳으로 통일, 2027년 값을 `announced.csv`로 보충 (#32)

## 1. `app/main.py` — translate 라우터 등록 (#27 병합 후)

```python
from app.api.routes import contracts, health, law, recordings, translate, wage
...
app.include_router(translate.router, prefix="/api")  # API-10 POST /translate
```

등록하면 `tests/test_openapi_contract.py`가 `openapi.yaml`(API-10 정의 있음)과 대조합니다.

## 2. 결과 번역 연결 (#27 병합 후)

`lang`이 `ko`가 아니면 점검 결과를 번역해서 돌려줍니다.

```python
from app.services.translate import translate_result

result_dict = review_result.model_dump()
if lang != "ko":
    result_dict = await translate_result(result_dict, lang)
```

- `async` 함수라 `await`가 필요합니다.
- 번역 대상: `explanation`, `disclaimer`, `items[].title/description`. `sources`·`calculation`은 번역하지 않습니다.
- Papago 오류 시 해당 문장은 원문이 그대로 나옵니다(결과 화면은 깨지지 않음).
- 대화 점검(C)의 결과(`findings`, `verbalPromises`, `checklistForNextTime`)도 같은 함수로 번역됩니다.

## 3. (제안) 근거 검색 — 키워드별로 골고루: `search_each`

`review.py`가 `search_evidence(keywords, limit=3)`로 키워드를 한 번에 검색하면 가장 흔한 주제(최저임금) 문항이 3개를 다 차지해서, 주휴·휴게 항목의 근거가 빠집니다.
(`["최저임금", "주휴", "휴게"]` → `manual-005`, `manual-006`, `manual-008`(최저임금 계열만))

키워드마다 따로 검색해 합치는 `search_each`를 추가해 두었습니다 (#27에 포함).

```python
from app.services.law_search import search_each

found = search_each(keywords, per_keyword=1, limit=3)
# → 최저임금 manual-005, 주휴 manual-010, 휴게 manual-013
```

반환 형식은 `search_evidence`와 같습니다 (`id`, `source`, `title`, `text`, `sourceUrl`). 한 줄 교체로 끝나고 `tests/test_review.py`의 기대값만 확인해 주세요.

## 4. 참고

- 계산: `calc.check_contract_wage(hourly_wage, weekly_hours, year=None)` (camelCase dict 반환, 연도 데이터 없으면 `WageYearNotFound`).
- 필수 항목 누락: `checklist.find_missing("CONTRACT" | "PAYSLIP", fields)`.
- 급여명세서 검산: `calc.check_payslip_totals(items, deductions, total_pay, net_pay)`.
- 시그니처와 규칙은 `docs/CHANGELOG.md` 참고.
