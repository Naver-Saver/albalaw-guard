#!/usr/bin/env bash
# CD(GitHub Actions)를 쓸 수 없을 때의 수동 배포: 서버에서 직접 이미지를 빌드해 같은 compose로 띄운다.
# 사용: scripts/deploy-on-server.sh <서버IP> <배포 개인키> [브랜치·태그(기본 main)]
# CD와 같은 /opt/albalaw-guard, 같은 이미지 이름을 쓰므로 이후 CD 배포가 그대로 덮어쓴다.
set -euo pipefail
HOST="${1:?서버 IP}"; KEY="${2:?배포 개인키}"; REF="${3:-main}"
REPO=https://github.com/Naver-Saver/albalaw-guard.git
REGISTRY=albalaw.kr.ncr.ntruss.com
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "root@$HOST")

"${SSH[@]}" bash -s -- "$REPO" "$REF" "$REGISTRY" <<'REMOTE'
set -euo pipefail
REPO="$1"; REF="$2"; REGISTRY="$3"; APP=/opt/albalaw-guard; SRC=$APP/src
mkdir -p "$APP"
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" fetch -q --depth 1 origin "$REF" && git -C "$SRC" checkout -q -f FETCH_HEAD
else
  git clone -q --depth 1 --branch "$REF" "$REPO" "$SRC"
fi
TAG="manual-$(git -C "$SRC" rev-parse --short HEAD)"
docker build -q -t "$REGISTRY/albalaw-backend:$TAG" "$SRC/backend" >/dev/null
docker build -q -t "$REGISTRY/albalaw-frontend:$TAG" "$SRC/frontend" >/dev/null
cp "$SRC/infra/docker-compose.prod.yml" "$APP/docker-compose.yml"
install -m 644 "$SRC/infra/cron/albalaw-sync" /etc/cron.d/albalaw-sync
install -m 755 "$SRC/infra/tls/setup-ip-cert.sh" "$APP/setup-ip-cert.sh"
mkdir -p "$APP/certs" "$APP/acme-webroot"
printf 'IMAGE_REGISTRY=%s\nIMAGE_TAG=%s\n' "$REGISTRY" "$TAG" > "$APP/.env"
touch "$APP/backend.env"
cd "$APP" && docker compose up -d --remove-orphans --pull never
docker image prune -af >/dev/null
docker builder prune -af >/dev/null
bash "$APP/setup-ip-cert.sh" || echo "HTTPS 인증서 발급 실패 — HTTP로 계속 서비스" >&2
echo "deployed $TAG"
REMOTE

for i in $(seq 1 10); do
  if curl -fsS "https://$HOST/api/health" || curl -fsS "http://$HOST/api/health"; then echo; exit 0; fi
  sleep 3
done
echo "헬스체크 실패" >&2; exit 1
