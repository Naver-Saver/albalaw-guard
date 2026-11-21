# 프론트엔드 디자인 기준

- `00_All_Wireframes.svg`: 사용자가 제공한 `00_All_Wireframes .svg` 원본을 내용 변경 없이 복사했습니다.
- 원본에는 데스크톱 화면 8개가 있으며, 한국어 신청서 작성 안내용 문구와 예시가 포함되어 있습니다.
- 화면 배치와 공통 스타일을 참고하되, 실제 화면의 내용과 데이터는 `docs/PRD.md` 및 `docs/spec/`의 알바생 노동권 서비스 명세를 따릅니다.
- 모바일 화면은 `NFR-06`에 맞춰 360px 폭부터 사용할 수 있도록 후속 퍼블리싱에서 구성합니다.

## 기초 스타일

폰트는 `frontend/src/assets/fonts/NotoSansKR-VF.ttf`의 Noto Sans KR 가변 폰트입니다. 라이선스는 `frontend/public/fonts/OFL.txt`에 있으며, 빌드 시 `dist/fonts/OFL.txt`로 함께 배포됩니다.

색상은 SVG의 기초 팔레트를 `frontend/src/styles/tokens.css`에서 관리합니다.

| 용도 | 색상 |
| --- | --- |
| 주요 색상 | `#03C75A` |
| 주요 텍스트 | `#007F3B` |
| 배경 | `#F5F8F6` |
| 카드 배경 | `#FFFFFF` |
| 본문 | `#1D2923` |
| 보조 텍스트 | `#6E7D74` |
| 테두리 | `#E1E9E4` |

공통 컴포넌트와 개별 화면은 다음 작업에서 추가합니다.
