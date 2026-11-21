# 변경 이력 (파트 A: 데이터·근거·명세)

명세(`docs/spec/`)와 파트 A가 제공하는 인터페이스(함수 시그니처·응답 형식)를 바꿀 때 여기에 기록합니다.
시그니처가 바뀌면 B·C에게 공지가 필요합니다.

## 2026-11-21

### 추가한 인터페이스 (B·C가 호출)

| 모듈 | 함수 | 비고 |
| --- | --- | --- |
| `app/services/law_search.py` | `load_law_data()`, `search_evidence(query, limit=5, sources=None)`, `get_source(source_id)`, `build_evidence_block(items, max_total_chars=4000)` | 데이터를 처음 쓸 때 자동 로드되므로 시작 시 호출은 선택. `sources`는 `"MANUAL"`, `"LAW_API"` |
| `app/services/calc.py` | `get_min_wage(year=None)`, `check_contract_wage(hourly_wage, weekly_hours, year=None)`, `check_payslip_totals(items, deductions, total_pay, net_pay)`, `WageYearNotFound` | 아래 "CLAUDE.md 초안과 다른 점" 참고 |
| `app/services/checklist.py` | `find_missing(doc_type, fields)` | `fields` 키는 snake_case (`hourly_wage`, `break_minutes` …) |

### API 명세 변경 (`docs/spec/openapi.yaml`, `03-api-spec.md`)

- API-11 `GET /qa/search`: 응답 항목에 `source` 추가, 설명 변경 (백문백답 → 수동 Q&A·법령 조문).
- API-12 `GET /law/sources/{source_id}` 추가 (근거 원문 단건).
- API-13 `GET /wage/minimum` 추가 (연도별 최저임금, `is_fallback`).

### 데이터 출처 변경

- 법제처 생활법령 GW API(15159736·15160076)가 호출 오류(코드 04)로 사용 불가 → 국가법령정보센터 Open API 조문 + 조문 기반 수동 Q&A로 대체. 근거는 `PRD.md` 결정 기록, `02-functional-spec.md` FS-06, `04-data-model.md` 참고.
- 최저임금은 고용노동부 연도별 최저임금 CSV(`sync.wage`로 변환)에서 읽는다.

### 일정

- 프로젝트 기간을 2주 → 1주로 변경 (`PRD.md` §14, `01-requirements.md`, `CONVENTIONS.md`).

### CLAUDE.md 초안과 다르게 구현한 점 (레포 컨벤션 우선)

- 필드·키 이름은 snake_case, 오류는 `{"detail": …}`, 경로는 `/api/...` (CLAUDE.md의 camelCase·`{success, code…}`·`/api/v1` 대신 레포 `openapi.yaml` 기준).
- `calc.check_contract_wage`의 반환 키는 CLAUDE.md 초안과 같은 camelCase(`minimumWage` 등)이고, 서비스 내부용이다. API 응답 변환은 라우터에서 한다.
- 주휴수당은 `주휴시간 × max(시급, 최저임금)` — 레포 명세 BR-04를 따랐다 (CLAUDE.md 초안은 `시급` 기준). 팀 검토 필요.
- 계약 기간(`contract_period`)은 근거 법령(기간제법)을 수집하지 않아 체크리스트에서 뺐다.
