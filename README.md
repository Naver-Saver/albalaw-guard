# 알바생 노동권 지킴이 (albalaw-guard)

근로계약서·급여명세서 사진과 대화 녹음을 정리하고, **국가법령정보센터 법령 조문**과 고용노동부 최저임금 고시·노동 Q&A를 근거로 확인이 필요한 부분을 알려주는 웹 서비스입니다.
네이버 클라우드 CLOVA OCR · Speech · Studio · Chatbot · CSR · Voice · Papago와 Object Storage를 사용합니다.

> 이 서비스는 법률 자문이 아닙니다. 정확한 판단은 고용노동부(1350) 또는 대한법률구조공단(132)에 문의하세요.

## 문서

- [기술 문서](docs/TECHNICAL.md) — 기술 스펙 · 아키텍처 · 발전 과정 · 조원별 역할
- [기술 문서 Word 파일](docs/TECHNICAL.docx) — 같은 내용을 Word(.docx)로 내려받기
- [PRD](docs/PRD.md) — 목표, 범위, 일정
- [명세 (SDD)](docs/spec/README.md) — 요구사항 분석 · 기능 명세 · API 명세(`openapi.yaml`) · 데이터 저장 구조 · AI 파이프라인
- [협업 컨벤션](docs/CONVENTIONS.md) — 브랜치·커밋·PR 규칙
- [배포 가이드](docs/DEPLOY.md) — NCP 인프라, CI/CD, 시크릿

## 구조

```
backend/    FastAPI (Python 3.12)
frontend/   React + TypeScript + Vite
infra/      운영 docker-compose, ncloud CLI 스크립트
docs/       기술 문서, PRD, 명세(spec/), 컨벤션, 배포 가이드
.github/    CI/CD 워크플로, PR·이슈 템플릿
```

## 로컬 실행

```bash
# 백엔드
cd backend
cp ../.env.example .env        # 키 채우기 (.env는 git에 올라가지 않음)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload  # http://localhost:8000/docs

# 프론트엔드 (다른 터미널)
cd frontend
npm install
npm run dev                    # http://localhost:5173  (/api → 8000 프록시)

# 또는 한 번에
docker compose up --build      # http://localhost:8080
```

## 팀

| 역할 | 담당 |
| --- | --- |
| 프론트엔드 | |
| 백엔드·인프라 | |
| AI 파이프라인 | |
| 데이터·콘텐츠 | |
