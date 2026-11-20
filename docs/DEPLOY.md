# 배포 가이드 (NCP + GitHub Actions)

```
PR ──► CI (lint · test · build · docker build)
main push ──► CD: 이미지 빌드 → NCP Container Registry push → SSH로 서버 docker compose pull/up → /api/health 확인
```

## 1. NCP 리소스 준비

1. **API 인증키**: 콘솔 → 마이페이지 → 계정 관리 → 인증키 관리 → 신규 API 인증키 생성 (서브 계정 권장)
2. **ncloud CLI** 설치 후 `ncloud configure` (Access Key / Secret Key / `https://ncloud.apigw.ntruss.com`)
3. 인프라 생성
   ```bash
   cd infra/ncloud
   cp env.sh.example env.sh
   ./00-check.sh
   ./01-network.sh          # 출력된 이미지 번호·스펙 코드를 env.sh에 입력
   ./02-server.sh           # 서버 + 공인 IP
   ./04-object-storage.sh   # 업로드 버킷
   ```
4. **Container Registry** (콘솔): Container Registry → 레지스트리 생성 → 엔드포인트 확인 (예: `albalaw.kr.ncr.ntruss.com`)
5. **CD용 SSH 키** 만들고 서버에 등록
   ```bash
   ssh-keygen -t ed25519 -f ./albalaw_deploy -N "" -C albalaw-deploy
   scp infra/ncloud/03-server-init.sh root@<공인IP>:/root/
   ssh root@<공인IP> "bash /root/03-server-init.sh '$(cat albalaw_deploy.pub)'"
   ```

## 2. GitHub Secrets 등록

Settings → Secrets and variables → Actions → New repository secret

| 이름 | 값 |
| --- | --- |
| `NCP_ACCESS_KEY` | NCP Access Key (NCR 로그인용) |
| `NCP_SECRET_KEY` | NCP Secret Key |
| `NCR_REGISTRY` | 예: `albalaw.kr.ncr.ntruss.com` |
| `SERVER_HOST` | 서버 공인 IP |
| `SERVER_USER` | (선택) 기본 `root` |
| `SERVER_SSH_KEY` | `albalaw_deploy` **개인키** 전체 내용 |
| `BACKEND_ENV` | (선택) 운영용 `backend/.env` 전체 내용. 없으면 서버의 `/opt/albalaw-guard/backend.env` 사용 |

gh CLI로 한 번에:
```bash
gh secret set NCP_ACCESS_KEY  -R <org>/albalaw-guard
gh secret set NCP_SECRET_KEY  -R <org>/albalaw-guard
gh secret set NCR_REGISTRY    -R <org>/albalaw-guard -b "albalaw.kr.ncr.ntruss.com"
gh secret set SERVER_HOST     -R <org>/albalaw-guard -b "<공인IP>"
gh secret set SERVER_SSH_KEY  -R <org>/albalaw-guard < albalaw_deploy
gh secret set BACKEND_ENV     -R <org>/albalaw-guard < backend/.env.prod
```

시크릿이 없으면 CD는 경고만 남기고 건너뜁니다(실패 아님).

## 3. 배포 확인

- Actions → CD 실행 결과의 **Smoke test** 단계 통과
- 브라우저에서 `http://<공인IP>` 접속

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
