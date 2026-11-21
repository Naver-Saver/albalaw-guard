# Saver(알바생 노동권 지킴이) 기술 문서

작성: 이동건 · 2026-11-21

Saver는 아르바이트생이 근로계약서·급여명세서 사진을 올리면 시급·근무시간을 읽어 최저임금·주휴수당·휴게시간을 점검하고, 법령 근거와 함께 쉬운 말로 설명해 주는 웹 서비스다. 질문(텍스트·음성)과 대화 녹음 정리도 지원한다.

| 항목 | 내용 |
| --- | --- |
| 과정 | 네이버 클라우드 소버린 AI 리터러시 과정 팀 프로젝트 (B안) |
| 운영 주소 | http://101.79.9.131 |
| 저장소 | [Naver-Saver/albalaw-guard](https://github.com/Naver-Saver/albalaw-guard) (public) |
| 기준 버전 | main `fbd41c5` (PR #81), 2026-11-21 배포 |
| 명세 | `docs/PRD.md`, `docs/spec/`(요구사항·기능·API·데이터·AI 파이프라인), `docs/spec/openapi.yaml` |

금액·시간 계산은 모두 백엔드 코드가 하고, LLM은 근거 원문을 바탕으로 설명만 쓴다. 결과는 법률 자문이 아니며 고용노동부 1350·대한법률구조공단 132 상담을 안내한다.

## 1. 기술 스펙

프론트는 React SPA, 백엔드는 FastAPI 단일 서버이며, DB 없이 NAVER Cloud Object Storage(JSON)와 서버 메모리만 쓴다.

| 영역 | 기술 | 비고 |
| --- | --- | --- |
| 프론트엔드 | React 19, Vite 8, TypeScript 7, oxlint | 해시 라우팅(`#/`, `#/guide`, `#/workspace`), 빌드 결과를 Nginx가 서빙 |
| 백엔드 | Python 3.12, FastAPI, Uvicorn(워커 1), pydantic-settings, httpx, boto3 | 공통 응답 `{success, data}` / `{success:false, error:{code, message}}`, 요청마다 `X-Request-ID` |
| 문서 인식 | CLOVA OCR | 계약서·급여명세서 글자 추출 → 규칙 기반 항목 추출(BR-02) |
| 설명·요약 | CLOVA Studio HCX-005 | 근거 기반 설명, 녹음 타임라인 분류. 답변 속 숫자는 코드가 검증(number guard) |
| 질문 | CLOVA Chatbot(FAQ), CLOVA Speech Recognition(CSR) | FAQ에 없으면 Studio 근거 답변, 음성 질문 60초 이하 |
| 녹음 정리 | CLOVA Speech(장문·화자 분리) | 비동기 인식, 결과 JSON을 버킷에서 읽고 즉시 삭제 |
| 번역·음성 | Papago, CLOVA Voice | 한국어·English·Tiếng Việt·中文, 답변 듣기 mp3 |
| 근거 데이터 | 국가법령정보센터 Open API, 고용노동부 최저임금 CSV, 수동 Q&A | 조문 329건·Q&A 36건·최저임금 14개 연도(2027년 10,700원 포함), 키워드 검색(임베딩 없음) |
| 저장 | NCP Object Storage `albalaw-uploads` | `law-data/*.json`, `meta/sync_log.json`, 녹음 원본은 처리 후 삭제 |
| 인프라 | NCP Server(KVM, KR-2, Ubuntu, 디스크 50GB), Docker Compose, NCP Container Registry | 프론트 Nginx(80) → `/api` 프록시 → 백엔드(8000), SSH는 키 인증만 |
| CI/CD | GitHub Actions | PR마다 lint·테스트·Docker 빌드·PR 제목 검사, main 머지 시 이미지 빌드·배포·스모크 테스트 |
| 정기 작업 | 서버 cron | 매주 월 04:17 KST 법령·최저임금 수집(`python -m sync.all`), 서버는 600초마다 다시 읽음 |
| 테스트 | pytest(백엔드 약 300건), node:test(프론트 41건), ruff | OpenAPI 계약 테스트, 라우터 등록 누락 검사 포함 |

업로드 제한은 문서 10MB(jpg·png·pdf), 녹음 200MB·10분(m4a·mp3·wav), 음성 질문 10MB·60초다. CLOVA Dubbing은 교육 영상 제작용(콘텐츠)으로, 서비스 코드에는 연결하지 않는다.

## 2. 아키텍처

브라우저 요청은 Nginx가 받아 `/api`만 FastAPI로 넘기고, FastAPI가 NAVER Cloud AI와 Object Storage를 호출한다. 근거 데이터는 서버 cron이 매주 법령 API에서 받아 버킷에 올린다.

![시스템 구성: 서버 1대, 외부 서비스 3그룹](images/architecture.png)

### 기능별 요청 흐름

1. 계약서 점검: 업로드 → CLOVA OCR → 규칙 기반 항목 추출(시급·주 소정근로시간·근무요일·휴게·적용 연도) → 확인 화면에 자동 입력 → 사용자가 확인·수정 → 최저임금·주휴수당 계산 → 항목별 근거 검색 → Studio 설명(숫자 검증) → 결과
2. 급여명세서 점검: 업로드 → OCR → 지급·공제 항목, 합계 추출 → 확인·수정 → 합계 검산·필수 기재 항목·최저임금 → 근거
3. 질문: 텍스트 또는 음성(CSR) → Chatbot FAQ → 없으면 근거 검색 + Studio 답변 → 선택 언어로 번역(Papago), 답변 듣기(Voice)
4. 녹음 정리: 동의 + 업로드 → Object Storage → CLOVA Speech 비동기 인식(화자 분리) → 결과 JSON 읽기 → Studio 타임라인 분류 → 원본·결과 삭제 → 발언별 근거·"말로 한 약속" 안내

### API

| 기능 | 메서드·경로 |
| --- | --- |
| 상태 | `GET /api/health` |
| 계약서 | `POST /api/contracts/ocr`, `POST /api/contracts/review` |
| 급여명세서 | `POST /api/payslips/review` (OCR은 `doc_type=payslip`) |
| 최저임금 | `GET /api/wage/minimum`, `POST /api/wage/check` |
| 근거 | `GET /api/qa/search`, `GET /api/law/sources/{source_id}` |
| 질문 | `POST /api/ask/text`, `POST /api/ask/voice` |
| 녹음 | `POST /api/recordings`, `GET /api/recordings/{job_id}`, `POST /api/recordings/evidence` |
| 번역·음성 | `POST /api/translate`, `POST /api/tts` |

### 데이터와 개인정보

- DB는 쓰지 않는다. 근거 데이터는 버킷 JSON을 600초 캐시로 읽고, 녹음 작업 상태는 서버 메모리에 1시간만 둔다(그래서 Uvicorn 워커는 1개).
- 문서 이미지는 메모리에서만 처리하고 저장하지 않는다. 녹음 원본과 CLOVA Speech 결과 JSON은 처리 직후 지운다.
- 키는 서버 `backend.env`(권한 600)와 GitHub Secrets에만 두고 저장소에는 넣지 않는다.

## 3. 발전 과정

이틀 동안 명세·인프라 → 백엔드 뼈대 → 데이터·AI 모듈 → 화면 → 실제 API 연동 순으로 다섯 단계를 거쳤다. 최신 단계부터 적는다.

| 날짜 | 단계 | 내용 |
| --- | --- | --- |
| 11-21 | 5. 실제 연동·안정화 | 모든 화면을 실제 API에 연결(계약서·급여명세서 점검, 텍스트·음성 질문, 답변 번역·듣기, 녹음 정리). OCR 추출값 자동 입력, 녹음이 항상 실패하던 CLOVA Speech 결과 읽기 문제 해결 |
| 11-21 | 4. 화면 | 공통 UI, 소개·이용 안내, 언어 선택·문서 업로드, 추출 확인, 점검 결과, 질문, 대화 기록 화면 |
| 11-21 | 3. 데이터·AI 모듈 | 법령 근거 수집·검색, 최저임금 데이터 일원화, Object Storage 연동, Papago 번역, CLOVA Voice, 질문 API, 급여명세서 점검·발언 근거 API, 법령 주간 수집 cron. 서버 디스크 10GB → 50GB |
| 11-21 | 2. 백엔드 뼈대 | 공통 응답·오류 처리, OCR 항목 추출, Studio 공통 모듈·숫자 검증, 서류 평가, 첫 자동 배포 |
| 11-20 | 1. 기획·인프라 | PRD·SDD 명세, NCP 서버·레지스트리·CI/CD, DB 제거 → Object Storage 구조 결정, 수업 자료 기준 키 체계 정정, CLOVA Chatbot FAQ 구성 |

도중 바뀐 결정: 법제처 생활법령 API가 호출 오류(코드 04)로 막혀 국가법령정보센터 조문 + 수동 Q&A로 바꿨고, 프로젝트 기간을 2주에서 1주로 줄였다.

## 4. 조원별 역할

네 명이 백엔드 뼈대·배포, 데이터·근거, 저장소·음성, 화면을 나눠 맡았다. 이름 칸은 GitHub 아이디이며, 실명은 팀이 채워 주세요.

| 담당 | 주요 산출물 | 역할 |
| --- | --- | --- |
| 이동건 (Movinggun-bit) | PRD·SDD 명세, FastAPI 뼈대·공통 응답, CLOVA OCR·항목 추출, Studio 공통 모듈·숫자 검증, 서류 평가, NCP 서버·CI/CD·법령 수집 cron, Chatbot 도메인 구성, API 화면 연동 마무리 | 백엔드 뼈대·서류 점검·인프라 |
| k-dong1 | 법령 조문·최저임금 수집(`sync`), 근거 검색(`law_search`)·계산(`calc`), Papago 번역, 급여명세서 점검·발언 근거 API, 텍스트·음성 질문 API, 버킷 읽기 캐시 | 데이터·근거·질문 |
| SippZa | Object Storage 공통 모듈, CLOVA Speech 녹음 정리 API, 법령 로더 버킷 연동, CLOVA Voice 음성 합성 API | 저장소·녹음·음성 |
| Unknown02-coder | 공통 UI·퍼블리싱, 소개·이용 안내, 언어 선택·문서 업로드, 추출 확인·점검 결과·질문·대화 기록 화면, OCR·번역·텍스트·음성 질문 연동 | 프론트엔드 |

PRD의 초기 역할안(프론트엔드 / 백엔드·인프라 / AI 파이프라인 / 데이터·콘텐츠)과 실제 분담은 위 표처럼 달라졌다. Chatbot FAQ 보강, Dubbing 교육 영상, 발표자료 담당은 팀 확인이 필요하다.
