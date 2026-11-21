# 05. AI 파이프라인 명세

> 상태: 초안 v0.1 · 담당: AI 파이프라인
> 각 외부 서비스의 **입출력 계약·인증·타임아웃·실패 처리**를 정의한다. 코드는 `backend/app/services/<서비스>.py` 하나씩.
> 엔드포인트 도메인은 NCP 콘솔(각 서비스/Application 상세)에 표시된 값을 우선한다.

## 인증 방식 요약

| 서비스 | 인증 | 환경변수 |
| --- | --- | --- |
| CLOVA OCR | 헤더 `X-OCR-SECRET` + 도메인별 Invoke URL | `CLOVA_OCR_INVOKE_URL`, `CLOVA_OCR_SECRET` |
| CLOVA Speech | 헤더 `X-CLOVASPEECH-API-KEY` + 도메인별 Invoke URL | `CLOVA_SPEECH_INVOKE_URL`, `CLOVA_SPEECH_SECRET` |
| CLOVA Studio | `Authorization: Bearer <API 키(nv-…)>` + `X-NCP-CLOVASTUDIO-REQUEST-ID` | `CLOVA_STUDIO_API_KEY`, `CLOVA_STUDIO_REQUEST_ID`, `CLOVA_STUDIO_MODEL` |
| CLOVA Chatbot | 헤더 `X-NCP-CHATBOT_SIGNATURE` (요청 본문 HMAC-SHA256, Secret Key) | `CLOVA_CHATBOT_INVOKE_URL`, `CLOVA_CHATBOT_SECRET` |
| CSR · CLOVA Voice | 헤더 `X-NCP-APIGW-API-KEY-ID`, `X-NCP-APIGW-API-KEY` — **AI·NAVER API > Application** (CSR·Voice 선택) | `AINAVER_CLIENT_ID`, `AINAVER_CLIENT_SECRET` |
| Papago | 같은 헤더 이름이지만 **Papago Translation > Application** 에서 따로 발급 (AI·NAVER 키로 호출하면 401) | `PAPAGO_CLIENT_ID`, `PAPAGO_CLIENT_SECRET` |
| Object Storage | S3 호환 (NCP Access/Secret Key) | `NCP_ACCESS_KEY`, `NCP_SECRET_KEY` |

## AI-01. CLOVA OCR (FS-01)

- 요청: `POST {INVOKE_URL}` (도메인 > API Gateway 연동의 APIGW Invoke URL) · `{"version":"V2","requestId":uuid,"timestamp":0,"lang":"ko","images":[{"format":"jpg","name":"doc","data":base64}]}`
- 이미지는 **base64 `data`로 직접 전송**한다. 수업 실습의 `url` 방식은 이미지를 Object Storage에 **공개**로 올려야 해서 계약서(개인정보)에는 쓰지 않는다.
- 사용 필드: `images[0].fields[].inferText`, `lineBreak` → 줄 단위 텍스트로 합침
- 타임아웃 15초, 실패 시 502 + "글자를 읽지 못했어요"
- `[미정]` 템플릿 OCR: 샘플 계약서 양식이 고정되면 템플릿 도메인으로 전환 검토

## AI-02. CLOVA Speech 장문 인식 (FS-02)

- 요청: `POST {INVOKE_URL}/recognizer/object-storage` · `{"dataKey":"uploads/<file>","language":"ko-KR","completion":"async","diarization":{"enable":true}}`
- 결과: 응답의 작업 토큰으로 상태 조회 → `segments[].start, speaker.label, text`
- 사전 준비: 장문 인식 도메인 생성(Basic, 화자 인식 사용, 인식 대상·결과 경로 = 버킷 `albalaw-uploads`)
- 수업은 빌더(콘솔)로만 실행했으므로, API 호출용 Invoke URL·Secret Key 위치는 도메인 생성 후 확인해 `[확인 필요]`
- 폴링 간격 3초, 최대 5분

## AI-03. CLOVA Studio — 점검 결과 설명 (FS-01)

- 요청: `POST https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/{CLOVA_STUDIO_MODEL}` (테스트 API 키는 `testapp` 경로), 모델 `HCX-005`, `temperature 0.3`, `maxTokens 600`
- 대안: OpenAI 호환 `https://clovastudio.stream.ntruss.com/v1/openai` (`openai` 패키지, 4·5차시 실습과 동일)
- 시스템 프롬프트 (초안):

```
너는 아르바이트 근로자에게 근로조건을 쉬운 말로 설명하는 도우미다.
규칙:
1. 아래 [계산 결과]와 [근거 원문]에 있는 내용만 사용한다. 없는 내용은 "확인이 필요해요"라고 말한다.
2. 금액·시간 등 숫자는 [계산 결과]에 있는 값만 그대로 쓴다. 새로 계산하지 않는다.
3. "불법", "위법", "신고하세요" 같은 단정 표현을 쓰지 않는다.
4. 3~5문장, 존댓말, 중학생도 이해할 수 있게 쓴다.
5. 마지막 문장은 고용노동부(1350) 또는 대한법률구조공단(132) 상담 안내로 끝낸다.
```

- 사용자 메시지: `[계산 결과] {calculation JSON}\n[근거 원문] {sources: title + answer 앞 800자} × 최대 3건`
- 후처리: BR-05 숫자 검증 (설명 속 숫자 ⊆ calculation 값 + 1350, 132, 15, 40, 8)

## AI-04. CLOVA Studio — 대화 타임라인 (FS-02)

- 입력: 화자·시각이 붙은 세그먼트 목록 (최대 약 6,000자, 넘으면 분할 처리)
- 출력: **JSON 배열만** `[{"start_ms":int,"speaker":str,"text":str,"category":"임금|근무시간|휴게·휴일|약속·지시|기타"}]`
- 파싱 실패 시 1회 재시도, 그래도 실패하면 대본만 반환

## AI-05. 질문 라우팅 — CSR → Chatbot → Studio (FS-03)

- CSR: `POST https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang=Kor`, `Content-Type: application/octet-stream`, Body에 음성 바이너리, 60초 이하
- Chatbot: `{"version":"v2","userId":<임시 세션 ID>,"timestamp":ms,"bubbles":[{"type":"text","data":{"description":질문}}],"event":"send"}`
  - FAQ 판정(BR-11): 기본(실패) 답변이 아니고 신뢰도 기준 통과
  - 실제 응답(`samples/raw/chatbot/`): 일치 시 `bubbles[0].information`에 `score`·`matchingType`(`exactMatch`/`model`)·`scenarioName`, 일치 없음은 `defaultMsgType`/`failureMsgId`(score 없음). 서명 = base64(HMAC-SHA256(Secret, 요청 본문 바이트)).
  - 유의: `model` 매칭은 0.70~0.96 점수대에서 엉뚱한 FAQ가 걸리기도 한다(예: "주 10시간 일하면 주휴수당 있어?" → 연장근로 FAQ 0.73). 근무시간을 말한 질문은 Chatbot을 건너뛴다.
  - CSR 실제 응답(`samples/raw/csr/`): 성공 `{"text"}`, 60초 초과 → 500 `STT006`.
- Studio(미매칭 시): AI-03과 같은 규칙, [계산 결과] 대신 [질문]

## AI-06. Papago 번역 (FS-04)

- `POST https://papago.apigw.ntruss.com/nmt/v1/translation` · JSON `{"source":"ko","target":…,"text":…}` → `message.result.translatedText`
- `target ∈ {en, vi, zh-CN}`, 문장 단위 호출 + 메모리 캐시

## AI-07. CLOVA Voice (FS-01, FS-03)

- `POST https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts` · form `speaker=nara&speed=0&format=mp3&text=…`
- 화자 기본 `nara` (리허설에서 변경 가능), 1회 최대 2,000자
- 결과 캐싱(텍스트+화자 해시)

## 공통 실패 처리 (NFR-04)

| 상황 | 처리 |
| --- | --- |
| 타임아웃·5xx | 1회 재시도 후 502 |
| 4xx(키·권한) | 재시도 없이 502 + 서버 로그에 서비스명·상태코드 (키 값은 로그 금지) |
| `DEMO_MODE=true` | 실패 시 `backend/data/demo/<service>.json` 캐시 응답 반환 |
