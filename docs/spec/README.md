# 명세 문서 (SDD — Spec-Driven Development)

이 프로젝트는 **명세를 먼저 쓰고, 명세대로 구현하고, 명세로 검증**합니다.
코드와 명세가 다르면 **명세가 기준**이고, 바꾸고 싶으면 명세부터 고칩니다.

## 문서 구성과 추적 체계

| 순서 | 문서 | ID 체계 | 질문 |
| --- | --- | --- | --- |
| 0 | [PRD](../PRD.md) | F1~F6 | 왜, 누구를 위해, 어디까지 만드나 |
| 1 | [요구사항 분석](01-requirements.md) | `FR-xx`, `NFR-xx` | 시스템이 **무엇을** 해야 하나 |
| 2 | [기능 명세](02-functional-spec.md) | `FS-xx`, `BR-xx`, `AC-xx` | 각 기능이 **어떻게** 동작하나 (입력·출력·규칙·예외·완료 조건) |
| 3 | [API 명세](03-api-spec.md) + [`openapi.yaml`](openapi.yaml) | `API-xx` | 프론트↔백엔드 **계약** |
| 4 | [데이터 모델](04-data-model.md) | 테이블명 | 무엇을 저장하고 무엇을 저장하지 않나 |
| 5 | [AI 파이프라인 명세](05-ai-pipeline.md) | `AI-xx` | 외부 AI 서비스 입출력 계약, 프롬프트, 라우팅 |

```
PRD(F1) ─► FR-01..07 ─► FS-01 (BR-01..05, AC-01..06) ─► API-03, API-04 ─► 테스트
```

모든 구현 PR은 위 ID 중 하나 이상을 참조해야 합니다.

## 작업 흐름

1. **명세 PR** — `docs(spec): ...`
   - 해당 FR/FS/API 항목을 추가·수정하고, `openapi.yaml`도 함께 고칩니다.
   - 담당 역할 간 합의(특히 프론트↔백엔드는 API 명세)가 끝나면 머지합니다.
2. **구현 PR** — `feat(be|fe|ai|data): ...`
   - PR 본문의 "관련 명세"에 ID를 적습니다. 예: `FS-01 / BR-02 / API-04`
   - 명세의 `AC-xx`(완료 조건)를 테스트나 확인 절차로 증명합니다.
3. **명세와 다르게 구현해야 하면** 구현 PR에서 몰래 바꾸지 말고 명세 PR을 먼저 올립니다.

## 자동 검사

- `backend/tests/test_openapi_contract.py` — FastAPI가 노출하는 모든 `METHOD path`가 `openapi.yaml`에 정의되어 있는지 CI에서 검사합니다. 명세에 없는 API를 만들면 CI가 실패합니다.
- 프론트엔드는 `openapi.yaml`을 기준으로 타입을 작성합니다 (`[미정]` openapi-typescript로 자동 생성).

## 상태 표기

각 항목의 상태: `초안` → `합의` → `구현` → `검증`
