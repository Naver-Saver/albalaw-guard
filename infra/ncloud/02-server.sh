#!/usr/bin/env bash
# 서버 생성 + 공인 IP 할당
set -euo pipefail
source "$(dirname "$0")/env.sh"
J="--regionCode $NCP_REGION --output json"
OUT="$(dirname "$0")/.state"
: "${SERVER_IMAGE_NO:?env.sh에 SERVER_IMAGE_NO를 채우세요}" "${SERVER_SPEC_CODE:?env.sh에 SERVER_SPEC_CODE를 채우세요}"
vpc_no=$(cat "$OUT/vpc_no"); subnet_no=$(cat "$OUT/subnet_no"); acg_no=$(cat "$OUT/acg_no")

server_no=$(ncloud vserver getServerInstanceList $J --vpcNo "$vpc_no" --serverName "$PREFIX-app" | jq -r '.getServerInstanceListResponse.serverInstanceList[0].serverInstanceNo // empty')
if [ -z "$server_no" ]; then
  server_no=$(ncloud vserver createServerInstances $J --vpcNo "$vpc_no" --subnetNo "$subnet_no" \
    --serverName "$PREFIX-app" --serverImageNo "$SERVER_IMAGE_NO" --serverSpecCode "$SERVER_SPEC_CODE" \
    --loginKeyName "$LOGIN_KEY_NAME" \
    --networkInterfaceList "networkInterfaceOrder='0', accessControlGroupNoList=['$acg_no']" \
    | jq -r '.createServerInstancesResponse.serverInstanceList[0].serverInstanceNo')
  echo "서버 생성 요청: $server_no (RUN까지 수 분 소요)"
fi
until [ "$(ncloud vserver getServerInstanceDetail $J --serverInstanceNo "$server_no" | jq -r '.getServerInstanceDetailResponse.serverInstanceList[0].serverInstanceStatus.code')" = "RUN" ]; do sleep 15; echo -n .; done
echo; echo "$server_no" > "$OUT/server_no"

ip=$(ncloud vserver getServerInstanceDetail $J --serverInstanceNo "$server_no" | jq -r '.getServerInstanceDetailResponse.serverInstanceList[0].publicIp // empty')
if [ -z "$ip" ]; then
  ip=$(ncloud vserver createPublicIpInstance $J --serverInstanceNo "$server_no" | jq -r '.createPublicIpInstanceResponse.publicIpInstanceList[0].publicIp')
fi
echo "$ip" > "$OUT/public_ip"
echo "서버: $server_no  공인 IP: $ip"
echo
echo "root 비밀번호 확인:"
echo "  ncloud vserver getRootPassword $J --serverInstanceNo $server_no --privateKey \"\$(cat $OUT/$LOGIN_KEY_NAME.pem)\""
echo "다음: ssh root@$ip 로 접속해 03-server-init.sh 실행 (docs/DEPLOY.md)"
