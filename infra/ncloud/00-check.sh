#!/usr/bin/env bash
# ncloud CLI 설치·인증 확인. 사전: Java 8+, jq, ncloud CLI (https://cli.ncloud-docs.com/docs/guide-clichange)
#   ncloud configure   # Access Key / Secret Key / https://ncloud.apigw.ntruss.com 입력
set -euo pipefail
command -v ncloud >/dev/null || { echo "ncloud CLI가 PATH에 없습니다."; exit 1; }
command -v jq >/dev/null || { echo "jq가 필요합니다: sudo apt install -y jq"; exit 1; }
echo "== 인증 확인 (리전 목록) =="
ncloud vserver getRegionList --output json | jq -r '.getRegionListResponse.regionList[] | "\(.regionCode)\t\(.regionName)"'
