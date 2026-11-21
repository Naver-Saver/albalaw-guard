#!/usr/bin/env bash
# 서버 공인 IP에 Let's Encrypt IP 인증서를 발급하고 자동 갱신을 건다 (root, 서버에서 실행).
# - IP 인증서는 shortlived 프로필(유효 약 6일)만 가능 → 3일마다 갱신
# - 검증은 HTTP-01 webroot: 프론트 Nginx가 /.well-known/acme-challenge/를 acme-webroot에서 서빙
# - 갱신 뒤 프론트 컨테이너가 HTTPS 설정을 다시 고르고 Nginx를 reload
# 여러 번 실행해도 안전하다. 사용: setup-ip-cert.sh [공인 IP] [앱 폴더]
set -euo pipefail
APP="${2:-/opt/albalaw-guard}"
IP="${1:-$(curl -fsS4 --max-time 10 https://api.ipify.org)}"
ACME="$HOME/.acme.sh/acme.sh"
CERTS="$APP/certs"; WEBROOT="$APP/acme-webroot"
mkdir -p "$CERTS" "$WEBROOT"
chmod 700 "$CERTS"

if [ ! -x "$ACME" ]; then
  curl -fsSL https://raw.githubusercontent.com/acmesh-official/acme.sh/master/acme.sh \
    | sh -s -- --install-online --nocron >/dev/null
fi
"$ACME" --upgrade >/dev/null 2>&1 || true
"$ACME" --set-default-ca --server letsencrypt >/dev/null
"$ACME" --install-cronjob >/dev/null 2>&1 || true

RELOAD="cd $APP && docker compose exec -T frontend sh /docker-entrypoint.d/40-albalaw-tls.sh && docker compose exec -T frontend nginx -s reload"

if ! "$ACME" --list | awk 'NR>1{print $1}' | grep -qx "$IP"; then
  "$ACME" --issue -d "$IP" --webroot "$WEBROOT" \
    --server letsencrypt --certificate-profile shortlived --days 3
fi
"$ACME" --install-cert -d "$IP" \
  --key-file "$CERTS/privkey.pem" \
  --fullchain-file "$CERTS/fullchain.pem" \
  --reloadcmd "$RELOAD"
echo "IP 인증서 준비 완료: https://$IP"
