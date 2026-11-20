#!/usr/bin/env bash
# CD에 필요한 GitHub Secrets 등록 (gh auth login 된 PC에서 직접 실행)
#   사용: scripts/set-deploy-secrets.sh <서버 공인 IP> <배포 개인키 경로> [NCR 엔드포인트]
#   NCP 키는 ~/.ncloud/configure 에서 읽어 바로 gh로 넘긴다 (화면에 출력하지 않음).
set -euo pipefail
REPO=Naver-Saver/albalaw-guard
HOST="${1:?서버 공인 IP}"; KEY="${2:?배포 개인키 경로}"; NCR="${3:-albalaw.kr.ncr.ntruss.com}"
cfg() { awk -F' *= *' -v k="$1" '$1==k{printf "%s",$2}' ~/.ncloud/configure; }
cfg ncloud_access_key_id     | gh secret set NCP_ACCESS_KEY -R "$REPO"
cfg ncloud_secret_access_key | gh secret set NCP_SECRET_KEY -R "$REPO"
gh secret set NCR_REGISTRY   -R "$REPO" -b "$NCR"
gh secret set SERVER_HOST    -R "$REPO" -b "$HOST"
gh secret set SERVER_USER    -R "$REPO" -b root
gh secret set SERVER_SSH_KEY -R "$REPO" < "$KEY"
gh secret list -R "$REPO"
