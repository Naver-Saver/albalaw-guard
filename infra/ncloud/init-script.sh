#!/bin/bash
# 서버 최초 부팅 시 실행 (NCP Init Script). __DEPLOY_PUBKEY__는 02-server.sh가 치환.
set -e
mkdir -p /root/.ssh && chmod 700 /root/.ssh
echo "__DEPLOY_PUBKEY__" >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys
mkdir -p /opt/albalaw-guard && touch /opt/albalaw-guard/backend.env && chmod 600 /opt/albalaw-guard/backend.env
if ! swapon --show | grep -q swap; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
