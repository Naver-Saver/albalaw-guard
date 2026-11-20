#!/usr/bin/env bash
# CD용 배포 키 생성 → Init Script(Docker 설치·키 등록) → 서버 생성(공인 IP 포함)
set -euo pipefail
cd "$(dirname "$0")"; source ./env.sh
N() { python3 ./ncp.py "$@"; }
VPC_NO=$(cat .state/vpc_no); SUBNET_NO=$(cat .state/subnet_no); ACG=$(cat .state/acg_no)

[ -f .state/deploy_key ] || ssh-keygen -q -t ed25519 -f .state/deploy_key -N "" -C "$PREFIX-deploy"
INIT=$(sed "s|__DEPLOY_PUBKEY__|$(cat .state/deploy_key.pub)|" ./init-script.sh)
INIT_NO=$(N vserver createInitScript regionCode=$NCP_REGION initScriptName=$PREFIX-init osTypeCode=LNX "initScriptContent=$INIT" \
  | jq -r '.createInitScriptResponse.initScriptList[0].initScriptNo')

SERVER_NO=$(N vserver createServerInstances regionCode=$NCP_REGION vpcNo=$VPC_NO subnetNo=$SUBNET_NO serverName=$PREFIX-001 \
  serverImageNo=$SERVER_IMAGE_NO serverSpecCode=$SERVER_SPEC_CODE loginKeyName=$LOGIN_KEY_NAME initScriptNo=$INIT_NO \
  associateWithPublicIp=true networkInterfaceList.1.networkInterfaceOrder=0 networkInterfaceList.1.accessControlGroupNoList.1=$ACG \
  | jq -r '.createServerInstancesResponse.serverInstanceList[0].serverInstanceNo')
echo "서버 생성: $SERVER_NO (running까지 대기)"
until [ "$(N vserver getServerInstanceDetail regionCode=$NCP_REGION serverInstanceNo=$SERVER_NO | jq -r '.getServerInstanceDetailResponse.serverInstanceList[0].serverInstanceStatus.code')" = RUN ]; do sleep 15; echo -n .; done
IP=$(N vserver getServerInstanceDetail regionCode=$NCP_REGION serverInstanceNo=$SERVER_NO | jq -r '.getServerInstanceDetailResponse.serverInstanceList[0].publicIp')
echo; echo "$IP" > .state/public_ip
echo "서버 $SERVER_NO  공인 IP $IP  — 배포 키: .state/deploy_key (GitHub Secret SERVER_SSH_KEY)"
