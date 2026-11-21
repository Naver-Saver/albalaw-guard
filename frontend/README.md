# 알바생 노동권 지킴이 프론트엔드

팀 저장소의 React + TypeScript + Vite 프로젝트입니다. 이 폴더를 이후 프론트엔드 작업 기준으로 사용합니다.

## 실행

Node.js 22.12 이상을 사용합니다. 저장소 루트에서:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

터미널에 표시된 개발 서버 주소를 엽니다(기본 `http://localhost:5173`). Windows PowerShell에서 `npm.ps1` 실행 정책 오류를 피하려면 위처럼 `npm.cmd`를 사용하면 됩니다. macOS/Linux에서는 `npm`을 사용합니다.

백엔드는 별도 터미널에서 루트 README의 방법으로 실행합니다. Vite가 `/api` 요청을 `http://localhost:8000`으로 전달합니다. 현재 공통 UI 미리보기는 API를 호출하지 않아 백엔드 없이도 확인할 수 있습니다.

```powershell
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

`build`는 TypeScript 검사 후 `dist/`에 배포 파일을 생성합니다. 현재 Vite 설정에서는 `preview`도 `/api` 프록시를 사용하므로 API 확인 시 백엔드를 함께 실행합니다. Docker·Nginx를 포함한 통합 확인은 저장소 루트의 `docker compose up --build`를 사용합니다.

## 현재 파일과 기준

| 경로 | 역할 |
| --- | --- |
| `src/main.tsx` | React 진입점과 전역 스타일 로드 |
| `src/App.tsx` | 작업 레이아웃과 공통 UI 미리보기 연결 |
| `src/components/common/` | 버튼·폼·카드·배지·화면 상태 공통 요소 |
| `src/components/layout/` | 헤더·사이드바·모바일 메뉴 |
| `src/pages/CommonUiPreview.tsx` | 공통 요소의 상태와 입력 동작을 확인하는 예시 화면 |
| `src/api.ts` | 백엔드 호출 코드 |
| `src/styles/tokens.css` | 공통 색상·폰트·모서리 변수 |
| `src/styles/global.css` | 로컬 폰트와 기본 스타일 |
| `src/assets/fonts/` | Noto Sans KR 가변 폰트 |
| `public/fonts/OFL.txt` | 배포 파일에도 포함되는 폰트 라이선스 |
| `../docs/design/` | 원본 와이어프레임과 해석 기준 |
| `../docs/spec/openapi.yaml` | 백엔드 요청·응답 명세 |

원본 SVG의 신청서 작성 문구는 화면 배치 참고용입니다. 실제 내용은 근로계약서·급여명세서 점검 기획에 맞춥니다.

Naver Cloud API 키는 프론트에 넣지 않습니다. 프론트는 팀 백엔드의 `/api`만 호출합니다. API 연결 시 `main`에 반영된 명세와 공통 응답 형식을 확인합니다.

## 화면 주소

- `/#/`: 서비스 소개 (처음 접속 시 기본 화면)
- `/#/guide`: 이용 안내 영상 전용 페이지. 영상이 제공되지 않으면 준비 상태와 글 안내를 표시합니다.
- `/#/workspace`: 2번 작업의 공통 UI 미리보기. 실제 업로드·점검 기능은 아직 연결하지 않았습니다.

`npm.cmd test`는 화면 이동 경로와 소개·영상 페이지의 서버 렌더링 결과를 확인합니다. 실제 브라우저 클릭 및 모바일 화면 검증을 대체하지 않습니다.

## 다음 작업

공통 UI·레이아웃 → 소개 화면 → 문서 업로드 → 추출 내용 수정 → 점검 결과 → 질문 → 녹음 순서로 퍼블리싱합니다. 샘플 응답은 API 명세의 필드명을 따르고, 실제 API 연결은 별도 작업으로 진행합니다.

브랜치·커밋·PR 규칙은 `../docs/CONVENTIONS.md`를 따릅니다.
