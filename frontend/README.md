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

백엔드는 별도 터미널에서 루트 README의 방법으로 실행합니다. Vite가 `/api` 요청을 `http://localhost:8000`으로 전달하므로 백엔드가 실행 중이어야 서버 상태가 정상으로 표시됩니다. 화면 퍼블리싱 자체는 백엔드 없이도 가능합니다.

```powershell
npm.cmd run lint
npm.cmd run build
npm.cmd run preview
```

`build`는 TypeScript 검사 후 `dist/`에 배포 파일을 생성합니다. 현재 Vite 설정에서는 `preview`도 `/api` 프록시를 사용하므로 API 확인 시 백엔드를 함께 실행합니다. Docker·Nginx를 포함한 통합 확인은 저장소 루트의 `docker compose up --build`를 사용합니다.

## 현재 파일과 기준

| 경로 | 역할 |
| --- | --- |
| `src/main.tsx` | React 진입점과 전역 스타일 로드 |
| `src/App.tsx` | 기존 서비스 소개·서버 상태 화면 |
| `src/api.ts` | 백엔드 호출 코드 |
| `src/styles/tokens.css` | 공통 색상·폰트·모서리 변수 |
| `src/styles/global.css` | 로컬 폰트와 기본 스타일 |
| `src/index.css` | 기존 시작 화면 스타일 |
| `src/assets/fonts/` | Noto Sans KR 가변 폰트 |
| `public/fonts/OFL.txt` | 배포 파일에도 포함되는 폰트 라이선스 |
| `../docs/design/` | 원본 와이어프레임과 해석 기준 |
| `../docs/spec/openapi.yaml` | 백엔드 요청·응답 명세 |

원본 SVG의 신청서 작성 문구는 화면 배치 참고용입니다. 실제 내용은 근로계약서·급여명세서 점검 기획에 맞춥니다.

Naver Cloud API 키는 프론트에 넣지 않습니다. 프론트는 팀 백엔드의 `/api`만 호출합니다. API 연결 시 `main`에 반영된 명세와 공통 응답 형식을 확인합니다.

## 다음 작업

공통 UI·레이아웃 → 소개 화면 → 문서 업로드 → 추출 내용 수정 → 점검 결과 → 질문 → 녹음 순서로 퍼블리싱합니다. 샘플 응답은 API 명세의 필드명을 따르고, 실제 API 연결은 별도 작업으로 진행합니다.

브랜치·커밋·PR 규칙은 `../docs/CONVENTIONS.md`를 따릅니다.
