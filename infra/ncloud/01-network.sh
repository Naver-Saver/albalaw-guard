#!/usr/bin/env bash
# VPC·Public Subnet·ACG(22/80/443) 준비. 기존 VPC를 쓰려면 env.sh에 VPC_NO, SUBNET_NO를 지정.
set -euo pipefail
cd "$(dirname "$0")"; source ./env.sh
N() { python3 ./ncp.py "$@"; }
mkdir -p .state

if [ -z "${VPC_NO:-}" ]; then
  VPC_NO=$(N vpc createVpc regionCode=$NCP_REGION vpcName=$PREFIX-vpc ipv4CidrBlock=$VPC_CIDR | jq -r '.createVpcResponse.vpcList[0].vpcNo')
  until [ "$(N vpc getVpcDetail regionCode=$NCP_REGION vpcNo=$VPC_NO | jq -r '.getVpcDetailResponse.vpcList[0].vpcStatus.code')" = RUN ]; do sleep 5; done
fi
echo "$VPC_NO" > .state/vpc_no

if [ -z "${SUBNET_NO:-}" ]; then
  ACL=$(N vpc getNetworkAclList regionCode=$NCP_REGION vpcNo=$VPC_NO | jq -r '.getNetworkAclListResponse.networkAclList[0].networkAclNo')
  SUBNET_NO=$(N vpc createSubnet regionCode=$NCP_REGION vpcNo=$VPC_NO subnetName=$PREFIX-public subnet=$SUBNET_CIDR \
    zoneCode=$NCP_ZONE networkAclNo=$ACL subnetTypeCode=PUBLIC usageTypeCode=GEN | jq -r '.createSubnetResponse.subnetList[0].subnetNo')
  until [ "$(N vpc getSubnetDetail regionCode=$NCP_REGION subnetNo=$SUBNET_NO | jq -r '.getSubnetDetailResponse.subnetList[0].subnetStatus.code')" = RUN ]; do sleep 5; done
fi
echo "$SUBNET_NO" > .state/subnet_no

ACG=$(N vserver getAccessControlGroupList regionCode=$NCP_REGION vpcNo=$VPC_NO accessControlGroupName=$PREFIX-acg | jq -r '.getAccessControlGroupListResponse.accessControlGroupList[0].accessControlGroupNo // empty')
if [ -z "$ACG" ]; then
  ACG=$(N vserver createAccessControlGroup regionCode=$NCP_REGION vpcNo=$VPC_NO accessControlGroupName=$PREFIX-acg | jq -r '.createAccessControlGroupResponse.accessControlGroupList[0].accessControlGroupNo')
  sleep 5
  # 22는 GitHub Actions 러너 IP가 고정이 아니라 전체 허용 (키 인증만 사용)
  N vserver addAccessControlGroupInboundRule regionCode=$NCP_REGION vpcNo=$VPC_NO accessControlGroupNo=$ACG \
    accessControlGroupRuleList.1.protocolTypeCode=TCP accessControlGroupRuleList.1.ipBlock=0.0.0.0/0 accessControlGroupRuleList.1.portRange=22 \
    accessControlGroupRuleList.2.protocolTypeCode=TCP accessControlGroupRuleList.2.ipBlock=0.0.0.0/0 accessControlGroupRuleList.2.portRange=80 \
    accessControlGroupRuleList.3.protocolTypeCode=TCP accessControlGroupRuleList.3.ipBlock=0.0.0.0/0 accessControlGroupRuleList.3.portRange=443 >/dev/null
  # 새 ACG는 아웃바운드 규칙이 비어 있어 외부 통신(Docker 설치, 이미지 pull)이 막힌다 → 전체 허용
  N vserver addAccessControlGroupOutboundRule regionCode=$NCP_REGION vpcNo=$VPC_NO accessControlGroupNo=$ACG \
    accessControlGroupRuleList.1.protocolTypeCode=TCP accessControlGroupRuleList.1.ipBlock=0.0.0.0/0 accessControlGroupRuleList.1.portRange=1-65535 \
    accessControlGroupRuleList.2.protocolTypeCode=UDP accessControlGroupRuleList.2.ipBlock=0.0.0.0/0 accessControlGroupRuleList.2.portRange=1-65535 \
    accessControlGroupRuleList.3.protocolTypeCode=ICMP accessControlGroupRuleList.3.ipBlock=0.0.0.0/0 >/dev/null
fi
echo "$ACG" > .state/acg_no
echo "VPC=$VPC_NO SUBNET=$SUBNET_NO ACG=$ACG"
echo "== 서버 스펙 후보 (이미지 $SERVER_IMAGE_NO) =="
N vserver getServerSpecList regionCode=$NCP_REGION zoneCode=$NCP_ZONE serverImageNo=$SERVER_IMAGE_NO \
  | jq -r '.getServerSpecListResponse.serverSpecList[] | "\(.serverSpecCode)\t\(.serverSpecDescription)"' | head -8
