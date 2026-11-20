#!/usr/bin/env bash
# 인증 확인. 사전: python3, jq, ~/.ncloud/configure (ncloud configure로 생성) 또는 NCP_ACCESS_KEY/NCP_SECRET_KEY
set -euo pipefail
command -v jq >/dev/null || { echo "jq가 필요합니다: sudo apt install -y jq"; exit 1; }
python3 "$(dirname "$0")/ncp.py" vserver getRegionList | jq -r '.getRegionListResponse.regionList[] | "\(.regionCode)\t\(.regionName)"'
