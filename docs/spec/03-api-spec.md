# 03. API 명세

> 기준 파일: [`openapi.yaml`](openapi.yaml) (이 문서는 사람이 읽기 위한 요약)
> 상태: v0.2 (공통 응답 형식 추가) · Base URL: `/api`

## 공통 규칙

| 항목 | 규칙 |
| --- | --- |
| 형식 | JSON (`application/json`), 업로드는 `multipart/form-data` |
| 필드 이름 | `snake_case` |
| 금액 | 정수(원), 시간은 소수 허용(시간 단위), 녹음 시각은 `start_ms`(밀리초) |
| 응답 형식 | **공통 응답** — 성공 `{"success": true, "data": {...}}` / 실패 `{"success": false, "error": {"code": "…", "message": "…"}}` (아래 표). 음성(mp3) 응답만 예외 |
| 추적 | 모든 응답 헤더에 `X-Request-ID` (요청에 있으면 그대로, 없으면 서버가 생성). 서버 로그에 같은 ID 기록 |
| 상태 코드 | 200 성공, 202 비동기 작업 생성, 400 업무 규칙 위반, 404 없음/만료, 413 파일 크기 초과, 422 검증 실패, 502 외부 서비스 실패 |
| 인증 | 없음 (MVP). 남용 방지는 Nginx rate limit `[미정]` |
| 언어 | `lang`: `ko`(기본) `en` `vi` `zh-CN`. `POST /payslips/review`·`POST /recordings/evidence`는 서버가 번역하고, `POST /contracts/review`의 `lang`은 **서버가 사용하지 않는다**(항상 한국어). 점검 결과 번역은 프런트가 `POST /translate`로 한다 |

## 오류 코드

| code | HTTP | 언제 | message 예 |
| --- | --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 요청 스키마 검증 실패 (`details`에 필드별 오류) | 입력값을 확인해 주세요. |
| `BAD_REQUEST` | 400 | 업무 규칙 위반 (지원하지 않는 연도 등) | 2030년 최저임금 데이터가 없습니다. |
| `UNSUPPORTED_FILE` | 400 | 허용하지 않는 파일 형식 (BR-01·07) | jpg, png, pdf 파일만 올릴 수 있어요. |
| `FILE_TOO_LARGE` | 413 | 크기 초과 | 10MB 이하 파일만 올릴 수 있어요. |
| `NOT_FOUND` | 404 | 없는 경로·만료된 작업 | 요청한 정보를 찾을 수 없어요. |
| `OCR_FAILED` | 502 | CLOVA OCR 호출 실패 | 글자를 읽지 못했어요. 다시 찍거나 직접 입력해 주세요. |
| `AI_UNAVAILABLE` | 502 | CLOVA Studio 등 AI 호출 실패 | AI 설명을 불러오지 못했어요. |
| `SERVICE_NOT_CONFIGURED` | 503 | 서버에 해당 서비스 키가 없음 | 서비스 설정이 아직 완료되지 않았어요. |
| `INTERNAL_ERROR` | 500 | 그 외 서버 오류 | 잠시 후 다시 시도해 주세요. |

## 엔드포인트 목록

| ID | Method · Path | 기능 | 명세 | 담당 | 상태 |
| --- | --- | --- | --- | --- | --- |
| API-01 | `GET /health` | 헬스체크 | — | BE | 구현 |
| API-02 | `POST /wage/check` | 최저임금·주휴수당 계산 | FS-01 BR-03·04 | BE | 구현 |
| API-03 | `POST /contracts/ocr` | 이미지 → 필드 추출 | FS-01 BR-01·02 | BE·AI | 구현 (#9·#10) |
| API-04 | `POST /contracts/review` | 계산 + 근거 설명 | FS-01 BR-03~06 | BE·AI | 구현 (#12) |
| API-05 | `POST /recordings` | 녹음 업로드 → 작업 생성 | FS-02 BR-07 | BE·AI | 합의 전 |
| API-06 | `GET /recordings/{job_id}` | 작업 상태·타임라인 | FS-02 BR-08~10 | BE·AI | 합의 전 |
| API-07 | `POST /ask/voice` | 음성 질문 | FS-03 BR-11~13 | BE·AI | 구현 |
| API-08 | `POST /ask/text` | 텍스트 질문 | FS-03 BR-11 | BE·AI | 구현 |
| API-09 | `POST /tts` | 음성 합성(mp3) | FS-01, FS-03 | AI | 구현 (#47) |
| API-10 | `POST /translate` | 번역 | FS-04 | AI | 구현 |
| API-11 | `GET /qa/search` | 근거(수동 Q&A·법령 조문) 키워드 검색 | FS-06 | DATA | 구현 |
| API-12 | `GET /law/sources/{source_id}` | 근거 원문 단건 조회 | FS-06 | DATA | 구현 |
| API-13 | `GET /wage/minimum` | 연도별 최저임금 조회 | FS-01 BR-03 | DATA | 구현 |
| API-14 | `POST /payslips/review` | 급여명세서 점검 | FS-01 BR-14 | DATA | 구현 |
| API-15 | `POST /recordings/evidence` | 대화 발언 근거·말로만 한 약속 안내 | FS-02 BR-15 | DATA | 구현 |

## 주요 요청·응답 예시

### API-02 `POST /wage/check`

```json
// 요청
{ "hourly_wage": 10000, "weekly_hours": 20, "year": 2026 }
// 응답 200 (이하 예시는 data 안의 내용만 표시)
{ "success": true, "data": {
  "year": 2026, "minimum_hourly": 10320, "notice": "고용노동부 고시 (2026년 적용분)",
  "hourly_wage": 10000, "meets_minimum": false, "shortfall_per_hour": 320,
  "weekly_hours": 20, "weekly_holiday_eligible": true,
  "weekly_holiday_hours": 4.0, "weekly_holiday_pay": 41280
} }
```

### API-11 `GET /qa/search?q=주휴수당&limit=3`

```json
{ "success": true, "data": { "items": [ { "id": "manual-009", "source": "MANUAL", "title": "주휴수당은 어떤 경우에 받을 수 있나요?", "snippet": "근로기준법 제55조는 …", "url": "https://www.law.go.kr/법령/근로기준법/제55조" } ] } }
```

`source`: `MANUAL`(조문 기반 수동 Q&A, 우선) · `LAW_API`(국가법령정보센터 조문). 결과가 없으면 `items: []`.

### API-12 `GET /law/sources/law-001872-17`

```json
{ "success": true, "data": { "id": "law-001872-17", "source": "LAW_API", "title": "근로기준법 제17조(근로조건의 명시)", "text": "제17조(근로조건의 명시)\n① …", "url": "https://www.law.go.kr/…", "related_article_ids": [] } }
```

없는 id는 404 `NOT_FOUND` (`근거 원문을 찾을 수 없어요.`). 수동 Q&A는 `related_article_ids`에 연결된 조문 id를 담는다.

### API-13 `GET /wage/minimum?year=2026`

```json
{ "success": true, "data": { "year": 2026, "hourly_wage": 10320, "period_start": "2026-01-01", "period_end": "2026-12-31", "is_fallback": false } }
```

`year` 생략 시 올해 값, 올해 데이터가 없으면 가장 최근 연도로 대체하고 `is_fallback: true`. `year`를 지정했는데 데이터가 없으면 404 `NOT_FOUND`.

### API-14 `POST /payslips/review`

```json
// 요청 (사용자가 확인·수정한 값. 시급·주 소정근로시간은 알 때만)
{ "employee_name": "가상인물", "pay_date": "2026-11-10",
  "items": [ { "name": "기본급", "amount": 900000 } ],
  "deductions": [ { "name": "국민연금", "amount": 40000 } ],
  "total_pay": 950000, "net_pay": 910000, "calculation_method": null,
  "hourly_wage": 9000, "weekly_hours": 20, "year": 2026, "lang": "ko" }
// 응답 200 (data 안의 내용)
{ "success": true, "data": {
  "totals": { "items_sum": 900000, "deductions_sum": 40000, "total_pay": 950000, "net_pay": 910000,
              "expected_net_pay": 910000, "total_matches": false, "net_matches": true,
              "mismatches": [ { "field": "totalPay", "expected": 900000, "actual": 950000, "difference": 50000 } ] },
  "wage": { "year": 2026, "minimum_wage": 10320, "hourly_wage": 9000, "is_below_minimum": true,
            "shortfall_per_hour": 1320, "weekly_holiday_eligible": true,
            "weekly_holiday_hours": 4.0, "weekly_holiday_pay": 41280 },
  "missing": [ { "item": "항목별 계산방법", "field_key": "calculation_method", "source_ids": ["law-003058-27-2"], "conditional": true } ],
  "items": [ { "level": "check", "title": "지급 항목 합계와 총액이 달라요", "description": "지급 항목을 더하면 900,000원인데 총액은 950,000원이에요. 50,000원 차이가 나니 빠진 항목이 있는지 확인해 보세요." } ],
  "sources": [ { "id": "manual-022", "title": "급여명세서를 꼭 받아야 하나요?", "snippet": "…", "url": "https://www.law.go.kr/…" } ],
  "disclaimer": "이 결과는 법률 자문이 아니에요. …" } }
```

`items`의 문장·금액은 코드 템플릿이 만들고(NFR-08), `lang`이 ko가 아니면 `items`·`disclaimer`만 번역한다. 이름·지급일은 있는지만 확인하고 응답에 돌려주지 않는다.

### API-15 `POST /recordings/evidence`

```json
// 요청: API-06 타임라인 항목 (최대 50개)
{ "entries": [ { "start_ms": 12000, "speaker": "화자 B", "text": "이번 달부터 시급 만 원으로 할게", "category": "임금" } ], "lang": "ko" }
// 응답 200 (data 안의 내용)
{ "success": true, "data": {
  "entries": [ { "index": 0, "start_ms": 12000, "verbal_promise": true,
                 "advice": "말로만 한 조건이에요. 계약서나 문자로 남겨 달라고 요청해 보세요.",
                 "sources": [ { "id": "manual-005", "title": "…", "snippet": "…", "url": "…" } ] } ],
  "checklist_for_next_time": [ "시급·근무시간·휴게시간을 계약서에 적어 달라고 요청하세요.", "…" ],
  "disclaimer": "이 결과는 법률 자문이 아니에요. …" } }
```

서버에 저장하지 않는다. `lang`이 ko가 아니면 `advice`·`checklist_for_next_time`·`disclaimer`만 번역한다.

### API-03 `POST /contracts/ocr`

```
file=@contract.jpg, doc_type=contract
```
```json
{
  "doc_type": "contract",
  "raw_text": "근로계약서 ... 시급 10,000원 ... 월~금 10:00~14:00 ...",
  "extracted": {
    "hourly_wage":   { "value": 10000, "confidence": "high", "source_text": "시급 10,000원" },
    "weekly_hours":  { "value": 20,    "confidence": "low",  "source_text": "월~금 10:00~14:00" },
    "work_days":     { "value": ["월","화","수","목","금"], "confidence": "high" },
    "break_minutes": { "value": null,  "confidence": "low" }
  }
}
```

### API-04 `POST /contracts/review`

```json
// 요청
{ "hourly_wage": 10000, "weekly_hours": 20, "work_days": ["월","화","수","목","금"], "break_minutes": 0, "year": 2026 }
// 응답 200
{
  "calculation": { "...": "API-02 응답과 동일" },
  "items": [
    { "level": "check", "title": "시급이 최저임금보다 낮아요", "description": "2026년 최저시급은 10,320원이에요. 시간당 320원 차이가 있어요." },
    { "level": "check", "title": "주휴수당 대상이에요", "description": "주 15시간 이상 일하면 주휴수당이 있어요. 계산상 주 41,280원이에요." }
  ],
  "explanation": "…(CLOVA Studio 설명, 숫자 검증 통과분만)…",
  "sources": [ { "id": "…", "title": "주휴수당은 누가 받을 수 있나요?", "snippet": "…" } ],
  "disclaimer": "이 결과는 법률 자문이 아니에요. 고용노동부(1350), 대한법률구조공단(132)에 상담할 수 있어요."
}
```

> `items`의 문장과 금액은 **백엔드 템플릿**이 만들고, `explanation`만 LLM이 만든다 (NFR-08).

### API-05 / API-06 녹음

```json
// POST /recordings → 202
{ "job_id": "rec_7f3a", "status": "queued" }

// GET /recordings/rec_7f3a → 200 (완료)
{
  "job_id": "rec_7f3a", "status": "done", "error": null,
  "speakers": ["화자 A", "화자 B"],
  "timeline": [
    { "start_ms": 12000, "speaker": "화자 A", "text": "이번 달부터 시급 만 원으로 할게", "category": "임금" }
  ],
  "transcript": "…"
}
```

### API-07 / API-08 질문

```json
// POST /ask/text 요청 (question 2~300자). POST /ask/voice 는 multipart `file` (60초 이하, 10MB 이하)
{ "question": "주 3일 하루 5시간 일하면 주휴수당 나와?" }
// 응답 200 (data 안의 내용)
{ "success": true, "data": { "question": "주 3일 하루 5시간 일하면 주휴수당 나와?", "route": "studio",
  "answer": "주 3일 하루 5시간이면 주 15시간이라 주휴수당 대상이 될 수 있어요. …",
  "sources": [ { "id": "manual-011", "title": "주 15시간 미만으로 일하면 …", "snippet": "…", "url": "https://www.law.go.kr/…" } ] } }
```

`route`: `faq`(Chatbot FAQ, 신뢰도 0.7 이상) · `studio`(근거 검색 + Studio 설명) · `none`(근거를 못 찾았거나 설명을 못 만들었을 때 상담 안내, 찾은 근거는 `sources`에 남김).
음성에서 인식된 말이 없으면 200 + `route: none`, `answer: "잘 못 들었어요. 텍스트로 질문해 주세요."`(BR-13). 60초 초과(wav·mp3는 서버가 길이 확인)나 읽을 수 없는 음성은 400, 10MB 초과는 413, 인식 서비스 장애는 502. 녹음은 저장하지 않는다.

## 변경 이력

| 날짜 | 변경 | PR |
| --- | --- | --- |
| 2026-11-20 | 초안 작성 (API-01~11) | #1 |
| 2026-11-20 | 공통 응답 형식·오류 코드·X-Request-ID 추가 (v0.2) | #8 |
| 2026-11-21 | API-07·08 구현 상태 갱신, 응답 설명·오류 보강 | #58 |
| 2026-11-21 | API-14(급여명세서 점검)·API-15(대화 발언 근거) 추가 | — |
| 2026-11-21 | API-11 응답에 `source` 추가·설명 변경, API-12(근거 원문)·API-13(최저임금 조회) 추가 (공통 응답 형식 적용) | #21 |
