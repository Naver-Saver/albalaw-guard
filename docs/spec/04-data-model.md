# 04. 데이터 모델

> 상태: 초안 v0.1 · DB: Cloud DB for MySQL 8 (로컬은 SQLite)
> 원칙: **개인정보와 업로드 원본은 저장하지 않는다** (NFR-01). DB에는 공공 원문 캐시와 익명 처리 기록만 둔다.

## 저장하는 것 / 저장하지 않는 것

| 저장 O | 저장 X |
| --- | --- |
| 백문백답 원문 캐시, Chatbot FAQ 목록, AI 응답 캐시(입력 해시 키), 익명 처리 통계 | 계약서·명세서 이미지, 녹음 파일, OCR 원문 전체, 이름·주소·계좌·전화번호, 녹음 대본 |

## 테이블

### `law_qa` — 백문백답 원문 캐시 (FS-06)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | VARCHAR(64) PK | API 문항 식별자 |
| category | VARCHAR(50) | 분야 (근로자) |
| title | VARCHAR(500) | 질문 |
| answer | TEXT | 답변 본문 |
| keywords | VARCHAR(500) | 검색용 키워드 (쉼표 구분) |
| source_url | VARCHAR(500) | 원문 링크 |
| fetched_at | DATETIME | 수집 시각 |

인덱스: `FULLTEXT(title, answer)` (MySQL ngram parser) `[미정]`, 로컬은 LIKE 검색.

### `faq` — Chatbot 등록 FAQ 사본 (FS-03)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | INT PK AUTO | |
| question | VARCHAR(300) | 대표 질문 |
| answer | TEXT | 답변 |
| law_qa_id | VARCHAR(64) NULL FK→law_qa.id | 근거 문항 |

Chatbot 빌더에 등록한 내용과 같은 원본을 `backend/data/faq.csv`로 관리하고, 이 테이블은 시드로 채운다.

### `ai_cache` — AI 응답 캐시 (NFR-05)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| key | CHAR(64) PK | SHA-256(서비스명 + 정규화 입력) |
| service | VARCHAR(30) | studio / papago / voice … |
| value | MEDIUMTEXT | 응답(JSON 또는 base64) |
| created_at | DATETIME | |

TTL: 7일 (배치 또는 조회 시 만료 처리).

### `request_log` — 익명 처리 기록 (발표 지표용)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| id | BIGINT PK AUTO | |
| feature | VARCHAR(20) | ocr / review / recording / ask |
| route | VARCHAR(10) NULL | faq / studio |
| status | VARCHAR(10) | ok / fail |
| latency_ms | INT | |
| created_at | DATETIME | |

입력 값·결과 내용은 기록하지 않는다.

## 비영속 상태

- 녹음 작업(`RecordingJob`)은 서버 메모리(dict)에 저장, 조회 후 1시간 만료 (BR-10). 서버 재시작 시 사라져도 된다.
- Object Storage `uploads/` 프리픽스: 처리 직후 삭제 + 버킷 수명주기 1일 자동 삭제.
