# 변경 이력 (파트 A: 데이터·근거·명세)

명세(`docs/spec/`)와 파트 A가 제공하는 인터페이스(함수 시그니처·응답 형식)를 바꿀 때 여기에 기록합니다.
시그니처가 바뀌면 B·C에게 공지가 필요합니다.

## 2026-11-21 (#40 법령 데이터 읽기 보강)

- `law_data.read_json`(실제 NCP 버킷에서 읽을 때만): 읽은 JSON을 프로세스 안에 캐시하고(갱신은 서버 재시작으로 반영), 실패·없음은 60초간 기억해 그동안 로컬 파일을 쓴다. 읽기 전용 클라이언트는 연결 3초·읽기 10초·재시도 1회의 짧은 타임아웃. `calc.get_min_wage` 등이 요청마다 `read_json`을 호출해도 버킷 호출이 반복되지 않는다. In-Memory 스토리지·`LAW_DATA_DIR`는 기존 동작 그대로.
- 시그니처 변경 없음. 업로드·읽기 연동 자체는 #41(C)에서 구현됨.

## 2026-11-21 (Papago 번역, #27)

### 추가한 인터페이스 (B·C가 호출)

| 모듈 | 함수 | 비고 |
| --- | --- | --- |
| `app/services/translate.py` | `async translate_texts(texts, target, source="ko", *, strict=False)` | 같은 문장은 캐시. 기본은 실패 시 원문 반환 + 경고 로그, `strict=True`면 예외(`AI_UNAVAILABLE` 502). `target="ko"`면 그대로 반환. 지원 `en`·`vi`·`zh-CN`, 그 밖은 `BAD_REQUEST` |
| `app/services/translate.py` | `async translate_result(result, target)` | 입력은 바꾸지 않고 번역본을 반환. 번역 대상: `explanation`, `disclaimer`, `items[].title/description`, `findings[].explanation`, `verbalPromises[].advice`, `checklistForNextTime[]`. `evidenceText`·`sources`·`calculation` 등은 번역하지 않음 |
| `app/services/law_search.py` | `search_each(keywords, per_keyword=1, limit=5)` | 키워드마다 따로 검색해 주제가 골고루 나오게 합침 (서류 점검 권장) |

- CLAUDE.md 초안과 다른 점: 레포의 CLOVA 연동처럼 **비동기(`async`)** 로 만들었다 (`app/services/http.py`의 `post_with_retry` 사용). 호출하는 쪽은 `await` 필요.
- `POST /translate`(API-10) 구현 완료 (`app/api/routes/translate.py`). 실패 시 원문을 돌려주지 않고 502.
- Papago 호출 형식은 실제 응답 샘플(`backend/samples/raw/papago/`) 기준: 헤더 `X-NCP-APIGW-API-KEY-ID`/`X-NCP-APIGW-API-KEY`, JSON `{source, target, text}`, 응답 `message.result.translatedText`, 오류 `error.errorCode`.

## 2026-11-21 (#31)

- `main.py`에 `/api/qa/search`·`/api/law/sources/{id}` 라우터 등록, 서버 시작 시 `load_law_data()` 호출.
- 서류 평가(`/api/contracts/review`) 근거 검색을 `law_search.search_evidence`로 교체, 예전 `law_qa` 모듈 삭제.
- 최저임금은 `law-data/min-wage.json` 한 곳에서만 읽는다 (`services/wage.py`의 연도별 상수 삭제).
- `sync.wage`: 공공데이터 CSV에 아직 없는 고시 확정 연도를 `samples/raw/wage/announced.csv`로 보충 (2027년 10,700원). 같은 연도는 공공데이터 CSV 우선.
- `sync` 공통 `read_env()`: `.env` 값의 따옴표를 제거 (`LAW_GO_KR_OC="..."` 형태에서 법제처 사용자 검증 실패하던 문제).

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

- API 필드 이름은 snake_case, 응답은 공통 응답 형식(`{"success": true, "data": …}` / `{"success": false, "error": {"code", "message"}}`), 경로는 `/api/...` (CLAUDE.md의 camelCase·`{success, code, message, data}`·`/api/v1` 대신 `main`의 공통 응답과 `openapi.yaml` 기준). 없는 근거·연도는 `NOT_FOUND`(404).
- `calc.check_contract_wage`의 반환 키는 CLAUDE.md 초안과 같은 camelCase(`minimumWage` 등)이고, 서비스 내부용이다. API 응답 변환은 라우터에서 한다.
- 주휴수당은 `주휴시간 × max(시급, 최저임금)` — 레포 명세 BR-04를 따랐다 (CLAUDE.md 초안은 `시급` 기준). 팀 검토 필요.
- 계약 기간(`contract_period`)은 근거 법령(기간제법)을 수집하지 않아 체크리스트에서 뺐다.
