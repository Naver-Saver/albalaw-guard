# 배포 가이드 (NCP + GitHub Actions)

```
PR ──► CI (lint · test · build · docker build)
main push ──► CD: 이미지 빌드 → NCP Container Registry push → SSH로 서버 docker compose pull/up → /api/health 확인
```

## 1. NCP 리소스 (생성 완료 · 2026-11-20)

| 리소스 | 값 |
| --- | --- |
| 서버 | `albalaw-001` · c2-g3a (2vCPU/4GB) · Ubuntu 22.04 · 공인 IP `101.79.9.131` · Docker/Compose 설치 완료 |
| VPC / Subnet | 기존 `ai-vpc` / `ai-public-subnet` (KR-2) 재사용 |
| ACG | `albalaw-acg` — 인바운드 22·80·443, 아웃바운드 전체 |
| Container Registry | `albalaw.kr.ncr.ntruss.com` (버킷 `albalaw-ncr`) |
| Object Storage | `albalaw-uploads` (업로드 임시 저장) |
| 배포 키 | 관리자 PC `nCloud_Project/.deploy/albalaw_deploy` (git 밖) — 서버 root에 등록됨 |

새로 만들 때는 `infra/ncloud/` 스크립트를 사용합니다 ([README](../infra/ncloud/README.md)).

**콘솔에서 남은 설정**
- Object Storage → `albalaw-uploads` → Lifecycle Management: `uploads/` 1일 후 삭제 (S3 API로는 설정 불가)
- CLOVA OCR / Speech / Chatbot 도메인, CLOVA Studio API 키·Request ID, AI·NAVER API Application(CSR·Voice), Papago Translation Application

## 2. GitHub Secrets 등록

키 값은 채팅·커밋에 남기지 않도록, 키가 있는 PC에서 스크립트로 바로 등록합니다.

```bash
scripts/set-deploy-secrets.sh 101.79.9.131 ../.deploy/albalaw_deploy
```

| 이름 | 값 |
| --- | --- |
| `NCP_ACCESS_KEY` / `NCP_SECRET_KEY` | `~/.ncloud/configure`에서 읽음 (NCR 로그인용) |
| `NCR_REGISTRY` | `albalaw.kr.ncr.ntruss.com` |
| `SERVER_HOST` / `SERVER_USER` | `101.79.9.131` / `root` |
| `SERVER_SSH_KEY` | 배포 개인키 |
| `BACKEND_ENV` | (선택) 운영용 `backend/.env` 전체. 없으면 서버 `/opt/albalaw-guard/backend.env` 사용 |

```bash
gh secret set BACKEND_ENV -R Naver-Saver/albalaw-guard < backend/.env.prod   # 나중에 AI 키가 준비되면
```

시크릿이 없으면 CD는 경고만 남기고 건너뜁니다(실패 아님).

## 3. 배포 확인

- Actions → CD 실행 결과의 **Smoke test** 단계 통과
- 브라우저에서 http://101.79.9.131 접속

## 4. 수동 롤백

```bash
ssh root@<공인IP>
cd /opt/albalaw-guard
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<이전 커밋 SHA>/' .env
docker compose pull && docker compose up -d
```

## 5. 비용 주의

- 시연이 끝나면 서버 **반납** 또는 정지, CLOVA Dubbing 프로젝트 그룹 삭제.
- 콘솔 → Billing → 예산 알림 설정.
