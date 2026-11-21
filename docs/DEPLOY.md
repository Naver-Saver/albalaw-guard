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

## 4. CD 없이 수동 배포

GitHub Secrets가 아직 없거나 Actions를 쓸 수 없을 때, 서버에서 직접 빌드해 같은 구성으로 띄운다.

```bash
scripts/deploy-on-server.sh 101.79.9.131 ../.deploy/albalaw_deploy main   # 브랜치·태그 지정 가능
```

이미지 이름·경로가 CD와 같아서, 이후 CD 배포가 그대로 덮어쓴다.

## 5. 수동 롤백

```bash
ssh root@<공인IP>
cd /opt/albalaw-guard
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<이전 커밋 SHA>/' .env
docker compose pull && docker compose up -d
```

## 6. 비용 주의

- 시연이 끝나면 서버 **반납** 또는 정지, CLOVA Dubbing 프로젝트 그룹 삭제.
- 콘솔 → Billing → 예산 알림 설정.

## 7. 법령·최저임금 데이터 정기 수집

근거 데이터(`law-data/law-articles.json`·`qna-manual.json`·`min-wage.json`)는 Object Storage `albalaw-uploads`에 있고, 서버는 여기서 읽는다(실패 시 이미지에 포함된 `backend/data/law-data/`로 대체).

| 항목 | 내용 |
| --- | --- |
| 수집 | `python -m sync.all` — 국가법령정보센터 Open API 조문 수집, 최저임금 CSV(+`announced.csv`) 변환, 수동 Q&A 업로드, `meta/sync_log.json` 기록 |
| 주기 | 매주 월 04:17 KST, 서버 cron(`infra/cron/albalaw-sync` → `/etc/cron.d/albalaw-sync`, CD가 설치)이 백엔드 컨테이너 안에서 실행 |
| 반영 | 서버는 `LAW_DATA_CACHE_SEC`(기본 600초)마다 Object Storage를 다시 읽는다. 재배포 불필요 |
| 필요 키 | 서버 `backend.env`의 `LAW_GO_KR_OC` (국가법령정보센터 OC). OC 신청 시 등록한 IP에서만 호출되므로 서버 IP(101.79.9.131)가 등록돼 있어야 한다 |
| 로그 | `/var/log/albalaw-sync.log`, Object Storage `meta/sync_log.json` |

즉시 수집:

```bash
ssh -i ../.deploy/albalaw_deploy root@101.79.9.131 'docker exec albalaw-guard-backend-1 python -m sync.all'
```

수집이 실패해도 Object Storage의 기존 파일은 그대로 남는다(단계별로 성공한 것만 덮어씀).

