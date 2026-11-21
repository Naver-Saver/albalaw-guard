# 계약서 서명 전 30초 체크

Saver가 직접 제작한 근로계약서 교육 영상. 외부 영상이나 음악을 사용하지 않는다.
일반적인 확인사항을 소개하며, 개별 사건의 법률 판단이나 최저임금 금액을 다루지 않는다.

- 근거: [고용노동부 근로계약서 작성 안내](https://www.moel.go.kr/mainpop2.do) (2026-11-21 확인)
- 시각 자료: Pillow로 그린 계약서 카드와 텍스트 애니메이션
- 내레이션: 기존 Saver `/api/tts`를 통한 CLOVA Voice 한국어 합성 (Dubbing 제작 아님)
- 출력: 1280×720, 24fps, 30초, H.264/AAC MP4, 빠른 재생 시작용 faststart
- 파일: `frontend/public/videos/contract-check.mp4`, 포스터 JPG, 한국어 WebVTT
- 화면: `/#/guide`, 기본 미디어로 연결. 자동 재생 없이 사용자가 재생하며 실패 시 체크리스트를 제공한다.

| 구간 | 내용 |
| --- | --- |
| 0–3초 | 서명하기 전, 잠깐! |
| 3–9초 | 시급·계산방법·지급일·지급방법 |
| 9–16초 | 근무요일·근무시간·휴게시간·휴일 |
| 16–22초 | 모르는 내용과 빈칸을 확인한 뒤 서명 |
| 22–27초 | 작성한 계약서를 받아 보관 |
| 27–30초 | 고용노동부 상담 1350 |

## 다시 만들기

별도 제작용 Python 환경에 `Pillow`, `imageio-ffmpeg`를 설치한다.
제품의 런타임 의존성으로 추가할 필요는 없다. Windows의 맑은 고딕을 사용하며,
다른 환경에서는 `VIDEO_FONT_REGULAR`와 `VIDEO_FONT_BOLD`에 한국어 폰트 경로를 설정한다.

```powershell
python -m pip install Pillow imageio-ffmpeg
python scripts/create-contract-video.py --api http://127.0.0.1:8000/api
```

API 주소는 `/tts`가 제공되는 실행 중인 Saver 백엔드로 지정한다.
새 내레이션을 합성할 때 CLOVA Voice 사용량이 발생한다.
문장별 음성은 OS 임시 폴더 `saver-contract-video`에 캐시하여 재사용한다.
키는 스크립트나 프론트에 넣지 않는다. 전체 대본과 장면 구성은 제작 스크립트에 있다.

완성 파일은 FFmpeg로 전체 디코딩 오류 없음, 길이 30초와 오디오 신호를 확인했다.
6개 장면을 이미지로 확인했으며 프론트 테스트 41개, lint, build가 통과했다.
브라우저에서 직접 재생·청취하는 검수는 별도다.
