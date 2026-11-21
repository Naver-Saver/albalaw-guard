# 요청: 담당 B — 근거 검색 라우터 등록, 데이터 배포, 최저임금 상수 정리

작성: 파트 A / 2026-11-21 · 대상 파일은 모두 B 소유라 A는 수정하지 않았습니다.

## 1. `app/main.py` — law 라우터 등록 (필수)

API-11(`GET /qa/search`)과 API-12(`GET /law/sources/{source_id}`)는 `app/api/routes/law.py`에 구현돼 있지만 앱에 등록돼 있지 않아 아직 동작하지 않습니다.

```python
from app.api.routes import health, law, wage
...
app.include_router(law.router, prefix="/api")
```

(선택) 시작 시 데이터를 미리 읽으려면 lifespan에서 `from app.services.law_search import load_law_data; load_law_data()` 호출. 호출하지 않아도 첫 검색 때 자동으로 읽습니다.

등록하면 `tests/test_openapi_contract.py`가 `openapi.yaml`과 대조합니다 (A가 이미 명세를 추가해 둠).

## 2. `backend/Dockerfile` — 데이터 파일 포함 (필수, 배포 전)

이미지에 `app/`만 복사해서 `backend/data/law-data/*.json`이 들어가지 않습니다. 그러면 운영에서 근거 검색이 비고 `GET /wage/minimum`이 404가 됩니다.
Object Storage 읽기가 구현되기 전까지는 아래 한 줄이 필요합니다.

```dockerfile
COPY data ./data
```

`.dockerignore`에는 `data`가 없으니 그대로 복사됩니다. Object Storage 연동 후에는 제거 가능.

## 3. `app/services/wage.py` — 최저임금 하드코딩 (논의 필요)

`MINIMUM_WAGE_BY_YEAR`에 2026·2027년 금액이 코드에 들어 있습니다. 2027년 값(10,700원, 고시 제2026-60호)은 고용노동부 CSV에 없어 출처를 확인하지 못했습니다.
A의 `app/services/calc.py`는 같은 값을 `law-data/min-wage.json`(CSV 기반)에서 읽습니다. 두 곳이 어긋날 수 있으니 `POST /wage/check`도 `calc.check_contract_wage`/`get_min_wage`를 쓰도록 바꾸거나, 최소한 2027년 값의 출처를 확인해 주세요. (`tests/test_wage.py`의 2027 테스트도 영향)

## 4. 참고: 연결 지점

- Studio 프롬프트용 근거: `search_evidence(...)` → `build_evidence_block(items)` ([법령 근거] 블록, 각 근거 앞에 `(id)`).
- 계산: `calc.check_contract_wage(hourly_wage, weekly_hours, year=None)` (camelCase dict 반환).
- 필수 항목 누락: `checklist.find_missing("CONTRACT" | "PAYSLIP", fields)`.
- 자세한 시그니처와 규칙은 `docs/CHANGELOG.md` 참고.
