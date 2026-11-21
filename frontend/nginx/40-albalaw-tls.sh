#!/bin/sh
# 인증서가 있으면 HTTPS 설정, 없으면 HTTP 전용 설정을 고른다.
# 컨테이너 시작 시 nginx 이미지가 자동 실행하고, 인증서 갱신 후 reloadcmd에서도 다시 실행한다.
set -eu
CERTS=/etc/nginx/certs
SRC=/etc/nginx/albalaw
if [ -s "$CERTS/fullchain.pem" ] && [ -s "$CERTS/privkey.pem" ]; then
  cp "$SRC/https.conf" /etc/nginx/conf.d/default.conf
  echo "albalaw: HTTPS 설정 사용"
else
  cp "$SRC/http.conf" /etc/nginx/conf.d/default.conf
  echo "albalaw: 인증서 없음, HTTP 설정 사용"
fi
