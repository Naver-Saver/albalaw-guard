# 협업 컨벤션

## 0. 개발 방식 — SDD (명세 우선)

**명세 PR → 구현 PR** 순서로 진행합니다. 자세한 내용은 [docs/spec/README.md](spec/README.md)에 있어요.

1. 요구사항(`FR`) → 기능 명세(`FS`/`BR`/`AC`) → API 명세(`API`, `openapi.yaml`)를 먼저 `docs(spec): ...` PR로 합의
2. 구현 PR은 본문에 관련 명세 ID를 적고, 완료 조건(`AC`)으로 검증
3. 명세에 없는 API를 구현하면 CI(계약 테스트)가 실패합니다

## 1. 브랜치 전략 (GitHub Flow)

2주짜리 프로젝트라 `develop` 없이 **main + 작업 브랜치**만 씁니다.

- `main` — 항상 배포 가능한 상태. push되면 CD가 NCP 서버에 배포합니다. 직접 push 대신 PR로 합칩니다.
- 작업 브랜치 이름: `<type>/<scope>-<이슈번호>-<짧은-설명>`

```
feat/fe-12-upload-page
feat/ai-15-clova-ocr
fix/be-21-wage-rounding
chore/infra-3-ncp-server
content/data-30-dubbing-video
```

## 2. 커밋 메시지

```
type(scope): 요약

(선택) 본문 — 무엇을, 왜
(선택) Closes #12
```

- 요약은 **한국어 명령형/명사형, 50자 이내, 마침표 없음**
- 한 커밋에는 한 가지 변경만

### type

| type | 언제 |
| --- | --- |
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `refactor` | 동작 변화 없는 구조 개선 |
| `test` | 테스트 추가·수정 |
| `docs` | 문서 (PRD, README 등) |
| `style` | 포맷팅, 세미콜론 등 (로직 변화 없음) |
| `chore` | 설정, 의존성, 잡일 |
| `ci` | GitHub Actions 워크플로 |
| `build` | Dockerfile, 빌드 설정 |
| `perf` | 성능 개선 |
| `content` | 코드 외 콘텐츠: FAQ 데이터, Dubbing 영상, 발표자료 |
| `revert` | 되돌리기 |

### scope (= 역할)

| scope | 영역 |
| --- | --- |
| `fe` | 프론트엔드 (`frontend/`) |
| `be` | 백엔드 API (`backend/`) |
| `infra` | 서버·스토리지·DB·Docker·NCP 스크립트 (`infra/`) |
| `ai` | OCR·Speech·Studio·Chatbot·Voice·Papago 연동, 프롬프트 |
| `data` | 공공 API 연동·캐싱, FAQ 데이터 |
| `docs` | 문서 (PRD, README, 가이드) |
| `spec` | 명세 (`docs/spec/` — 요구사항·기능·API·데이터·AI 파이프라인) |
| `ci` | 워크플로 |
| `repo` | 저장소 전반 (템플릿, .gitignore 등) |

### 예시

```
feat(ai): CLOVA OCR로 계약서 시급·근무시간 추출
feat(fe): 계약서 사진 업로드 화면 추가
fix(be): 주휴시간 반올림 오류 수정
feat(data): 백문백답 근로자 분야 수집 스크립트 추가
content(data): Chatbot FAQ 20문항 등록
chore(infra): NCP 서버 초기화 스크립트 추가
docs(spec): FS-02 녹음 최대 길이 규칙(BR-07) 확정
docs(docs): PRD 일정 갱신
```

커밋 템플릿 사용: `git config commit.template .gitmessage`

## 3. PR

- **제목 = 커밋 컨벤션과 같은 형식** `type(scope): 요약` — `PR Title` 워크플로가 자동 검사합니다.
- **Squash merge**로 합칩니다 → PR 제목이 그대로 main의 커밋 메시지가 됩니다.
- 본문은 PR 템플릿을 채우고, `Closes #이슈번호`로 이슈를 연결합니다.
- CI(Backend·Frontend·Docker)가 통과해야 머지합니다. 리뷰어 1명 권장(필수 아님).
- 머지 후 브랜치는 자동 삭제됩니다.

## 4. 이슈·라벨

- 작업은 이슈로 만들고 GitHub Projects 보드(Todo / In Progress / Done)로 관리합니다.
- 라벨: `area: frontend` `area: backend` `area: ai` `area: data` / `type: feature` `type: bug` `type: docs` / `priority: P0` `P1` `P2`
- 라벨 일괄 생성: `scripts/setup-labels.sh <owner/repo>` (gh CLI 필요)

## 5. 코드 스타일

- Python: `ruff check` + `ruff format` (CI에서 검사)
- TypeScript: `oxlint` (CI에서 검사)
- 비밀값은 절대 커밋하지 않습니다. `.env.example`에 키 **이름만** 추가하세요.
