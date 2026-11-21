# 변경 이력 (파트 A: 데이터·근거·명세)

명세(`docs/spec/`)와 파트 A가 제공하는 인터페이스(함수 시그니처·응답 형식)를 바꿀 때 여기에 기록합니다.
시그니처가 바뀌면 B·C에게 공지가 필요합니다.

## 2026-11-21 (질문 API, #58)

- **API-08 `POST /ask/text`**, **API-07 `POST /ask/voice`** 구현 (명세는 이미 있었음, `03` 설명·오류 보강, FS-03 BR-12 확정).
- 서비스: `clova_chatbot.py`(FAQ, 서명·판정), `clova_csr.py`(음성 인식), `ask.py`(Chatbot → faq / 근거 검색 + Studio → studio / none), `audio.py`(wav·mp3 길이). 프롬프트 `app/prompts/ask_explain_system.txt`.
- 내 근무시간을 말한 질문('주 N일 하루 M시간')은 Chatbot을 건너뛰고 `calc.weekly_holiday_hours`(새 공개 함수)로 계산해 Studio에 넘긴다. 설명의 숫자는 질문·근거·계산에 있는 값만 허용(`number_guard`).
- 라우터를 `main.py`에 등록했다 (담당자 허락).

## 2026-11-21 (급여명세서 점검·대화 발언 근거)

### 추가한 API (명세: `openapi.yaml`, `02` FS-01 BR-14·AC-19 / FS-02 BR-15·AC-20, `03` API-14·15)

- **API-14 `POST /payslips/review`** — 급여명세서 점검. 사용자가 확인·수정한 값(지급·공제 항목, 총액, 실지급액, 필요하면 시급·주 소정근로시간)으로 코드가 검산(`calc.check_payslip_totals`)·필수 항목 누락(`checklist.find_missing("PAYSLIP")`)·최저임금·주휴수당 항목 유무·위약금/교육비 등 공제 이름을 확인하고 법령 근거를 붙인다. 서비스 `app/services/payslip_review.py`, 라우터 `app/api/routes/payslips.py`.
- **API-15 `POST /recordings/evidence`** — 대화 타임라인 발언(API-06)의 근거와 '말로만 한 약속' 안내. 서비스 `app/services/timeline_evidence.py`, 라우터 `app/api/routes/evidence.py`. 저장하지 않는다.
- 두 API 모두 `lang != "ko"`면 설명 문장만 번역(`translate_texts`/`translate_result`, Papago 실패 시 원문).
- **`main.py`(B 소유)에 `payslips`·`evidence` 라우터 등록이 필요하다** → `docs/requests/B-law-router-and-data-deploy.md`.

### 데이터 보정 (`law-data/qna-manual.json`)

- manual-012 분류명에서 "주휴수당"을 빼서 "주휴수당" 검색 시 요건 문항(manual-010)이 먼저 나오게 함. 구어 검색을 위해 manual-015·016(야근·잔업), manual-027·028(나오지 마·잘렸어) 키워드 추가. 반영하려면 배포 후 `python -m sync.all`(업로드) 필요.

## 2026-11-21 (#40 법령 데이터 읽기 보강)

- `law_data.read_json`(실제 NCP 버킷에서 읽을 때만): 읽은 JSON을 프로세스 안에 `LAW_DATA_CACHE_SEC`(기본 600초) 동안 캐시하고(#44 정기 수집분은 캐시 만료 후 재시작 없이 반영, 재조회 실패 시 직전 버킷 값 유지), 실패·없음은 60초간 기억해 그동안 로컬 파일을 쓴다. 읽기 전용 클라이언트는 연결 3초·읽기 10초·재시도 1회의 짧은 타임아웃. `calc.get_min_wage` 등이 요청마다 `read_json`을 호출해도 버킷 호출이 반복되지 않는다. In-Memory 스토리지·`LAW_DATA_DIR`는 기존 동작 그대로.
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

## 2026-11-21 (#43)

- 백엔드 이미지에 `sync/`·`samples/raw/wage/` 포함, 서버 cron으로 주 1회 `python -m sync.all` (법령 조문·최저임금·수동 Q&A → Object Storage). `docs/DEPLOY.md` §7
- `law_data.read_json`: Object Storage 결과를 `LAW_DATA_CACHE_SEC`(기본 600초) 동안 캐시. `LAW_DATA_DIR` 지정 시 캐시 안 함. `clear_cache()` 추가
- `law_search`: 캐시 시간이 지나면 다시 적재(`load_law_data(keep_on_empty=True)`), 새로 읽은 결과가 비면 기존 인덱스 유지

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
