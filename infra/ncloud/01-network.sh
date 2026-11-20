#!/usr/bin/env bash
# VPC · Subnet · ACG · 로그인 키 생성 (이미 있으면 재사용)
set -euo pipefail
source "$(dirname "$0")/env.sh"
J="--regionCode $NCP_REGION --output json"
OUT="$(dirname "$0")/.state"; mkdir -p "$OUT"

vpc_no=$(ncloud vpc getVpcList $J --vpcName "$PREFIX-vpc" | jq -r '.getVpcListResponse.vpcList[0].vpcNo // empty')
if [ -z "$vpc_no" ]; then
  vpc_no=$(ncloud vpc createVpc $J --vpcName "$PREFIX-vpc" --ipv4CidrBlock "$VPC_CIDR" | jq -r '.createVpcResponse.vpcList[0].vpcNo')
  echo "VPC 생성: $vpc_no (RUN 상태가 될 때까지 대기)"
  until [ "$(ncloud vpc getVpcDetail $J --vpcNo "$vpc_no" | jq -r '.getVpcDetailResponse.vpcList[0].vpcStatus.code')" = "RUN" ]; do sleep 5; done
fi
echo "VPC: $vpc_no"; echo "$vpc_no" > "$OUT/vpc_no"

acl_no=$(ncloud vpc getNetworkAclList $J --vpcNo "$vpc_no" | jq -r '.getNetworkAclListResponse.networkAclList[0].networkAclNo')

subnet_no=$(ncloud vpc getSubnetList $J --vpcNo "$vpc_no" --subnetName "$PREFIX-public" | jq -r '.getSubnetListResponse.subnetList[0].subnetNo // empty')
if [ -z "$subnet_no" ]; then
  subnet_no=$(ncloud vpc createSubnet $J --vpcNo "$vpc_no" --subnetName "$PREFIX-public" --subnet "$SUBNET_CIDR" \
    --zoneCode "$NCP_ZONE" --networkAclNo "$acl_no" --subnetTypeCode PUBLIC --usageTypeCode GEN \
    | jq -r '.createSubnetResponse.subnetList[0].subnetNo')
  echo "Subnet 생성: $subnet_no (대기)"
  until [ "$(ncloud vpc getSubnetDetail $J --subnetNo "$subnet_no" | jq -r '.getSubnetDetailResponse.subnetList[0].subnetStatus.code')" = "RUN" ]; do sleep 5; done
fi
echo "Subnet: $subnet_no"; echo "$subnet_no" > "$OUT/subnet_no"

acg_no=$(ncloud vserver getAccessControlGroupList $J --vpcNo "$vpc_no" --accessControlGroupName "$PREFIX-acg" | jq -r '.getAccessControlGroupListResponse.accessControlGroupList[0].accessControlGroupNo // empty')
if [ -z "$acg_no" ]; then
  acg_no=$(ncloud vserver createAccessControlGroup $J --vpcNo "$vpc_no" --accessControlGroupName "$PREFIX-acg" \
    | jq -r '.createAccessControlGroupResponse.accessControlGroupList[0].accessControlGroupNo')
  # 22: GitHub Actions 러너 IP가 고정이 아니라 전체 허용(키 인증만 사용), 80/443: 웹
  for port in 22 80 443; do
    ncloud vserver addAccessControlGroupInboundRule $J --vpcNo "$vpc_no" --accessControlGroupNo "$acg_no" \
      --accessControlGroupRuleList "protocolTypeCode='TCP', ipBlock='0.0.0.0/0', portRange='$port'" >/dev/null
  done
fi
echo "ACG: $acg_no"; echo "$acg_no" > "$OUT/acg_no"

if ! ncloud vserver getLoginKeyList $J --keyName "$LOGIN_KEY_NAME" | jq -e '.getLoginKeyListResponse.loginKeyList | length > 0' >/dev/null; then
  ncloud vserver createLoginKey $J --keyName "$LOGIN_KEY_NAME" | jq -r '.createLoginKeyResponse.privateKey' > "$OUT/$LOGIN_KEY_NAME.pem"
  chmod 600 "$OUT/$LOGIN_KEY_NAME.pem"
  echo "로그인 키 저장: $OUT/$LOGIN_KEY_NAME.pem (분실 시 재발급 불가 — 안전한 곳에 보관)"
fi

echo
echo "== 사용 가능한 서버 이미지 (Ubuntu) — SERVER_IMAGE_NO 후보 =="
ncloud vserver getServerImageList $J | jq -r '.getServerImageListResponse.serverImageList[] | select(.serverImageName|test("ubuntu";"i")) | "\(.serverImageNo)\t\(.serverImageName)"' || true
echo "== 서버 스펙 — SERVER_SPEC_CODE 후보 (2vCPU/4~8GB 권장) =="
ncloud vserver getServerSpecList $J --zoneCode "$NCP_ZONE" | jq -r '.getServerSpecListResponse.serverSpecList[] | "\(.serverSpecCode)\t\(.cpuCount)vCPU\t\(.memorySize/1073741824)GB"' | head -20 || true
echo
echo "→ env.sh 에 SERVER_IMAGE_NO / SERVER_SPEC_CODE 를 채운 뒤 02-server.sh 실행"
