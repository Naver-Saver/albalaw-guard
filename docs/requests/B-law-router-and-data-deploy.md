# 요청: 담당 B — 근거·번역 연결, 라우터 등록, 최저임금 정리

작성: 파트 A / 2026-11-21 (갱신) · 대상 파일은 모두 B 소유라 A는 수정하지 않았습니다.
관련 이슈: 데이터 쪽 #28 (근거 연결), AI 쪽 #27 (Papago)

> 이전 요청 중 Dockerfile의 `COPY data ./data`는 #20에서 반영돼 완료했습니다. 고맙습니다.

## 1. `app/services/review.py` — 근거 검색을 `law_search`로 교체 (가장 중요)

지금 `/contracts/review`는 `law_qa.get_index()`(= `data/law_qa/manyask-worker.json`)에서 근거를 찾는데, 이 파일은 없어서 `sources`가 항상 비어 있습니다.
A가 수집한 근거(법령 조문 329건 + 수동 Q&A 36건)는 `app/services/law_search.py`에 있으니 아래처럼 바꿔 주세요.

```python
from app.services.law_search import build_evidence_block, search_each

# review() 안: 키워드마다 1건씩 골고루 (한 번에 검색하면 '최저임금' 문항이 3개를 다 차지함)
found = search_each(keywords, per_keyword=1, limit=3)   # list[dict]: id, source, title, text, sourceUrl

# explain(): 컨텍스트는 근거 블록 함수 사용 ("(id) 제목\n본문" 형식, 근거 1개 최대 800자·전체 한도)
context = build_evidence_block(sources, max_total_chars=2400)

# 응답 Source
Source(id=i["id"], title=i["title"], snippet=i["text"][:SNIPPET_CHARS] or None, url=i["sourceUrl"] or None)
```

- `explain(..., sources: list[LawQa])` 타입은 `list[dict]`로 바뀝니다. `LawQa` import와 `law_qa.py`, `data/law_qa/`는 사용처가 없어지면 지워도 됩니다.
- 확인: `build_items`의 키워드 `["최저임금", "주휴", "휴게"]`로 검색하면 각각 `manual-005`(최저임금), `manual-010`(주휴수당), `manual-013`(휴게시간)이 나옵니다.
- 데이터는 첫 호출 때 자동으로 읽히므로 시작 시 호출은 선택입니다 (원하면 lifespan에서 `load_law_data()`).
- `tests/test_review.py`가 `law_qa`를 가짜로 쓰고 있다면 `law_search` 기준으로 같이 바꿔 주세요. 테스트용 데이터는 `LAW_DATA_DIR` 환경변수로 폴더를 바꿀 수 있고, A의 테스트가 쓰는 `tests/conftest.py`의 `law_data_dir` 픽스처를 참고하세요.

## 2. `app/main.py` — 라우터 2개 등록 (필수)

```python
from app.api.routes import contracts, health, law, translate, wage
...
app.include_router(law.router, prefix="/api")        # API-11 GET /qa/search, API-12 GET /law/sources/{id}
app.include_router(translate.router, prefix="/api")  # API-10 POST /translate
```

(`translate` 라우터는 #27에서 추가됩니다. 해당 PR이 병합된 뒤 등록하세요.) 등록하면 `tests/test_openapi_contract.py`가 `openapi.yaml`과 대조하는데, A가 명세를 이미 추가해 두었습니다.

## 3. 결과 번역 연결 (#27 병합 후)

`lang`이 `ko`가 아니면 점검 결과를 번역해서 돌려줍니다.

```python
from app.services.translate import translate_result

result_dict = review_result.model_dump()
if lang != "ko":
    result_dict = await translate_result(result_dict, lang)
```

- `async` 함수라 `await`가 필요합니다.
- 번역 대상: `explanation`, `disclaimer`, `items[].title/description`. `sources`·`calculation`은 번역하지 않습니다.
- Papago 오류 시 원문이 그대로 나옵니다(결과 화면은 깨지지 않음).
- `ReviewRequest`에 `lang`이 이미 있으니, 응답 모델에 `lang`을 넣으시면 프런트에서 구분하기 좋습니다.

## 4. `app/services/wage.py` — 최저임금 하드코딩 (논의 필요)

`MINIMUM_WAGE_BY_YEAR`에 2026·2027년 금액이 코드에 들어 있습니다. 2027년 값(10,700원, 고시 제2026-60호)은 고용노동부 CSV에 없어 출처를 확인하지 못했습니다.
A의 `calc.py`는 같은 값을 `law-data/min-wage.json`(CSV 기반)에서 읽습니다. 두 곳이 어긋날 수 있으니:

- 추천: `check_wage`가 `calc.get_min_wage(year)`를 쓰게 하거나 `calc.check_contract_wage`로 바꾸기 (주휴수당 규칙은 BR-04 그대로: 주휴시간 × max(시급, 최저임금)).
- 최소: 2027년 값의 출처를 확인해서 알려 주세요. 확인 전에는 데이터에서 빼는 것이 안전합니다 (`tests/test_wage.py`의 2027 테스트도 영향).

## 5. 참고

- 계산: `calc.check_contract_wage(hourly_wage, weekly_hours, year=None)` (camelCase dict 반환, 연도 데이터 없으면 `WageYearNotFound`).
- 필수 항목 누락: `checklist.find_missing("CONTRACT" | "PAYSLIP", fields)`.
- 급여명세서 검산: `calc.check_payslip_totals(items, deductions, total_pay, net_pay)`.
- 시그니처와 규칙은 `docs/CHANGELOG.md` 참고.
