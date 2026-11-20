#!/usr/bin/env bash
# Object Storage 버킷 + Container Registry 생성
#   NCP Object Storage는 S3 LocationConstraint를 받지 않으므로 region을 us-east-1로 둬야 버킷 생성이 된다.
#   수명주기(자동 삭제)는 S3 API로 설정 불가(AccessDenied) → 콘솔 Object Storage > Lifecycle Management에서 설정.
set -euo pipefail
cd "$(dirname "$0")"; source ./env.sh
cfg() { awk -F' *= *' -v k="$1" '$1==k{print $2}' ~/.ncloud/configure; }
export AWS_ACCESS_KEY_ID=${NCP_ACCESS_KEY:-$(cfg ncloud_access_key_id)} AWS_SECRET_ACCESS_KEY=${NCP_SECRET_KEY:-$(cfg ncloud_secret_access_key)}
S3="aws --endpoint-url https://kr.object.ncloudstorage.com --region us-east-1"
for b in "$OBJECT_STORAGE_BUCKET" "$NCR_BUCKET"; do $S3 s3api create-bucket --bucket "$b" >/dev/null 2>&1 && echo "버킷 생성: $b" || echo "버킷 존재/실패: $b"; done
python3 ./ncp.py raw POST "https://ncr.apigw.ntruss.com/ncr/api/v2/repositories/$NCR_NAME" "{\"bucket\":\"$NCR_BUCKET\",\"storageType\":\"objectStorage\"}" || true
python3 ./ncp.py raw GET https://ncr.apigw.ntruss.com/ncr/api/v2/repositories | jq -r '.results[] | "\(.name)\t\(.end_point)\t\(.status)"'
