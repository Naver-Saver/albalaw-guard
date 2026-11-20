#!/usr/bin/env bash
# [서버에서 실행] Docker 설치 + 배포 디렉터리 + CD용 SSH 공개키 등록
#   사용: sudo bash 03-server-init.sh "<GitHub Actions용 공개키 내용>"
set -euo pipefail
DEPLOY_PUBKEY="${1:?CD용 공개키(ssh-ed25519 ...)를 인자로 주세요}"

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
mkdir -p /opt/albalaw-guard
touch /opt/albalaw-guard/backend.env && chmod 600 /opt/albalaw-guard/backend.env

mkdir -p ~/.ssh && chmod 700 ~/.ssh
grep -qF "$DEPLOY_PUBKEY" ~/.ssh/authorized_keys 2>/dev/null || echo "$DEPLOY_PUBKEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 메모리 작은 스펙 대비 2GB 스왑
if ! swapon --show | grep -q swap; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
docker --version && docker compose version
echo "완료: /opt/albalaw-guard/backend.env 에 운영용 환경변수를 넣으세요 (또는 GitHub Secret BACKEND_ENV 사용)"
